<script setup lang="ts">
/**
 * Pantalla de arranque (DEP-04).
 *
 * El panel no se renderiza en el servidor y la primera lectura de Wialon
 * tarda unos segundos; en Render, además, el plan gratuito suspende el
 * servicio por inactividad. Sin esto el usuario mira una pantalla en blanco
 * y concluye que la aplicación está rota.
 */
const segundos = ref(0)
let reloj: ReturnType<typeof setInterval>

onMounted(() => {
  reloj = setInterval(() => (segundos.value += 1), 1000)
})
onBeforeUnmount(() => clearInterval(reloj))

const mensaje = computed(() => {
  if (segundos.value < 4) return 'Conectando con el servidor…'
  if (segundos.value < 12) return 'Iniciando el servidor. Puede tardar hasta un minuto.'
  return 'Sigue iniciando. El plan gratuito suspende el servicio por inactividad.'
})
</script>

<template>
  <div class="grid min-h-dvh place-items-center bg-console px-6 text-console-ink">
    <div class="grid justify-items-center gap-4 text-center">
      <span
        class="size-8 animate-spin rounded-full border-2 border-console-line border-t-brand-dark"
        aria-hidden="true"
      />
      <p class="font-semibold">{{ mensaje }}</p>
      <p v-if="segundos > 3" class="font-mono text-xs text-console-muted tabular">
        {{ segundos }} s
      </p>
    </div>
  </div>
</template>
