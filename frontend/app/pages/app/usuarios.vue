<script setup lang="ts">
import { mensajeDeError } from '~/composables/useAuth'
import type { ManagedUser, TemporaryPassword } from '~/features/users/useUsers'

definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'users:manage' })
useHead({ title: 'Usuarios · sigmoGPS' })

const { user: actual } = useAuth()
const toast = useToast()

const busqueda = ref('')
const { data: usuarios, isPending, isError, error, refetch, isFetching } = useUsers(busqueda)
const { data: roles } = useRoles()
const { crear, cambiarRol, cambiarEstado, restablecer } = useUserMutations()

const ocupado = ref<string | null>(null)
const modal = ref<'ninguno' | 'crear' | 'clave' | 'desactivar'>('ninguno')
const guardando = ref(false)

// ── crear ──
const form = reactive({ email: '', full_name: '', role_id: null as number | null })
const errorForm = ref<string | null>(null)

function abrirCrear() {
  Object.assign(form, { email: '', full_name: '', role_id: roles.value?.[1]?.id ?? null })
  errorForm.value = null
  modal.value = 'crear'
}

// ── contraseña temporal: se muestra una sola vez ──
const credencial = ref<TemporaryPassword | null>(null)
const copiada = ref(false)

function mostrarCredencial(c: TemporaryPassword) {
  credencial.value = c
  copiada.value = false
  modal.value = 'clave'
}

async function copiar() {
  if (!credencial.value) return
  try {
    await navigator.clipboard.writeText(credencial.value.temporary_password)
    copiada.value = true
  } catch {
    toast.aviso('No se pudo copiar. Selecciona el texto manualmente.')
  }
}

async function guardarNuevo() {
  errorForm.value = null
  if (!form.email.trim() || !form.full_name.trim() || !form.role_id) {
    errorForm.value = 'Completa correo, nombre y rol.'
    return
  }
  guardando.value = true
  try {
    const c = await crear.mutateAsync({
      email: form.email.trim(),
      full_name: form.full_name.trim(),
      role_id: form.role_id,
    })
    mostrarCredencial(c)
  } catch (e) {
    errorForm.value = mensajeDeError(e)
  } finally {
    guardando.value = false
  }
}

// ── rol ──
async function alCambiarRol(u: ManagedUser, roleId: number) {
  ocupado.value = u.id
  try {
    await cambiarRol.mutateAsync({ id: u.id, roleId })
    toast.exito(`Rol de ${u.full_name} actualizado.`)
  } catch (e) {
    toast.error(mensajeDeError(e))
    await refetch()
  } finally {
    ocupado.value = null
  }
}

// ── activar / desactivar ──
const aDesactivar = ref<ManagedUser | null>(null)

async function alternarEstado(u: ManagedUser) {
  if (u.is_active) {
    aDesactivar.value = u
    modal.value = 'desactivar'
    return
  }
  ocupado.value = u.id
  try {
    await cambiarEstado.mutateAsync({ id: u.id, activo: true })
    toast.exito(`${u.full_name} reactivado.`)
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    ocupado.value = null
  }
}

async function confirmarDesactivar() {
  if (!aDesactivar.value) return
  const nombre = aDesactivar.value.full_name
  guardando.value = true
  try {
    await cambiarEstado.mutateAsync({ id: aDesactivar.value.id, activo: false })
    toast.exito(`${nombre} desactivado. Sus sesiones se cerraron.`)
    modal.value = 'ninguno'
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    guardando.value = false
  }
}

// ── restablecer ──
async function alRestablecer(u: ManagedUser) {
  ocupado.value = u.id
  try {
    mostrarCredencial(await restablecer.mutateAsync(u.id))
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    ocupado.value = null
  }
}

function fecha(iso: string | null) {
  if (!iso) return 'Nunca'
  return new Date(iso).toLocaleString('es-CO', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Bogota',
  })
}
</script>

