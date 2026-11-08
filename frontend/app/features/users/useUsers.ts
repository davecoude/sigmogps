import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'

export interface RoleOption {
  id: number
  name: string
  description: string
  permissions: string[]
}

export interface ManagedUser {
  id: string
  email: string
  full_name: string
  role_name: string
  is_active: boolean
  must_change_password: boolean
  is_locked: boolean
  last_login_at: string | null
  created_at: string
}

export interface TemporaryPassword {
  user_id: string
  email: string
  temporary_password: string
}

export function useRoles() {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['roles'],
    queryFn: () => $api<RoleOption[]>('/users/roles'),
    staleTime: 5 * 60_000, // los roles los siembra el código; no cambian solos
  })
}

export function useUsers(search: Ref<string>) {
  const { $api } = useNuxtApp()
  return useQuery({
    queryKey: ['users', search],
    queryFn: () => $api<ManagedUser[]>('/users', { query: { search: search.value || undefined } }),
    placeholderData: (anterior) => anterior,
  })
}

export function useUserMutations() {
  const { $api } = useNuxtApp()
  const qc = useQueryClient()

  const invalidar = () => qc.invalidateQueries({ queryKey: ['users'] })

  /**
   * PATCH devuelve el usuario ya actualizado, así que se escribe directo en la
   * caché en vez de volver a pedir la lista entera. Ahorra un viaje completo a
   * Neon y la fila cambia en el mismo instante. La relectura en segundo plano
   * confirma después, sin que el usuario la espere.
   */
  const aplicarEnCache = (actualizado: ManagedUser) => {
    qc.setQueriesData<ManagedUser[]>({ queryKey: ['users'] }, (lista) =>
      lista?.map((u) => (u.id === actualizado.id ? actualizado : u)),
    )
  }

  const crear = useMutation({
    mutationFn: (datos: { email: string; full_name: string; role_id: number }) =>
      $api<TemporaryPassword>('/users', { method: 'POST', body: datos }),
    // Un alta sí necesita releer: la respuesta trae la clave, no la fila.
    onSuccess: invalidar,
  })

  const cambiarRol = useMutation({
    mutationFn: ({ id, roleId }: { id: string; roleId: number }) =>
      $api<ManagedUser>(`/users/${id}/role`, { method: 'PATCH', body: { role_id: roleId } }),
    onSuccess: (actualizado) => {
      aplicarEnCache(actualizado)
      invalidar()
    },
  })

  const cambiarEstado = useMutation({
    mutationFn: ({ id, activo }: { id: string; activo: boolean }) =>
      $api<ManagedUser>(`/users/${id}/active`, { method: 'PATCH', body: { is_active: activo } }),
    onSuccess: (actualizado) => {
      aplicarEnCache(actualizado)
      invalidar()
    },
  })

  const restablecer = useMutation({
    mutationFn: (id: string) =>
      $api<TemporaryPassword>(`/users/${id}/reset-password`, { method: 'POST' }),
    onSuccess: invalidar,
  })

  return { crear, cambiarRol, cambiarEstado, restablecer }
}
