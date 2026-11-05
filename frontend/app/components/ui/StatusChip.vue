<script setup lang="ts">
import type { VehicleStatus } from '~/types/api'

const props = defineProps<{ status: VehicleStatus; dark?: boolean }>()

const ETIQUETAS: Record<VehicleStatus, string> = {
  en_movimiento: 'En movimiento',
  detenido: 'Detenido',
  sin_senal: 'Sin señal',
}

const clases = computed(() => {
  if (props.dark) {
    return {
      en_movimiento: 'bg-teal-soft/10 text-teal-dark',
      detenido: 'bg-console-2 text-console-muted border border-console-line',
      sin_senal: 'bg-brand-soft/10 text-brand-dark',
    }[props.status]
  }
  return {
    en_movimiento: 'bg-teal-soft text-teal-ink',
    detenido: 'bg-wash text-muted border border-line',
    sin_senal: 'bg-brand-soft text-brand',
  }[props.status]
})
</script>

<template>
  <!-- El color nunca viaja solo: el punto y el texto lo acompañan (UX-03). -->
  <span
    class="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold"
    :class="clases"
  >
    <span class="size-1.5 rounded-full bg-current" aria-hidden="true" />
    {{ ETIQUETAS[status] }}
  </span>
</template>
