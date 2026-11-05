/** Estado de sesión compartido. La cookie vive en el backend; aquí solo el perfil. */
import type { Me } from '~/types/api'
import { ApiError } from '~/plugins/api'

export function useAuth() {
  const user = useState<Me | null>('auth:user', () => null)
  const cargado = useState<boolean>('auth:cargado', () => false)
  const { $api } = useNuxtApp()

  const autenticado = computed(() => user.value !== null)

  /** Permisos efectivos. Ordena la interfaz; el backend es quien protege. */
  function puede(...permisos: string[]): boolean {
    if (!user.value) return false
    return permisos.every((p) => user.value!.permissions.includes(p))
  }

  async function cargarSesion(forzar = false): Promise<Me | null> {
    if (cargado.value && !forzar) return user.value
    try {
      user.value = await $api<Me>('/auth/me')
    } catch {
      user.value = null
    } finally {
      cargado.value = true
    }
    return user.value
  }

  async function ingresar(email: string, password: string): Promise<Me> {
    const me = await $api<Me>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    user.value = me
    cargado.value = true
    return me
  }

  async function salir(): Promise<void> {
    try {
      await $api('/auth/logout', { method: 'POST' })
    } catch {
      // Si el servidor no responde, igual se limpia del lado del cliente.
    }
    user.value = null
    cargado.value = true
    await navigateTo('/ingresar')
  }

  async function cambiarClave(actual: string, nueva: string): Promise<void> {
    await $api('/auth/change-password', {
      method: 'POST',
      body: { current_password: actual, new_password: nueva },
    })
    user.value = null
    cargado.value = true
  }

  return { user, autenticado, cargado, puede, cargarSesion, ingresar, salir, cambiarClave }
}

/** Traduce un error del API a un mensaje para el usuario. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError) {
    const campos = error.problem.errors
    if (campos?.length) return campos.map((c) => c.mensaje).join(' ')
    return error.problem.detail || error.problem.title
  }
  return 'Ocurrió un error inesperado. Intenta de nuevo.'
}
