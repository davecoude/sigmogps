<script setup lang="ts">
import { mensajeDeError } from '~/composables/useAuth'

definePageMeta({ middleware: 'guest', layout: false })
useHead({ title: 'Iniciar sesión · sigmoGPS' })

const { ingresar } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const cargando = ref(false)

async function enviar() {
  error.value = null
  cargando.value = true
  try {
    const me = await ingresar(email.value, password.value)
    const destino = (route.query.destino as string) || '/app/mapa'
    await navigateTo(me.must_change_password ? '/cambiar-clave' : destino)
  } catch (e) {
    error.value = mensajeDeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <main class="relative min-h-dvh">
    <!-- El mapa de fondo anticipa de qué se trata el producto. -->
    <!-- `isolate` encierra los z-index internos de Leaflet (sus paneles usan
         400 y taparían el formulario). -->
    <div class="absolute inset-0 isolate z-0" aria-hidden="true">
      <ClientOnly>
        <BaseMap :interactive="false" :zoom="11" />
      </ClientOnly>
      <div class="absolute inset-0 bg-gradient-to-r from-wash via-wash/85 to-transparent" />
    </div>

    <div class="relative z-10 flex min-h-dvh items-center px-4 sm:px-8 lg:px-16">
      <div class="w-full max-w-sm rounded-lg border border-line bg-paper p-7 shadow-xl">
        <NuxtLink to="/" class="mb-6 inline-flex items-center gap-2 text-lg font-bold tracking-tight">
          <svg viewBox="0 0 24 24" class="size-5" aria-hidden="true">
            <path d="M12 22c4.5-5.2 7-9 7-12a7 7 0 1 0-14 0c0 3 2.5 6.8 7 12z" fill="#EB162C" />
            <circle cx="12" cy="10" r="2.7" fill="#fff" />
          </svg>
          sigmo<span class="text-brand">GPS</span>
        </NuxtLink>

        <h1 class="text-xl font-semibold">Iniciar sesión</h1>
        <p class="mt-1 text-sm text-muted">Panel de monitoreo de flota.</p>

        <form class="mt-6 grid gap-4" novalidate @submit.prevent="enviar">
          <AppAlert v-if="error">{{ error }}</AppAlert>

          <AppField
            id="email"
            v-model="email"
            label="Correo"
            type="email"
            autocomplete="username"
            required
          />
          <AppField
            id="password"
            v-model="password"
            label="Contraseña"
            type="password"
            autocomplete="current-password"
            required
          />

          <AppButton type="submit" :loading="cargando" block>
            {{ cargando ? 'Entrando…' : 'Entrar' }}
          </AppButton>
        </form>

        <p class="mt-5 text-xs text-muted">
          Sesión protegida con cookie HttpOnly. Tras cinco intentos fallidos la cuenta se
          bloquea quince minutos.
        </p>
      </div>
    </div>
  </main>
</template>
