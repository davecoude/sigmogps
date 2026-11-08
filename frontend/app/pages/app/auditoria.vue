<script setup lang="ts">
definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'audit:read' })
useHead({ title: 'Auditoría · sigmoGPS' })

const busqueda = ref('')
const accion = ref('')
const soloFallidos = ref(false)
const pagina = ref(1)

const zonaTabla = ref<HTMLElement | null>(null)
const { filas: porPagina } = useFilasQueCaben(zonaTabla)

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
watch([accion, soloFallidos], () => (pagina.value = 1))

const filtros = computed(() => ({
  action: accion.value,
  search: busquedaDiferida.value,
  onlyFailures: soloFallidos.value,
  page: pagina.value,
  pageSize: porPagina.value,
}))

const { data, isPending, isError, error, refetch, isFetching } = useAuditEntries(filtros)
const { data: acciones } = useAuditActions()

const eventos = computed(() => data.value?.items ?? [])
const meta = computed(() => data.value?.meta)

function numeroDeFila(indice: number) {
  return (meta.value ? (meta.value.page - 1) * meta.value.page_size : 0) + indice + 1
}

function cuando(iso: string) {
  return new Date(iso).toLocaleString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'America/Bogota',
  })
}

/** Resumen de una línea del detalle, para no romper la fila. */
function resumen(detalle: Record<string, unknown> | null) {
  if (!detalle) return ''
  return Object.entries(detalle)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
    .join(' · ')
}

const expandido = ref<string | null>(null)
</script>

<template>
  <div class="flex h-full flex-col">
    <header
      class="flex flex-wrap items-center gap-3 border-b p-4"
      :style="{ borderColor: 'var(--border)' }"
    >
      <div class="mr-auto flex items-baseline gap-3">
        <h1 class="text-lg font-semibold">Auditoría</h1>
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

      <label class="sr-only" for="buscar-evento">Buscar por correo, acción o entidad</label>
      <input
        id="buscar-evento"
        v-model="busqueda"
        type="search"
        placeholder="Correo, acción o entidad"
        class="field-input max-w-xs"
      />

      <label class="sr-only" for="filtro-accion">Filtrar por acción</label>
      <select id="filtro-accion" v-model="accion" class="field-input max-w-[12rem]">
        <option value="">Todas las acciones</option>
        <option v-for="a in acciones" :key="a" :value="a">{{ a }}</option>
      </select>

      <label class="flex items-center gap-2 text-xs" :style="{ color: 'var(--on-surface-soft)' }">
        <input v-model="soloFallidos" type="checkbox" class="size-4 accent-[var(--danger)]" />
        Solo fallidos
      </label>
    </header>

    <div ref="zonaTabla" class="flex min-h-0 flex-1 flex-col p-4">
      <div v-if="isPending" class="grid gap-2" aria-busy="true">
        <div
          v-for="n in 8"
          :key="n"
          class="h-11 animate-pulse rounded-md"
          :style="{ background: 'var(--surface)' }"
        />
      </div>

      <div v-else-if="isError" class="mx-auto max-w-md">
        <AppAlert>{{ (error as Error)?.message ?? 'No se pudo cargar la auditoría.' }}</AppAlert>
        <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
      </div>

      <div v-else-if="!eventos.length" class="grid justify-items-center gap-2 py-16 text-center">
        <span class="text-3xl" aria-hidden="true">≡</span>
        <p class="font-semibold">Ningún evento coincide</p>
        <p class="max-w-sm text-sm" :style="{ color: 'var(--on-surface-muted)' }">
          Quita los filtros para ver el registro completo.
        </p>
      </div>

      <div
        v-else
        class="min-h-0 flex-1 overflow-x-auto rounded-md border"
        :style="{ borderColor: 'var(--border)' }"
      >
        <table class="w-full min-w-[56rem] border-collapse text-sm">
          <caption class="sr-only">Quién hizo qué y cuándo</caption>
          <thead>
            <tr
              class="text-left text-xs font-semibold"
              :style="{ background: 'var(--surface)', color: 'var(--on-surface-soft)' }"
            >
              <th scope="col" class="w-12 p-3 text-right">#</th>
              <th scope="col" class="p-3">Cuándo</th>
              <th scope="col" class="p-3">Acción</th>
              <th scope="col" class="p-3">Quién</th>
              <th scope="col" class="p-3">Sobre</th>
              <th scope="col" class="p-3">Detalle</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(e, i) in eventos"
              :key="e.id"
              class="border-t align-top"
              :style="{ borderColor: 'var(--border)' }"
            >
              <td
                class="p-3 text-right font-mono text-xs tabular"
                :style="{ color: 'var(--on-surface-muted)' }"
              >
                {{ numeroDeFila(i) }}
              </td>
              <td class="whitespace-nowrap p-3 font-mono text-xs tabular">{{ cuando(e.created_at) }}</td>
              <td class="p-3">
                <span
                  class="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  :class="e.success ? 'bg-teal-soft/10 text-teal-dark' : 'bg-brand-soft/10 text-brand-dark'"
                >
                  <span class="size-1.5 rounded-full bg-current" aria-hidden="true" />
                  {{ e.action }}
                </span>
              </td>
              <td class="p-3 text-xs">{{ e.user_email ?? '—' }}</td>
              <td class="p-3 font-mono text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                <template v-if="e.entity_type">{{ e.entity_type }} {{ e.entity_id }}</template>
                <template v-else>—</template>
              </td>
              <td class="p-3 text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                <template v-if="e.detail">
                  <button
                    type="button"
                    class="max-w-[22rem] truncate text-left hover:underline"
                    :aria-expanded="expandido === e.id"
                    @click="expandido = expandido === e.id ? null : e.id"
                  >
                    {{ resumen(e.detail) }}
                  </button>
                  <pre
                    v-if="expandido === e.id"
                    class="mt-2 max-w-[22rem] overflow-x-auto rounded p-2 font-mono text-[11px]"
                    :style="{ background: 'var(--surface-sunken)' }"
                  >{{ JSON.stringify(e.detail, null, 2) }}</pre>
                </template>
                <template v-else>—</template>
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
        etiqueta="eventos"
        @cambiar="pagina = $event"
      />
    </div>
  </div>
</template>
