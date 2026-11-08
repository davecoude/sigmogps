<script setup lang="ts">
import { mensajeDeError } from '~/composables/useAuth'
import type { Driver, DriverWrite } from '~/features/drivers/useDrivers'
import type { VehicleListItem } from '~/types/api'

definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'drivers:read' })
useHead({ title: 'Conductores · sigmoGPS' })

const { puede } = useAuth()
const toast = useToast()

const puedeEditar = computed(() => puede('drivers:write'))
const puedeVincular = computed(() => puede('bindings:write'))

const busqueda = ref('')
const pagina = ref(1)

// El tamaño de página lo decide el alto de la ventana, no una constante.
const zonaTabla = ref<HTMLElement | null>(null)
const { filas: porPagina } = useFilasQueCaben(zonaTabla)

// Al cambiar el tamaño de página, la fila que el usuario miraba debe seguir
// visible: se recalcula a qué página pertenece.
watch(porPagina, (nuevo, anterior) => {
  if (!anterior || !nuevo) return
  const primerRegistro = (pagina.value - 1) * anterior
  pagina.value = Math.floor(primerRegistro / nuevo) + 1
})

const busquedaDiferida = ref('')
let temporizador: ReturnType<typeof setTimeout>
watch(busqueda, (v) => {
  clearTimeout(temporizador)
  temporizador = setTimeout(() => {
    busquedaDiferida.value = v
    pagina.value = 1
  }, 350)
})

const filtros = computed(() => ({
  search: busquedaDiferida.value,
  page: pagina.value,
  pageSize: porPagina.value,
}))

/** Número de registro dentro del total, no dentro de la página. */
function numeroDeFila(indice: number) {
  return (meta.value ? (meta.value.page - 1) * meta.value.page_size : 0) + indice + 1
}

const { data, isPending, isError, error, refetch, isFetching } = useDrivers(filtros)
const conductores = computed(() => data.value?.items ?? [])
const meta = computed(() => data.value?.meta)
const { crear, editar, eliminar, vincular, desvincular } = useDriverMutations()

const filtrosVehiculos = computed(() => ({ pageSize: 100 }))
const { data: paginaVehiculos } = useVehicles(filtrosVehiculos)
const vehiculos = computed<VehicleListItem[]>(() => paginaVehiculos.value?.items ?? [])

function nombreUnidad(id: number | null) {
  if (!id) return null
  return vehiculos.value.find((v) => v.id === id)?.display_name ?? `Unidad ${id}`
}

/** Id de la fila en curso: la acción se deshabilita mientras viaja. */
const ocupado = ref<number | null>(null)

// ── formulario ──
const modal = ref<'ninguno' | 'formulario' | 'eliminar' | 'vincular'>('ninguno')
const enEdicion = ref<Driver | null>(null)
const guardando = ref(false)
const form = reactive({ name: '', code: '', phone: '', description: '' })
const errorForm = ref<string | null>(null)

function abrirCrear() {
  enEdicion.value = null
  Object.assign(form, { name: '', code: '', phone: '', description: '' })
  errorForm.value = null
  modal.value = 'formulario'
}

function abrirEditar(d: Driver) {
  enEdicion.value = d
  Object.assign(form, {
    name: d.name,
    code: d.code ?? '',
    phone: d.phone ?? '',
    description: d.description ?? '',
  })
  errorForm.value = null
  modal.value = 'formulario'
}

async function guardar() {
  errorForm.value = null
  if (!form.name.trim()) {
    errorForm.value = 'Escribe el nombre del conductor.'
    return
  }
  // `custom_fields` se omite: el backend relee los de Wialon y los reenvía.
  const datos: DriverWrite = {
    name: form.name.trim(),
    code: form.code.trim() || null,
    phone: form.phone.trim() || null,
    description: form.description.trim() || null,
  }
  guardando.value = true
  try {
    if (enEdicion.value) {
      await editar.mutateAsync({ id: enEdicion.value.id, datos })
      toast.exito('Conductor actualizado.')
    } else {
      await crear.mutateAsync(datos)
      toast.exito('Conductor creado.')
    }
    modal.value = 'ninguno'
  } catch (e) {
    errorForm.value = mensajeDeError(e)
  } finally {
    guardando.value = false
  }
}

// ── eliminar ──
const aEliminar = ref<Driver | null>(null)
function abrirEliminar(d: Driver) {
  aEliminar.value = d
  modal.value = 'eliminar'
}
async function confirmarEliminar() {
  if (!aEliminar.value) return
  const nombre = aEliminar.value.name
  guardando.value = true
  try {
    await eliminar.mutateAsync(aEliminar.value.id)
    toast.exito(`${nombre} eliminado.`)
    modal.value = 'ninguno'
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    guardando.value = false
  }
}

