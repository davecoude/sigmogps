import { useQuery } from '@tanstack/vue-query'
import type { Paged } from '~/types/api'

export interface AuditEntry {
  id: string
  action: string
  user_email: string | null
  entity_type: string | null
  entity_id: string | null
  success: boolean
  detail: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface FiltrosAuditoria {
  action: string
  search: string
  onlyFailures: boolean
  page: number
  pageSize: number
}

export function useAuditEntries(filtros: Ref<FiltrosAuditoria>) {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['audit', filtros],
    queryFn: () =>
      $api<Paged<AuditEntry>>('/audit', {
        query: {
          action: filtros.value.action || undefined,
          search: filtros.value.search || undefined,
          only_failures: filtros.value.onlyFailures || undefined,
          page: filtros.value.page,
          page_size: filtros.value.pageSize,
        },
      }),
    placeholderData: (anterior) => anterior,
  })
}

export function useAuditActions() {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['audit-actions'],
    queryFn: () => $api<string[]>('/audit/actions'),
    staleTime: 60_000,
  })
}
