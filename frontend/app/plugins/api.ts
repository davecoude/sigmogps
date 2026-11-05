/**
 * Cliente HTTP centralizado (ARQ-09).
 *
 * Resuelve tres cosas que no deben repetirse en cada llamada:
 *  - la cookie de sesión viaja siempre;
 *  - el token CSRF se adjunta en toda petición que modifica datos (SEG-11);
 *  - un 401 intenta renovar la sesión una vez antes de mandar al login.
 */
import type { Problem } from '~/types/api'

const CSRF_COOKIE = 'sigmogps_csrf'
const CSRF_HEADER = 'X-CSRF-Token'
const MUTACIONES = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export class ApiError extends Error {
  constructor(
    readonly problem: Problem,
    readonly status: number,
  ) {
    super(problem.detail || problem.title)
    this.name = 'ApiError'
  }
}

function leerCookie(nombre: string): string | null {
  if (import.meta.server) return null
  const partes = document.cookie.split('; ')
  for (const parte of partes) {
    const [clave, ...resto] = parte.split('=')
    if (clave === nombre) return decodeURIComponent(resto.join('='))
  }
  return null
}

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  const base = config.public.apiBaseUrl

  let renovando: Promise<boolean> | null = null

  async function renovarSesion(): Promise<boolean> {
    // Una sola renovación aunque fallen diez peticiones a la vez.
    if (!renovando) {
      renovando = $fetch('/auth/refresh', {
        baseURL: base,
        method: 'POST',
        credentials: 'include',
      })
        .then(() => true)
        .catch(() => false)
        .finally(() => {
          renovando = null
        })
    }
    return renovando
  }

  const api = $fetch.create({
    baseURL: base,
    credentials: 'include',
    retry: false,

    onRequest({ options }) {
      const metodo = (options.method ?? 'GET').toUpperCase()
      if (MUTACIONES.has(metodo)) {
        const token = leerCookie(CSRF_COOKIE)
        if (token) {
          options.headers = new Headers(options.headers)
          options.headers.set(CSRF_HEADER, token)
        }
      }
    },

  async onResponseError({ request, options, response }) {
    const problem = response._data as Problem | undefined
    const urlPeticion = String(request)

    // /auth/me y /auth/refresh son el sondeo de sesión: un 401 ahí solo
    // significa «no hay sesión», no hay nada que renovar.
    const esSondeoDeSesion = urlPeticion.includes('/auth/me') || urlPeticion.includes('/auth/refresh')

      if (response.status === 401 && !esSondeoDeSesion && !(options as any)._reintentado) {
        if (await renovarSesion()) {
          ;(options as any)._reintentado = true
          response._data = await $fetch(request, options as any)
          return
        }
        if (import.meta.client && !window.location.pathname.startsWith('/ingresar')) {
          await navigateTo('/ingresar')
        }
      }

      throw new ApiError(
        problem ?? {
          type: 'about:blank',
          title: 'Error de red',
          status: response.status,
          detail: 'No se pudo contactar al servidor.',
          instance: urlPeticion,
          trace_id: '',
        },
        response.status,
      )
    },
  })

  return { provide: { api } }
})
