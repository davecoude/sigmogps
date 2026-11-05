<script setup lang="ts">
/**
 * Mapa Leaflet. Se importa dinámicamente porque Leaflet toca `window`
 * y no puede ejecutarse durante el renderizado en servidor.
 */
import type { Map as LeafletMap } from 'leaflet'

const props = withDefaults(
  defineProps<{
    center?: [number, number]
    zoom?: number
    interactive?: boolean
  }>(),
  { center: () => [4.711, -74.0721], zoom: 12, interactive: true }, // Bogotá
)

const contenedor = ref<HTMLElement | null>(null)
const mapa = shallowRef<LeafletMap | null>(null)

onMounted(async () => {
  const L = await import('leaflet')
  if (!contenedor.value) return

  mapa.value = L.map(contenedor.value, {
    center: props.center,
    zoom: props.zoom,
    zoomControl: props.interactive,
    dragging: props.interactive,
    scrollWheelZoom: props.interactive,
    doubleClickZoom: props.interactive,
    attributionControl: true,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; colaboradores de OpenStreetMap',
  }).addTo(mapa.value)
})

onBeforeUnmount(() => {
  mapa.value?.remove()
  mapa.value = null
})

defineExpose({ mapa })
</script>

<template>
  <div ref="contenedor" class="size-full" role="application" aria-label="Mapa de la flota">
    <slot :mapa="mapa" />
  </div>
</template>