// ── vincular ──
const aVincular = ref<Driver | null>(null)
const unidadElegida = ref<number | null>(null)
function abrirVincular(d: Driver) {
  aVincular.value = d
  unidadElegida.value = null
  modal.value = 'vincular'
}
async function confirmarVincular() {
  if (!aVincular.value || !unidadElegida.value) return
  guardando.value = true
  try {
    await vincular.mutateAsync({ id: aVincular.value.id, unitId: unidadElegida.value })
    toast.exito('Conductor vinculado. Ya aparece en el detalle del vehículo.')
    modal.value = 'ninguno'
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    guardando.value = false
  }
}
async function quitarVinculo(d: Driver) {
  ocupado.value = d.id
  try {
    await desvincular.mutateAsync({ id: d.id, unitId: d.bound_unit_id! })
    toast.exito('Conductor desvinculado.')
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    ocupado.value = null
  }
}
</script>

<template>
  <div class="flex h-dvh flex-col">
    <header
      class="flex flex-wrap items-center gap-3 border-b p-4"
      :style="{ borderColor: 'var(--border)' }"
    >
      <div class="mr-auto flex items-baseline gap-3">
        <h1 class="text-lg font-semibold">Conductores</h1>
        <span
          v-if="meta"
          class="font-mono text-xs tabular"
          :style="{ color: 'var(--on-surface-muted)' }"
        >
          {{ meta.total }}
        </span>
        <!-- Señal de que el listado se está releyendo tras una acción. -->
        <span
          v-if="isFetching && !isPending"
          class="size-3 animate-spin rounded-full border-2 border-t-transparent"
          :style="{ borderColor: 'var(--border-strong)', borderTopColor: 'transparent' }"
          aria-hidden="true"
        />
      </div>

      <label class="sr-only" for="buscar-conductor">Buscar conductor</label>
      <input
        id="buscar-conductor"
        v-model="busqueda"
        type="search"
        placeholder="Nombre, código o teléfono"
        class="field-input max-w-xs"
      />

      <BotonExportar recurso="drivers" />
      <AppButton v-if="puedeEditar" @click="abrirCrear">Nuevo conductor</AppButton>
    </header>

    <div ref="zonaTabla" class="flex min-h-0 flex-1 flex-col p-4">
      <div v-if="isPending" class="grid gap-2" aria-busy="true">
        <div
          v-for="n in 6"
          :key="n"
          class="h-14 animate-pulse rounded-md"
          :style="{ background: 'var(--surface)' }"
        />
      </div>

      <div v-else-if="isError" class="mx-auto max-w-md">
        <AppAlert>
          {{ (error as Error)?.message ?? 'No se pudieron cargar los conductores.' }}
        </AppAlert>
        <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
      </div>

      <div v-else-if="!conductores.length" class="grid justify-items-center gap-2 py-16 text-center">
        <span class="text-3xl" aria-hidden="true">⚇</span>
        <p class="font-semibold">
          {{ busqueda ? 'Ningún conductor coincide' : 'Todavía no hay conductores' }}
        </p>
        <p class="max-w-sm text-sm" :style="{ color: 'var(--on-surface-muted)' }">
          {{
            busqueda
              ? 'Cambia el texto de búsqueda.'
              : 'Los conductores que crees aquí se guardan en Wialon.'
          }}
        </p>
        <AppButton v-if="puedeEditar && !busqueda" class="mt-2" @click="abrirCrear">
          Crear el primero
        </AppButton>
      </div>

      <div
        v-else
        class="min-h-0 flex-1 overflow-x-auto rounded-md border"
        :style="{ borderColor: 'var(--border)' }"
      >
        <table class="w-full min-w-[46rem] border-collapse text-sm">
          <caption class="sr-only">Conductores de la cuenta y su vehículo vinculado</caption>
          <thead>
            <tr
              class="text-left text-xs font-semibold"
              :style="{ background: 'var(--surface)', color: 'var(--on-surface-soft)' }"
            >
              <th scope="col" class="w-12 p-3 text-right">#</th>
              <th scope="col" class="p-3">Nombre</th>
              <th scope="col" class="p-3">Código</th>
              <th scope="col" class="p-3">Teléfono</th>
              <th scope="col" class="p-3">Vehículo</th>
              <th scope="col" class="p-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(d, i) in conductores"
              :key="d.id"
              class="border-t transition-opacity"
              :style="{ borderColor: 'var(--border)' }"
              :class="ocupado === d.id && 'opacity-50'"
            >
              <td
                class="p-3 text-right font-mono text-xs tabular"
                :style="{ color: 'var(--on-surface-muted)' }"
              >
                {{ numeroDeFila(i) }}
              </td>
              <td class="p-3 font-medium">{{ d.name || '(sin nombre)' }}</td>
              <td class="p-3 font-mono text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                {{ d.code || '—' }}
              </td>
              <td class="p-3 font-mono text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                {{ d.phone || '—' }}
              </td>
              <td class="p-3">
                <span v-if="d.bound_unit_id" class="font-mono text-xs text-teal-dark">
                  {{ nombreUnidad(d.bound_unit_id) }}
                </span>
                <span v-else class="text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                  Sin vincular
                </span>
              </td>
              <td class="p-3">
                <div class="flex justify-end gap-1.5">
                  <template v-if="puedeVincular">
                    <button
                      v-if="d.bound_unit_id"
                      type="button"
                      class="btn-row"
                      :disabled="ocupado === d.id"
                      @click="quitarVinculo(d)"
                    >
                      Desvincular
                    </button>
                    <button v-else type="button" class="btn-row" @click="abrirVincular(d)">
                      Vincular
                    </button>
                  </template>
                  <template v-if="puedeEditar">
                    <button type="button" class="btn-row" @click="abrirEditar(d)">Editar</button>
                    <button
                      type="button"
                      class="btn-row btn-row-danger"
                      @click="abrirEliminar(d)"
                    >
                      Eliminar
                    </button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <Paginador
        v-if="meta"
        :pagina="meta.page"
        :paginas="meta.pages"
        :total="meta.total"
        etiqueta="conductores"
        @cambiar="pagina = $event"
      />
    </div>

    <!-- ───────── formulario ───────── -->
    <AppModal
      v-if="modal === 'formulario'"
      :titulo="enEdicion ? 'Editar conductor' : 'Nuevo conductor'"
      descripcion="Los cambios se guardan en Wialon."
      @cerrar="modal = 'ninguno'"
    >
      <form class="grid gap-4" novalidate @submit.prevent="guardar">
        <AppAlert v-if="errorForm">{{ errorForm }}</AppAlert>

        <AppField id="d-name" v-model="form.name" label="Nombre" required placeholder="Carolina Rueda" />
        <AppField id="d-code" v-model="form.code" label="Código" hint="Opcional. Debe ser único." placeholder="CR-014" />
        <AppField id="d-phone" v-model="form.phone" label="Teléfono" hint="Opcional. Dígitos y un + inicial." placeholder="+573001112233" />
        <AppField id="d-desc" v-model="form.description" label="Descripción" placeholder="Turno noche" />

        <p v-if="enEdicion" class="field-hint">
          Los campos personalizados de este conductor se conservan: el backend los relee de
          Wialon y los reenvía completos.
        </p>

        <div class="flex justify-end gap-2 pt-1">
          <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
          <AppButton type="submit" :loading="guardando">
            {{ enEdicion ? 'Guardar cambios' : 'Crear conductor' }}
          </AppButton>
        </div>
      </form>
    </AppModal>

    <!-- ───────── eliminar ───────── -->
    <AppModal
      v-if="modal === 'eliminar'"
      titulo="Eliminar conductor"
      descripcion="Se aplica en Wialon y no se puede deshacer."
      @cerrar="modal = 'ninguno'"
    >
      <p class="text-sm">
        Se eliminará <strong>{{ aEliminar?.name }}</strong> de forma permanente.
      </p>
      <div class="mt-5 flex justify-end gap-2">
        <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
        <AppButton variant="danger" :loading="guardando" @click="confirmarEliminar">
          Eliminar
        </AppButton>
      </div>
    </AppModal>

    <!-- ───────── vincular ───────── -->
    <AppModal
      v-if="modal === 'vincular'"
      titulo="Vincular a un vehículo"
      :descripcion="`${aVincular?.name} quedará asignado en Wialon.`"
      @cerrar="modal = 'ninguno'"
    >
      <AppSelect id="unidad" v-model="unidadElegida" label="Vehículo">
        <option :value="null" disabled>Elige un vehículo…</option>
        <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.display_name }}</option>
      </AppSelect>
      <div class="mt-5 flex justify-end gap-2">
        <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
        <AppButton :loading="guardando" :disabled="!unidadElegida" @click="confirmarVincular">
          Vincular
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
