import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { Paged } from '~/types/api'

export interface Passenger {
  id: number
  name: string
  code: string | null
  custom_fields: Record<string, string>
  bound_unit_id: number | null
}

export interface PassengerWrite {
  name: string
  code?: string | null
  custom_fields?: Record<string, string> | null
}

export interface FiltrosPasajeros {
  search: string
  page: number
  pageSize: number
}

export function usePassengers(filtros: Ref<FiltrosPasajeros>) {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['passengers', filtros],
    queryFn: () =>
      $api<Paged<Passenger>>('/passengers', {
        query: {
          search: filtros.value.search || undefined,
          page: filtros.value.page,
          page_size: filtros.value.pageSize,
        },
      }),
    placeholderData: (anterior) => anterior,
  })
}

export function usePassengerMutations() {
  const { $api } = useNuxtApp()
  const qc = useQueryClient()

  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ['passengers'] })
    qc.invalidateQueries({ queryKey: ['vehicles'] })
  }

  /** La respuesta ya trae el pasajero actualizado: evita releer la página. */
  const aplicarEnCache = (actualizado: Passenger) => {
    qc.setQueriesData<Paged<Passenger>>({ queryKey: ['passengers'] }, (pagina) =>
      pagina
        ? {
            ...pagina,
            items: pagina.items.map((p) => (p.id === actualizado.id ? actualizado : p)),
          }
        : pagina,
    )
  }

  const crear = useMutation({
    mutationFn: (datos: PassengerWrite) =>
      $api<Passenger>('/passengers', { method: 'POST', body: datos }),
    onSuccess: invalidar,
  })

  const editar = useMutation({
    mutationFn: ({ id, datos }: { id: number; datos: PassengerWrite }) =>
      $api<Passenger>(`/passengers/${id}`, { method: 'PUT', body: datos }),
    onSuccess: (actualizado) => {
      aplicarEnCache(actualizado)
      invalidar()
    },
  })

  const guardarCampos = useMutation({
    mutationFn: ({ id, campos }: { id: number; campos: Record<string, string> }) =>
      $api<Passenger>(`/passengers/${id}/custom-fields`, {
        method: 'PUT',
        body: { custom_fields: campos },
      }),
    onSuccess: (actualizado) => {
      aplicarEnCache(actualizado)
      invalidar()
    },
  })

  const eliminar = useMutation({
    mutationFn: (id: number) => $api(`/passengers/${id}`, { method: 'DELETE' }),
    onSuccess: invalidar,
  })

  const asignar = useMutation({
    mutationFn: ({ id, unitId }: { id: number; unitId: number }) =>
      $api(`/passengers/${id}/assign`, { method: 'POST', body: { unit_id: unitId } }),
    onSuccess: invalidar,
  })

  const desasignar = useMutation({
    mutationFn: ({ id, unitId }: { id: number; unitId: number }) =>
      $api(`/passengers/${id}/unassign`, { method: 'POST', body: { unit_id: unitId } }),
    onSuccess: invalidar,
  })

  return { crear, editar, guardarCampos, eliminar, asignar, desasignar }
}
