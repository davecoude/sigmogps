/** Estado de servidor del detalle de un vehículo (RF-12, RF-13, RF-09, RF-19). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
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

/**
 * Campos personalizados del vehículo (RF-19, RF-20).
 *
 * El endpoint devuelve el vehículo ya actualizado y confirmado contra Wialon,
 * así que se escribe en el caché en vez de volver a leer: evita una consulta y
 * evita la ventana en la que Wialon aún no propagó el cambio.
 */
export function useVehicleCustomFields(id: Ref<number>) {
  const { $api } = useNuxtApp()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (campos: Record<string, string>) =>
      $api<VehicleDetail>(`/vehicles/${id.value}/custom-fields`, {
        method: 'PUT',
        body: { custom_fields: campos },
      }),
    onSuccess: (actualizado) => {
      qc.setQueryData(['vehicle', id], actualizado)
      // La placa vive en un campo personalizado, así que el mapa y la lista
      // pueden haber cambiado de nombre visible.
      qc.invalidateQueries({ queryKey: ['vehicles'] })
    },
  })
}
