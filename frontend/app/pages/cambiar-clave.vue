<script setup lang="ts">
import { mensajeDeError } from '~/composables/useAuth'

definePageMeta({ middleware: 'auth', layout: false })
useHead({ title: 'Cambiar contraseña · sigmoGPS' })

const { user, cambiarClave } = useAuth()

const actual = ref('')
const nueva = ref('')
const confirmacion = ref('')
const error = ref<string | null>(null)
const cargando = ref(false)

const noCoinciden = computed(
  () => confirmacion.value.length > 0 && nueva.value !== confirmacion.value,
)

async function enviar() {
  error.value = null
  if (noCoinciden.value) {
    error.value = 'Las contraseñas no coinciden.'
    return
  }
  cargando.value = true
  try {
    await cambiarClave(actual.value, nueva.value)
    await navigateTo('/ingresar')
  } catch (e) {
    error.value = mensajeDeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <main class="grid min-h-dvh place-items-center bg-wash px-4 py-10">
    <div class="w-full max-w-sm rounded-lg border border-line bg-paper p-7 shadow-md">
      <h1 class="text-xl font-semibold">Cambia tu contraseña</h1>
      <p class="mt-1 text-sm text-muted">
        Es tu primer ingreso{{ user ? `, ${user.full_name}` : '' }}. Define una contraseña propia
        antes de continuar.
      </p>

      <form class="mt-6 grid gap-4" novalidate @submit.prevent="enviar">
        <AppAlert v-if="error">{{ error }}</AppAlert>

        <AppField
          id="actual"
          v-model="actual"
          label="Contraseña actual"
          type="password"
          autocomplete="current-password"
          required
        />
        <AppField
          id="nueva"
          v-model="nueva"
          label="Nueva contraseña"
          type="password"
          autocomplete="new-password"
          hint="Mínimo 12 caracteres, con mayúscula, minúscula, dígito y símbolo."
          required
        />
        <AppField
          id="confirmacion"
          v-model="confirmacion"
          label="Repite la nueva contraseña"
          type="password"
          autocomplete="new-password"
          :error="noCoinciden ? 'No coincide con la anterior.' : null"
          required
        />

        <AppButton type="submit" :loading="cargando" block>
          {{ cargando ? 'Guardando…' : 'Cambiar contraseña' }}
        </AppButton>
      </form>

      <p class="mt-5 text-xs text-muted">
        Al cambiarla se cierran todas tus sesiones abiertas y tendrás que ingresar de nuevo.
      </p>
    </div>
  </main>
</template>