<template>
  <div class="flex h-dvh flex-col">
    <header
      class="flex flex-wrap items-center gap-3 border-b p-4"
      :style="{ borderColor: 'var(--border)' }"
    >
      <div class="mr-auto flex items-baseline gap-3">
        <h1 class="text-lg font-semibold">Usuarios</h1>
        <span
          v-if="usuarios?.length"
          class="font-mono text-xs tabular"
          :style="{ color: 'var(--on-surface-muted)' }"
        >
          {{ usuarios.length }}
        </span>
        <span
          v-if="isFetching && !isPending"
          class="size-3 animate-spin rounded-full border-2 border-t-transparent"
          :style="{ borderColor: 'var(--border-strong)', borderTopColor: 'transparent' }"
          aria-hidden="true"
        />
      </div>

      <label class="sr-only" for="buscar-usuario">Buscar usuario</label>
      <input
        id="buscar-usuario"
        v-model="busqueda"
        type="search"
        placeholder="Correo o nombre"
        class="field-input max-w-xs"
      />

      <AppButton @click="abrirCrear">Nuevo usuario</AppButton>
    </header>

    <div class="min-h-0 flex-1 overflow-auto p-4">
      <div v-if="isPending" class="grid gap-2" aria-busy="true">
        <div
          v-for="n in 4"
          :key="n"
          class="h-14 animate-pulse rounded-md"
          :style="{ background: 'var(--surface)' }"
        />
      </div>

      <div v-else-if="isError" class="mx-auto max-w-md">
        <AppAlert>{{ (error as Error)?.message ?? 'No se pudieron cargar los usuarios.' }}</AppAlert>
        <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
      </div>

      <div v-else-if="!usuarios?.length" class="grid justify-items-center gap-2 py-16 text-center">
        <span class="text-3xl" aria-hidden="true">⚿</span>
        <p class="font-semibold">Ningún usuario coincide</p>
        <p class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
          Cambia el texto de búsqueda.
        </p>
      </div>

      <div v-else class="overflow-x-auto rounded-md border" :style="{ borderColor: 'var(--border)' }">
        <table class="w-full min-w-[52rem] border-collapse text-sm">
          <caption class="sr-only">Usuarios de la plataforma, su rol y su estado</caption>
          <thead>
            <tr
              class="text-left text-xs font-semibold"
              :style="{ background: 'var(--surface)', color: 'var(--on-surface-soft)' }"
            >
              <th scope="col" class="p-3">Usuario</th>
              <th scope="col" class="p-3">Rol</th>
              <th scope="col" class="p-3">Estado</th>
              <th scope="col" class="p-3">Último ingreso</th>
              <th scope="col" class="p-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="u in usuarios"
              :key="u.id"
              class="border-t transition-opacity"
              :style="{ borderColor: 'var(--border)' }"
              :class="ocupado === u.id && 'opacity-50'"
            >
              <td class="p-3">
                <div class="font-medium">
                  {{ u.full_name }}
                  <span
                    v-if="u.id === actual?.id"
                    class="ml-1.5 text-xs font-normal"
                    :style="{ color: 'var(--on-surface-muted)' }"
                  >
                    (tú)
                  </span>
                </div>
                <div class="font-mono text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                  {{ u.email }}
                </div>
              </td>

              <td class="p-3">
                <label class="sr-only" :for="`rol-${u.id}`">Rol de {{ u.full_name }}</label>
                <select
                  :id="`rol-${u.id}`"
                  class="field-input py-1.5 text-xs"
                  :value="roles?.find((r) => r.name === u.role_name)?.id"
                  :disabled="ocupado === u.id"
                  @change="alCambiarRol(u, Number(($event.target as HTMLSelectElement).value))"
                >
                  <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </td>

              <td class="p-3">
                <div class="flex flex-wrap gap-1.5">
                  <span
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold"
                    :class="u.is_active ? 'bg-teal-soft/10 text-teal-dark' : 'bg-brand-soft/10 text-brand-dark'"
                  >
                    <span class="size-1.5 rounded-full bg-current" aria-hidden="true" />
                    {{ u.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                  <span
                    v-if="u.is_locked"
                    class="rounded-full bg-ochre/15 px-2.5 py-0.5 text-xs font-semibold text-ochre"
                  >
                    Bloqueado
                  </span>
                  <span
                    v-if="u.must_change_password"
                    class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                    :style="{ background: 'var(--surface-sunken)', color: 'var(--on-surface-muted)' }"
                  >
                    Clave pendiente
                  </span>
                </div>
              </td>

              <td class="p-3 font-mono text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                {{ fecha(u.last_login_at) }}
              </td>

              <td class="p-3">
                <div class="flex justify-end gap-1.5">
                  <button
                    type="button"
                    class="btn-row"
                    :disabled="ocupado === u.id"
                    @click="alRestablecer(u)"
                  >
                    Restablecer clave
                  </button>
                  <button
                    type="button"
                    class="btn-row"
                    :class="u.is_active && 'btn-row-danger'"
                    :disabled="ocupado === u.id || u.id === actual?.id"
                    :title="u.id === actual?.id ? 'No puedes desactivar tu propia cuenta' : undefined"
                    @click="alternarEstado(u)"
                  >
                    {{ u.is_active ? 'Desactivar' : 'Activar' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ───────── crear ───────── -->
    <AppModal
      v-if="modal === 'crear'"
      titulo="Nuevo usuario"
      descripcion="Recibirá una contraseña temporal y deberá cambiarla al entrar."
      @cerrar="modal = 'ninguno'"
    >
      <form class="grid gap-4" novalidate @submit.prevent="guardarNuevo">
        <AppAlert v-if="errorForm">{{ errorForm }}</AppAlert>

        <AppField id="u-email" v-model="form.email" label="Correo" type="email" required placeholder="operador@sigmogps.app" />
        <AppField id="u-name" v-model="form.full_name" label="Nombre completo" required placeholder="Carolina Rueda" />

        <AppSelect id="u-role" v-model="form.role_id" label="Rol">
          <option v-for="r in roles" :key="r.id" :value="r.id">
            {{ r.name }} — {{ r.description }}
          </option>
        </AppSelect>

        <div class="flex justify-end gap-2 pt-1">
          <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
          <AppButton type="submit" :loading="guardando">Crear usuario</AppButton>
        </div>
      </form>
    </AppModal>

    <!-- ───────── contraseña temporal ───────── -->
    <AppModal
      v-if="modal === 'clave'"
      titulo="Contraseña temporal"
      descripcion="Se muestra una sola vez. Cópiala antes de cerrar."
      @cerrar="modal = 'ninguno'"
    >
      <p class="text-sm">
        Entrégasela a <strong>{{ credencial?.email }}</strong>. La cambiará en su primer ingreso.
      </p>

      <div
        class="mt-4 flex items-center gap-3 rounded-md border p-3"
        :style="{ borderColor: 'var(--border-strong)', background: 'var(--surface-sunken)' }"
      >
        <code class="min-w-0 flex-1 break-all font-mono text-sm">
          {{ credencial?.temporary_password }}
        </code>
        <AppButton variant="ghost" @click="copiar">
          {{ copiada ? 'Copiada' : 'Copiar' }}
        </AppButton>
      </div>

      <AppAlert tone="warn" class="mt-4">
        No volverá a mostrarse. Si la pierdes, usa «Restablecer clave».
      </AppAlert>

      <div class="mt-5 flex justify-end">
        <AppButton @click="modal = 'ninguno'">Listo</AppButton>
      </div>
    </AppModal>

    <!-- ───────── desactivar ───────── -->
    <AppModal
      v-if="modal === 'desactivar'"
      titulo="Desactivar usuario"
      descripcion="Se cerrarán todas sus sesiones abiertas."
      @cerrar="modal = 'ninguno'"
    >
      <p class="text-sm">
        <strong>{{ aDesactivar?.full_name }}</strong> no podrá ingresar hasta que lo reactives.
      </p>
      <div class="mt-5 flex justify-end gap-2">
        <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
        <AppButton variant="danger" :loading="guardando" @click="confirmarDesactivar">
          Desactivar
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
