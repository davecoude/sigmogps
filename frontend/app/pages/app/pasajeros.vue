<script setup lang="ts">
import { mensajeDeError } from '~/composables/useAuth'
import type { Passenger, PassengerWrite } from '~/features/passengers/usePassengers'
import type { VehicleListItem } from '~/types/api'

definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'passengers:read' })
useHead({ title: 'Pasajeros · sigmoGPS' })

const { puede } = useAuth()
const toast = useToast()

const puedeEditar = computed(() => puede('passengers:write'))
const puedeAsignar = computed(() => puede('bindings:write'))

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

const { data, isPending, isError, error, refetch, isFetching } = usePassengers(filtros)
const { crear, editar, guardarCampos, eliminar, asignar, desasignar } = usePassengerMutations()

const pasajeros = computed(() => data.value?.items ?? [])
const meta = computed(() => data.value?.meta)

const filtrosVehiculos = computed(() => ({ pageSize: 100 }))
const { data: paginaVehiculos } = useVehicles(filtrosVehiculos)
const vehiculos = computed<VehicleListItem[]>(() => paginaVehiculos.value?.items ?? [])

/** Número de registro dentro del total, no dentro de la página. */
function numeroDeFila(indice: number) {
  return (meta.value ? (meta.value.page - 1) * meta.value.page_size : 0) + indice + 1
}

function nombreUnidad(id: number | null) {
  if (!id) return null
  return vehiculos.value.find((v) => v.id === id)?.display_name ?? `Unidad ${id}`
}

const ocupado = ref<number | null>(null)
const modal = ref<'ninguno' | 'formulario' | 'campos' | 'eliminar' | 'asignar'>('ninguno')
const guardando = ref(false)

// ── crear y editar ──
const enEdicion = ref<Passenger | null>(null)
const form = reactive({ name: '', code: '' })
const camposNuevos = ref<Record<string, string>>({})
const errorForm = ref<string | null>(null)

function abrirCrear() {
  enEdicion.value = null
  Object.assign(form, { name: '', code: '' })
  camposNuevos.value = {}
  errorForm.value = null
  modal.value = 'formulario'
}

function abrirEditar(p: Passenger) {
  enEdicion.value = p
  Object.assign(form, { name: p.name, code: p.code ?? '' })
  errorForm.value = null
  modal.value = 'formulario'
}

async function guardar() {
  errorForm.value = null
  if (!form.name.trim()) {
    errorForm.value = 'Escribe el nombre del pasajero.'
    return
  }
  guardando.value = true
  try {
    if (enEdicion.value) {
      // Sin `custom_fields`: el backend conserva los de Wialon (RF-27).
      const datos: PassengerWrite = { name: form.name.trim(), code: form.code.trim() || null }
      await editar.mutateAsync({ id: enEdicion.value.id, datos })
      toast.exito('Pasajero actualizado. Sus campos personalizados se conservaron.')
    } else {
      await crear.mutateAsync({
        name: form.name.trim(),
        code: form.code.trim() || null,
        custom_fields: camposNuevos.value,
      })
      toast.exito('Pasajero creado en Wialon.')
    }
    modal.value = 'ninguno'
  } catch (e) {
    errorForm.value = mensajeDeError(e)
  } finally {
    guardando.value = false
  }
}

// ── campos personalizados ──
const enCampos = ref<Passenger | null>(null)
const camposEditados = ref<Record<string, string>>({})

function abrirCampos(p: Passenger) {
  enCampos.value = p
  camposEditados.value = { ...p.custom_fields }
  errorForm.value = null
  modal.value = 'campos'
}

async function guardarLosCampos() {
  if (!enCampos.value) return
  guardando.value = true
  errorForm.value = null
  try {
    await guardarCampos.mutateAsync({ id: enCampos.value.id, campos: camposEditados.value })
    toast.exito('Campos personalizados guardados en Wialon.')
    modal.value = 'ninguno'
  } catch (e) {
    errorForm.value = mensajeDeError(e)
  } finally {
    guardando.value = false
  }
}

