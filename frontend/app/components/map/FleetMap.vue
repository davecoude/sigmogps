<script setup lang="ts">
import type { Map as LeafletMap, Marker } from 'leaflet'
import type { VehicleListItem } from '~/types/api'

const props = defineProps<{
  vehicles: VehicleListItem[]
  selectedId: number | null
}>()
const emit = defineEmits<{ select: [id: number] }>()

const contenedor = ref<HTMLElement | null>(null)
const mapa = shallowRef<LeafletMap | null>(null)
const marcadores = new Map<number, Marker>()
let L: typeof import('leaflet') | null = null
let cluster: any = null

const COLORES: Record<string, string> = {
  en_movimiento: '#1E8C93',
  detenido: '#6B6B6B',
  sin_senal: '#EB162C',
}

function icono(status: string, seleccionado: boolean) {
  const color = COLORES[status] ?? '#6B6B6B'
  const borde = seleccionado ? '#EEE8F2' : '#FFFFFF'
  const tamano = seleccionado ? 32 : 26
  return L!.divIcon({
    className: '',
    iconSize: [tamano, tamano],
    iconAnchor: [tamano / 2, tamano / 2],
    html: `<span style="display:grid;place-items:center;width:${tamano}px;height:${tamano}px;
      border-radius:50%;background:${color};border:3px solid ${borde};
      box-shadow:0 2px 8px rgba(0,0,0,.45);color:#fff;font-size:11px">▲</span>`,
  })
}

async function construir() {
  if (!contenedor.value) return

  // leaflet.markercluster es un plugin UMD: se engancha al objeto L global,
  // no al namespace del módulo. Hay que publicarlo antes de importarlo.
  const mod = await import('leaflet')
  L = ((mod as any).default ?? mod) as typeof import('leaflet')
  ;(window as any).L = L
  await import('leaflet.markercluster')

  mapa.value = L.map(contenedor.value, {
    center: [4.711, -74.0721],
    zoom: 11,
    zoomControl: true,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; colaboradores de OpenStreetMap',
  }).addTo(mapa.value)

  // Agrupación cuando hay marcadores cercanos (RF-11).
  cluster = (L as any).markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 48,
  })
  mapa.value.addLayer(cluster)
  pintar()
}

function pintar() {
  if (!mapa.value || !L || !cluster) return

  const vistos = new Set<number>()

  for (const v of props.vehicles) {
    if (!v.position) continue
    vistos.add(v.id)
    const latlng: [number, number] = [v.position.latitude, v.position.longitude]
    const existente = marcadores.get(v.id)

    if (existente) {
      existente.setLatLng(latlng)
      existente.setIcon(icono(v.status, v.id === props.selectedId))
    } else {
      const m = L.marker(latlng, {
        icon: icono(v.status, v.id === props.selectedId),
        title: v.display_name,
        keyboard: true,
        alt: v.display_name,
      })
      m.on('click', () => emit('select', v.id))
      marcadores.set(v.id, m)
      cluster.addLayer(m)
    }
  }

  for (const [id, m] of marcadores) {
    if (!vistos.has(id)) {
      cluster.removeLayer(m)
      marcadores.delete(id)
    }
  }
}

function centrarEn(id: number | null) {
  if (!id || !mapa.value) return
  const v = props.vehicles.find((x) => x.id === id)
  if (!v?.position) return
  mapa.value.setView([v.position.latitude, v.position.longitude], 15, { animate: true })
}

watch(() => props.vehicles, pintar, { deep: true })
watch(() => props.selectedId, (id) => { pintar(); centrarEn(id) })

onMounted(construir)
onBeforeUnmount(() => {
  mapa.value?.remove()
  mapa.value = null
  marcadores.clear()
})
</script>

<template>
  <div ref="contenedor" class="size-full bg-console-2" role="application" aria-label="Mapa de la flota" />
</template>

<style>
/* El agrupador de Leaflet trae estilos propios; se reemplazan por la paleta. */
.marker-cluster {
  background: rgba(168, 26, 43, 0.25);
  border-radius: 50%;
}
.marker-cluster div {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  margin: 3px;
  border-radius: 50%;
  background: #a81a2b;
  color: #fff;
  font: 600 12px/1 Inter, sans-serif;
}
.leaflet-container {
  background: #1a1722;
}
</style>
