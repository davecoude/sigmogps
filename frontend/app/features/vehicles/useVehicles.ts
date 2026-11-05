/** Estado de servidor de la flota (ARQ-10). */
import { useQuery } from '@tanstack/vue-query'
import type { FleetSummary, Paged, VehicleListItem, VehicleStatus } from '~/types/api'

export interface FiltrosVehiculos {
  search?: string
  status?: VehicleStatus | null
  page?: number
  pageSize?: number
}

export function useVehicles(filtros: Ref<FiltrosVehiculos>) {
  const { $api } = useNuxtApp()
  // El polling se detiene cuando la pestaña no está visible (RF-14).
  const visible = useDocumentVisibility()

  return useQuery({
    queryKey: ['vehicles', filtros],
    queryFn: () =>
      $api<Paged<VehicleListItem>>('/vehicles', {
        query: {
          search: filtros.value.search || undefined,
          status: filtros.value.status || undefined,
          page: filtros.value.page ?? 1,
          page_size: filtros.value.pageSize ?? 50,
        },
      }),
    refetchInterval: () => (visible.value ? 10_000 : false),
    placeholderData: (anterior) => anterior,
  })
}

export function useFleetSummary() {
  const { $api } = useNuxtApp()
  const visible = useDocumentVisibility()

  return useQuery({
    queryKey: ['fleet-summary'],
    queryFn: () => $api<FleetSummary>('/vehicles/summary'),
    refetchInterval: () => (visible.value ? 15_000 : false),
  })
}

/** Pausa el refresco cuando la pestaña está oculta. */
function useDocumentVisibility() {
  const visible = ref(true)
  onMounted(() => {
    const actualizar = () => (visible.value = document.visibilityState === 'visible')
    actualizar()
    document.addEventListener('visibilitychange', actualizar)
    onBeforeUnmount(() => document.removeEventListener('visibilitychange', actualizar))
  })
  return visible
}
