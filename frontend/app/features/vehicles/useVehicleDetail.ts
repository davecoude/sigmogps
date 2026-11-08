/** Estado de servidor del detalle de un vehículo (RF-12, RF-13, RF-09). */
import { useQuery } from '@tanstack/vue-query'
import type { VehicleDetail } from '~/types/api'
import type { Passenger } from '~/features/passengers/usePassengers'

export function useVehicleDetail(id: Ref<number>) {
  const { $api } = useNuxtApp()
  const visible = useDocumentVisibility()

  return useQuery({
    queryKey: ['vehicle', id],
    queryFn: () => $api<VehicleDetail>(`/vehicles/${id.value}`),
    refetchInterval: () => (visible.value ? 10_000 : false),
    placeholderData: (anterior) => anterior,
  })
}

/**
 * Las asignaciones viven en otra consulta: el detalle del vehículo se dibuja
 * aunque la lectura de tags de Wialon falle o tarde.
 */
export function useVehiclePassengers(id: Ref<number>) {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['vehicle-passengers', id],
    queryFn: () => $api<Passenger[]>(`/vehicles/${id.value}/passengers`),
  })
}
