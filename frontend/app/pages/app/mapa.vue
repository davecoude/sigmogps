<script setup lang="ts">
import type { VehicleStatus } from '~/types/api'

definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'vehicles:read' })
useHead({ title: 'Mapa · sigmoGPS' })

const busqueda = ref('')
const estado = ref<VehicleStatus | null>(null)
const seleccionado = ref<number | null>(null)
const vistaMovil = ref<'lista' | 'mapa'>('lista')

// Evita una petición por tecla.
const busquedaDiferida = ref('')
let temporizador: ReturnType<typeof setTimeout>
watch(busqueda, (v) => {
  clearTimeout(temporizador)
  temporizador = setTimeout(() => (busquedaDiferida.value = v), 350)
})

const filtros = computed(() => ({
  search: busquedaDiferida.value,
  status: estado.value,
  pageSize: 100,
}))

const { data, isPending, isError, error, refetch } = useVehicles(filtros)
const { data: resumen } = useFleetSummary()

const vehiculos = computed(() => data.value?.items ?? [])

const FILTROS: { valor: VehicleStatus | null; texto: string; clave?: keyof typeof contadores.value }[] = [
  { valor: null, texto: 'Todos' },
  { valor: 'en_movimiento', texto: 'En movimiento' },
  { valor: 'detenido', texto: 'Detenidos' },
  { valor: 'sin_senal', texto: 'Sin señal' },
]

const contadores = computed(() => ({
  total: resumen.value?.total ?? 0,
  en_movimiento: resumen.value?.en_movimiento ?? 0,
  detenido: resumen.value?.detenidos ?? 0,
  sin_senal: resumen.value?.sin_senal ?? 0,
}))

function contarDe(valor: VehicleStatus | null) {
  return valor === null ? contadores.value.total : contadores.value[valor]
}

function horaLocal(iso: string) {
  return new Date(iso).toLocaleTimeString('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Bogota',
  })
}

function seleccionar(id: number) {
  seleccionado.value = id
  if (window.innerWidth < 768) vistaMovil.value = 'mapa'
}
</script>

<template>
  <div class="flex h-dvh flex-col md:flex-row">
    <!-- ───────── lista ───────── -->
    <aside
      class="flex min-h-0 w-full flex-col border-console-line bg-console-2 md:w-[21rem] md:border-r"
      :class="vistaMovil === 'mapa' ? 'hidden md:flex' : 'flex'"
    >
      <div class="grid gap-3 border-b border-console-line p-4">
        <div class="flex items-baseline justify-between gap-3">
          <h1 class="text-lg font-semibold">Seguimiento de unidades</h1>
          <span class="font-mono text-xs text-console-muted tabular">
            {{ contadores.total }} unidades
          </span>
        </div>

        <label class="sr-only" for="buscar">Buscar vehículo</label>
        <input
          id="buscar"
          v-model="busqueda"
          type="search"
          placeholder="Buscar placa, unidad o conductor"
          class="rounded-md border border-console-line bg-console-3 px-3.5 py-2 text-sm
                 text-console-ink placeholder:text-console-muted"
        />

        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="f in FILTROS"
            :key="f.texto"
            type="button"
            class="rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors"
            :class="
              estado === f.valor
                ? 'border-brand-hi bg-brand-hi text-white'
                : 'border-console-line bg-console-3 text-console-muted hover:text-console-ink'
            "
            :aria-pressed="estado === f.valor"
            @click="estado = f.valor"
          >
            {{ f.texto }}
            <span class="ml-1 rounded bg-black/20 px-1 tabular">{{ contarDe(f.valor) }}</span>
          </button>
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <!-- carga -->
        <div v-if="isPending" class="grid gap-2 p-3" aria-busy="true">
          <div
            v-for="n in 6"
            :key="n"
            class="h-20 animate-pulse rounded-md border border-console-line bg-console-3"
          />
        </div>

        <!-- error -->
        <div v-else-if="isError" class="p-4">
          <AppAlert>{{ (error as Error)?.message ?? 'No se pudo cargar la flota.' }}</AppAlert>
          <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
        </div>

        <!-- vacío -->
        <div v-else-if="!vehiculos.length" class="grid gap-2 p-8 text-center">
          <span class="text-2xl" aria-hidden="true">◎</span>
          <p class="font-semibold">Ningún vehículo coincide</p>
          <p class="text-sm text-console-muted">Cambia el texto de búsqueda o quita el filtro.</p>
        </div>

        <!-- lista -->
        <ul v-else class="divide-y divide-console-line">
          <li v-for="v in vehiculos" :key="v.id">
            <button
              type="button"
              class="grid w-full gap-1.5 px-4 py-3 text-left transition-colors"
              :class="
                seleccionado === v.id
                  ? 'bg-console-3 shadow-[inset_3px_0_0_var(--color-brand-hi)]'
                  : 'hover:bg-console-3'
              "
              :aria-current="seleccionado === v.id ? 'true' : undefined"
              @click="seleccionar(v.id)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="truncate font-mono text-sm font-medium">{{ v.display_name }}</span>
                <StatusChip :status="v.status" dark />
              </div>
              <div class="flex flex-wrap gap-x-3 text-xs text-console-muted">
                <span class="tabular">{{ v.position?.speed_kmh ?? 0 }} km/h</span>
                <span v-if="v.position?.cardinal">{{ v.position.cardinal }}</span>
                <span v-if="v.position" class="tabular">{{ horaLocal(v.position.reported_at) }}</span>
              </div>
              <p class="truncate text-xs" :class="v.driver_name ? 'text-console-ink' : 'text-console-muted'">
                {{ v.driver_name ?? 'Sin conductor vinculado' }}
              </p>
            </button>
          </li>
        </ul>
      </div>

      <!-- alternador solo en móvil -->
      <div class="border-t border-console-line p-2 md:hidden">
        <AppButton variant="ghost" block @click="vistaMovil = 'mapa'">Ver en el mapa</AppButton>
      </div>
    </aside>

    <!-- ───────── mapa ───────── -->
    <div
      class="relative min-h-0 flex-1"
      :class="vistaMovil === 'lista' ? 'hidden md:block' : 'block'"
    >
      <ClientOnly>
        <FleetMap :vehicles="vehiculos" :selected-id="seleccionado" @select="seleccionado = $event" />
      </ClientOnly>

      <button
        type="button"
        class="absolute left-3 top-3 z-[500] rounded-md border border-console-line bg-console-2
               px-3 py-2 text-xs font-semibold md:hidden"
        @click="vistaMovil = 'lista'"
      >
        ← Volver a la lista
      </button>
    </div>
  </div>
</template>