// ── eliminar ──
const aEliminar = ref<Passenger | null>(null)
function abrirEliminar(p: Passenger) {
  aEliminar.value = p
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

// ── asignar ──
const aAsignar = ref<Passenger | null>(null)
const unidadElegida = ref<number | null>(null)
function abrirAsignar(p: Passenger) {
  aAsignar.value = p
  unidadElegida.value = null
  modal.value = 'asignar'
}
async function confirmarAsignar() {
  if (!aAsignar.value || !unidadElegida.value) return
  guardando.value = true
  try {
    await asignar.mutateAsync({ id: aAsignar.value.id, unitId: unidadElegida.value })
    toast.exito('Pasajero asignado al vehículo.')
    modal.value = 'ninguno'
  } catch (e) {
    toast.error(mensajeDeError(e))
  } finally {
    guardando.value = false
  }
}
async function quitarAsignacion(p: Passenger) {
  ocupado.value = p.id
  try {
    await desasignar.mutateAsync({ id: p.id, unitId: p.bound_unit_id! })
    toast.exito('Pasajero desasignado.')
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
        <h1 class="text-lg font-semibold">Pasajeros</h1>
        <span
          v-if="meta"
          class="font-mono text-xs tabular"
          :style="{ color: 'var(--on-surface-muted)' }"
        >
          {{ meta.total }}
        </span>
        <span
          v-if="isFetching && !isPending"
          class="size-3 animate-spin rounded-full border-2 border-t-transparent"
          :style="{ borderColor: 'var(--border-strong)', borderTopColor: 'transparent' }"
          aria-hidden="true"
        />
      </div>

      <label class="sr-only" for="buscar-pasajero">Buscar pasajero</label>
      <input
        id="buscar-pasajero"
        v-model="busqueda"
        type="search"
        placeholder="Nombre, código o campo personalizado"
        class="field-input max-w-sm"
      />

      <BotonExportar recurso="passengers" />
      <AppButton v-if="puedeEditar" @click="abrirCrear">Nuevo pasajero</AppButton>
    </header>

    <div ref="zonaTabla" class="flex min-h-0 flex-1 flex-col p-4">
      <div v-if="isPending" class="grid gap-2" aria-busy="true">
        <div
          v-for="n in 8"
          :key="n"
          class="h-12 animate-pulse rounded-md"
          :style="{ background: 'var(--surface)' }"
        />
      </div>

      <div v-else-if="isError" class="mx-auto max-w-md">
        <AppAlert>{{ (error as Error)?.message ?? 'No se pudieron cargar los pasajeros.' }}</AppAlert>
        <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
      </div>

      <div v-else-if="!pasajeros.length" class="grid justify-items-center gap-2 py-16 text-center">
        <span class="text-3xl" aria-hidden="true">⚉</span>
        <p class="font-semibold">
          {{ busquedaDiferida ? 'Ningún pasajero coincide' : 'Todavía no hay pasajeros' }}
        </p>
        <p class="max-w-sm text-sm" :style="{ color: 'var(--on-surface-muted)' }">
          {{
            busquedaDiferida
              ? 'La búsqueda también revisa los campos personalizados.'
              : 'Los pasajeros que crees aquí se guardan en Wialon.'
          }}
        </p>
        <AppButton v-if="puedeEditar && !busquedaDiferida" class="mt-2" @click="abrirCrear">
          Crear el primero
        </AppButton>
      </div>

      <div
        v-else
        class="min-h-0 flex-1 overflow-x-auto rounded-md border"
        :style="{ borderColor: 'var(--border)' }"
      >
        <table class="w-full min-w-[48rem] border-collapse text-sm">
          <caption class="sr-only">Pasajeros de la cuenta y su vehículo asignado</caption>
          <thead>
            <tr
              class="text-left text-xs font-semibold"
              :style="{ background: 'var(--surface)', color: 'var(--on-surface-soft)' }"
            >
              <th scope="col" class="w-12 p-3 text-right">#</th>
              <th scope="col" class="p-3">Nombre</th>
              <th scope="col" class="p-3">Código</th>
              <th scope="col" class="p-3">Campos</th>
              <th scope="col" class="p-3">Vehículo</th>
              <th scope="col" class="p-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(p, i) in pasajeros"
              :key="p.id"
              class="border-t transition-opacity"
              :style="{ borderColor: 'var(--border)' }"
              :class="ocupado === p.id && 'opacity-50'"
            >
              <td
                class="p-3 text-right font-mono text-xs tabular"
                :style="{ color: 'var(--on-surface-muted)' }"
              >
                {{ numeroDeFila(i) }}
              </td>
              <td class="p-3 font-medium">{{ p.name || '(sin nombre)' }}</td>
              <td class="p-3 font-mono text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                {{ p.code || '—' }}
              </td>
              <td class="p-3">
                <button
                  type="button"
                  class="btn-row"
                  :disabled="!puedeEditar"
                  @click="abrirCampos(p)"
                >
                  {{ Object.keys(p.custom_fields).length }}
                  {{ Object.keys(p.custom_fields).length === 1 ? 'campo' : 'campos' }}
                </button>
              </td>
              <td class="p-3">
                <span v-if="p.bound_unit_id" class="font-mono text-xs text-teal-dark">
                  {{ nombreUnidad(p.bound_unit_id) }}
                </span>
                <span v-else class="text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                  Sin asignar
                </span>
              </td>
              <td class="p-3">
                <div class="flex justify-end gap-1.5">
                  <template v-if="puedeAsignar">
                    <button
                      v-if="p.bound_unit_id"
                      type="button"
                      class="btn-row"
                      :disabled="ocupado === p.id"
                      @click="quitarAsignacion(p)"
                    >
                      Desasignar
                    </button>
                    <button v-else type="button" class="btn-row" @click="abrirAsignar(p)">
                      Asignar
                    </button>
                  </template>
                  <template v-if="puedeEditar">
                    <button type="button" class="btn-row" @click="abrirEditar(p)">Editar</button>
                    <button type="button" class="btn-row btn-row-danger" @click="abrirEliminar(p)">
                      Eliminar
                    </button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación numerada (RF-28). Queda fija bajo la tabla: nunca se va
           de la ventana, así que no hay que desplazarse para cambiar de página. -->
      <Paginador
        v-if="meta"
        :pagina="meta.page"
        :paginas="meta.pages"
        :total="meta.total"
        etiqueta="pasajeros"
        @cambiar="pagina = $event"
      />
    </div>

    <!-- ───────── crear / editar ───────── -->
    <AppModal
      v-if="modal === 'formulario'"
      :titulo="enEdicion ? 'Editar pasajero' : 'Nuevo pasajero'"
      descripcion="Los cambios se guardan en Wialon."
      @cerrar="modal = 'ninguno'"
    >
      <form class="grid gap-4" novalidate @submit.prevent="guardar">
        <AppAlert v-if="errorForm">{{ errorForm }}</AppAlert>

        <AppField id="p-name" v-model="form.name" label="Nombre" required placeholder="Ana Gómez" />
        <AppField id="p-code" v-model="form.code" label="Código" hint="Opcional. Debe ser único." placeholder="PAS-001" />

        <CustomFieldsEditor v-if="!enEdicion" v-model="camposNuevos" />

        <p v-else class="field-hint">
          Los campos personalizados se editan por separado, desde el botón de campos en la
          tabla. Guardar aquí no los toca.
        </p>

        <div class="flex justify-end gap-2 pt-1">
          <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
          <AppButton type="submit" :loading="guardando">
            {{ enEdicion ? 'Guardar cambios' : 'Crear pasajero' }}
          </AppButton>
        </div>
      </form>
    </AppModal>

    <!-- ───────── campos personalizados ───────── -->
    <AppModal
      v-if="modal === 'campos'"
      titulo="Campos personalizados"
      :descripcion="`${enCampos?.name}. Lo que quites de la lista se elimina en Wialon.`"
      @cerrar="modal = 'ninguno'"
    >
      <div class="grid gap-4">
        <AppAlert v-if="errorForm">{{ errorForm }}</AppAlert>
        <CustomFieldsEditor v-model="camposEditados" />
        <div class="flex justify-end gap-2">
          <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
          <AppButton :loading="guardando" @click="guardarLosCampos">Guardar campos</AppButton>
        </div>
      </div>
    </AppModal>

    <!-- ───────── eliminar ───────── -->
    <AppModal
      v-if="modal === 'eliminar'"
      titulo="Eliminar pasajero"
      descripcion="Se aplica en Wialon y no se puede deshacer."
      @cerrar="modal = 'ninguno'"
    >
      <p class="text-sm">
        Se eliminará <strong>{{ aEliminar?.name }}</strong> y sus
        {{ Object.keys(aEliminar?.custom_fields ?? {}).length }} campos personalizados.
      </p>
      <div class="mt-5 flex justify-end gap-2">
        <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
        <AppButton variant="danger" :loading="guardando" @click="confirmarEliminar">
          Eliminar
        </AppButton>
      </div>
    </AppModal>

    <!-- ───────── asignar ───────── -->
    <AppModal
      v-if="modal === 'asignar'"
      titulo="Asignar a un vehículo"
      :descripcion="`${aAsignar?.name} quedará asignado en Wialon.`"
      @cerrar="modal = 'ninguno'"
    >
      <AppSelect id="unidad-pasajero" v-model="unidadElegida" label="Vehículo">
        <option :value="null" disabled>Elige un vehículo…</option>
        <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.display_name }}</option>
      </AppSelect>
      <div class="mt-5 flex justify-end gap-2">
        <AppButton variant="ghost" @click="modal = 'ninguno'">Cancelar</AppButton>
        <AppButton :loading="guardando" :disabled="!unidadElegida" @click="confirmarAsignar">
          Asignar
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
