import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { Paged } from '~/types/api'

export interface Driver {
  id: number
  name: string
  code: string | null
  phone: string | null
  description: string | null
  bound_unit_id: number | null
  custom_fields: Record<string, string>
}

export interface DriverWrite {
  name: string
  code?: string | null
  phone?: string | null
  description?: string | null
  custom_fields?: Record<string, string> | null
}

export interface FiltrosConductores {
  search: string
  page: number
  pageSize: number
}

export function useDrivers(filtros: Ref<FiltrosConductores>) {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['drivers', filtros],
    queryFn: () =>
      $api<Paged<Driver>>('/drivers', {
        query: {
          search: filtros.value.search || undefined,
          page: filtros.value.page,
          page_size: filtros.value.pageSize,
        },
      }),
    placeholderData: (anterior) => anterior,
  })
}

export function useDriverMutations() {
  const { $api } = useNuxtApp()
  const qc = useQueryClient()

  // Los vehículos también cambian: el conductor vinculado se muestra ahí (RF-13).
  const invalidar = () => {
    qc.invalidateQueries({ queryKey: ['drivers'] })
    qc.invalidateQueries({ queryKey: ['vehicles'] })
    qc.invalidateQueries({ queryKey: ['fleet-summary'] })
  }

  /** La respuesta ya trae el conductor actualizado: evita releer la página. */
  const aplicarEnCache = (actualizado: Driver) => {
    qc.setQueriesData<Paged<Driver>>({ queryKey: ['drivers'] }, (pagina) =>
      pagina
        ? { ...pagina, items: pagina.items.map((d) => (d.id === actualizado.id ? actualizado : d)) }
        : pagina,
    )
  }

  const crear = useMutation({
    mutationFn: (datos: DriverWrite) => $api<Driver>('/drivers', { method: 'POST', body: datos }),
    onSuccess: invalidar,
  })

  const editar = useMutation({
    mutationFn: ({ id, datos }: { id: number; datos: DriverWrite }) =>
      $api<Driver>(`/drivers/${id}`, { method: 'PUT', body: datos }),
    onSuccess: (actualizado) => {
      aplicarEnCache(actualizado)
      invalidar()
    },
  })

  const eliminar = useMutation({
    mutationFn: (id: number) => $api(`/drivers/${id}`, { method: 'DELETE' }),
    onSuccess: invalidar,
  })

  const vincular = useMutation({
    mutationFn: ({ id, unitId }: { id: number; unitId: number }) =>
      $api(`/drivers/${id}/bind`, { method: 'POST', body: { unit_id: unitId } }),
    onSuccess: invalidar,
  })

  const desvincular = useMutation({
    mutationFn: ({ id, unitId }: { id: number; unitId: number }) =>
      $api(`/drivers/${id}/unbind`, { method: 'POST', body: { unit_id: unitId } }),
    onSuccess: invalidar,
  })

  return { crear, editar, eliminar, vincular, desvincular }
}
