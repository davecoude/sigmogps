<script setup lang="ts">
/**
 * Tablero de la flota (RF-23).
 *
 * KPIs numéricos. No hay gráficas de serie temporal porque dependen del
 * historial de recorridos, que quedó fuera de alcance y está declarado en el
 * README.
 *
 * Decisión de visualización: la composición por estado se dibuja como barras
 * por fila con etiqueta directa, no como una barra apilada. El teal de «en
 * movimiento» y el gris de «detenido» quedan a una distancia perceptual de
 * ΔE 10.9 en visión normal sobre esta superficie, por debajo del piso de 15:
 * pegados en una sola barra serían difíciles de separar incluso con visión
 * de color completa. Separados por fila, la identidad la carga el texto y el
 * color solo refuerza.
 */
definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'vehicles:read' })
useHead({ title: 'Tablero · sigmoGPS' })

const { data: resumen, isPending, isError, error, refetch } = useFleetSummary()

// Lista para los dos paneles operativos. El servicio ya ordena primero lo que
// exige atención, así que basta la primera página.
const filtros = ref({ pageSize: 100, page: 1 })
const { data: pagina } = useVehicles(filtros)
const vehiculos = computed(() => pagina.value?.items ?? [])

const sinSenal = computed(() =>
  vehiculos.value
    .filter((v) => v.status === 'sin_senal')
    .sort((a, b) => (b.minutes_since_report ?? 0) - (a.minutes_since_report ?? 0))
    .slice(0, 8),
)

const sinConductor = computed(() =>
  vehiculos.value.filter((v) => v.driver_id === null).slice(0, 9),
)

/** Composición por estado. Cada fila lleva su propio nombre y su valor. */
const composicion = computed(() => {
  const r = resumen.value
  if (!r || !r.total) return []
  return [
    { clave: 'en_movimiento' as const, nombre: 'En movimiento', valor: r.en_movimiento },
    { clave: 'detenido' as const, nombre: 'Detenidos', valor: r.detenidos },
    { clave: 'sin_senal' as const, nombre: 'Sin señal', valor: r.sin_senal },
  ].map((f) => ({
    ...f,
    porcentaje: Math.round((f.valor / r.total) * 100),
    ancho: (f.valor / r.total) * 100,
  }))
})

// Los mismos colores que el mapa y los chips de estado: un estado tiene un
// solo color en toda la aplicación.
const COLOR_ESTADO: Record<string, string> = {
  en_movimiento: '#1E8C93',
  detenido: '#6B6B6B',
  sin_senal: '#EB162C',
}

const cobertura = computed(() => {
  const r = resumen.value
  if (!r || !r.total) return 0
  return Math.round((r.con_conductor / r.total) * 100)
})

/** El relleno del medidor carga la severidad, no la identidad. */
const colorCobertura = computed(() => {
  const c = cobertura.value
  if (c >= 70) return '#1E8C93'
  if (c >= 30) return '#C9A227'
  return '#EB162C'
})

function haceCuanto(minutos: number | null) {
  if (minutos === null) return 'sin reporte'
  if (minutos < 60) return `${Math.round(minutos)} min`
  const horas = minutos / 60
  if (horas < 24) return `${Math.round(horas)} h`
  return `${Math.round(horas / 24)} d`
}
</script>

<template>
  <div class="flex h-dvh flex-col">
    <header
      class="flex flex-wrap items-center gap-3 border-b p-4"
      :style="{ borderColor: 'var(--border)' }"
    >
      <h1 class="mr-auto text-lg font-semibold">Tablero</h1>
      <NuxtLink to="/app/mapa" class="btn-row">Ver el mapa</NuxtLink>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      <div v-if="isPending" class="grid gap-3 lg:grid-cols-2" aria-busy="true">
        <div
          v-for="n in 4"
          :key="n"
          class="h-44 animate-pulse rounded-md"
          :style="{ background: 'var(--surface)' }"
        />
      </div>

      <div v-else-if="isError" class="mx-auto max-w-md">
        <AppAlert>{{ (error as Error)?.message ?? 'No se pudieron cargar los KPIs.' }}</AppAlert>
        <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
      </div>

      <div v-else-if="resumen" class="grid gap-3 lg:grid-cols-2">
        <!-- ─── cifra protagonista + composición ─── -->
        <section class="panel p-4 lg:col-span-2">
          <div class="grid gap-6 sm:grid-cols-[auto_1fr] sm:items-center">
            <div class="sm:border-r sm:pr-6" :style="{ borderColor: 'var(--border)' }">
              <p class="text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                Unidades en la flota
              </p>
              <p class="text-5xl font-semibold leading-none">{{ resumen.total }}</p>
            </div>

            <!-- Barras por fila. El valor va en la punta; el nombre, antes. -->
            <div class="grid gap-2.5">
              <div
                v-for="f in composicion"
                :key="f.clave"
                class="grid grid-cols-[9rem_1fr_auto] items-center gap-3"
                :title="`${f.nombre}: ${f.valor} de ${resumen.total} (${f.porcentaje}%)`"
              >
                <span class="flex items-center gap-2 text-sm">
                  <span
                    class="size-2 shrink-0 rounded-full"
                    :style="{ background: COLOR_ESTADO[f.clave] }"
                    aria-hidden="true"
                  />
                  {{ f.nombre }}
                </span>

                <span class="h-2.5 overflow-hidden rounded-sm" :style="{ background: 'var(--surface-sunken)' }">
                  <span
                    class="block h-full"
                    :style="{
                      width: `${f.ancho}%`,
                      background: COLOR_ESTADO[f.clave],
                      borderRadius: '0 4px 4px 0',
                    }"
                  />
                </span>

                <span class="text-right text-sm">
                  <span class="font-semibold">{{ f.valor }}</span>
                  <span class="ml-1.5 text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                    {{ f.porcentaje }}%
                  </span>
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- ─── cobertura de conductor ─── -->
        <section class="panel p-4">
          <h2 class="mb-3 text-sm font-semibold">Cobertura de conductor</h2>

          <p class="text-3xl font-semibold leading-none">{{ cobertura }}%</p>
          <p class="mt-1 text-xs" :style="{ color: 'var(--on-surface-muted)' }">
            {{ resumen.con_conductor }} de {{ resumen.total }} unidades con conductor vinculado
          </p>

          <div
            class="mt-3 h-2.5 overflow-hidden rounded-sm"
            role="meter"
            :aria-valuenow="cobertura"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="`Cobertura de conductor: ${cobertura} por ciento`"
            :style="{ background: 'var(--surface-sunken)' }"
          >
            <span
              class="block h-full"
              :style="{
                width: `${cobertura}%`,
                background: colorCobertura,
                borderRadius: '0 4px 4px 0',
              }"
            />
          </div>

          <dl class="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt class="text-xs" :style="{ color: 'var(--on-surface-muted)' }">Con conductor</dt>
              <dd class="text-xl font-semibold">{{ resumen.con_conductor }}</dd>
            </div>
            <div>
              <dt class="text-xs" :style="{ color: 'var(--on-surface-muted)' }">Sin conductor</dt>
              <dd class="text-xl font-semibold">{{ resumen.sin_conductor }}</dd>
            </div>
          </dl>
        </section>

        <!-- ─── sin señal ─── -->
        <section class="panel p-4">
          <div class="mb-3 flex items-baseline justify-between gap-3">
            <h2 class="text-sm font-semibold">Más tiempo sin reportar</h2>
            <span class="font-mono text-xs tabular" :style="{ color: 'var(--on-surface-muted)' }">
              {{ resumen.sin_senal }}
            </span>
          </div>

          <ul v-if="sinSenal.length" class="divide-y" :style="{ borderColor: 'var(--border)' }">
            <li v-for="v in sinSenal" :key="v.id" class="flex items-baseline gap-3 py-2 text-sm">
              <NuxtLink
                :to="`/app/vehiculos/${v.id}`"
                class="min-w-0 flex-1 truncate font-mono hover:underline"
              >
                {{ v.display_name }}
              </NuxtLink>
              <span class="shrink-0 font-mono text-xs tabular" :style="{ color: 'var(--on-surface-muted)' }">
                {{ haceCuanto(v.minutes_since_report) }}
              </span>
            </li>
          </ul>

          <p v-else class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
            Todas las unidades están reportando.
          </p>
        </section>

        <!-- ─── sin conductor ─── -->
        <section class="panel p-4 lg:col-span-2">
          <div class="mb-3 flex items-baseline justify-between gap-3">
            <h2 class="text-sm font-semibold">Unidades sin conductor vinculado</h2>
            <span class="font-mono text-xs tabular" :style="{ color: 'var(--on-surface-muted)' }">
              {{ resumen.sin_conductor }}
            </span>
          </div>

          <ul
            v-if="sinConductor.length"
            class="grid gap-x-8 sm:grid-cols-2 lg:grid-cols-3"
          >
            <li
              v-for="v in sinConductor"
              :key="v.id"
              class="flex items-baseline justify-between gap-3 border-b py-2 text-sm"
              :style="{ borderColor: 'var(--border)' }"
            >
              <NuxtLink
                :to="`/app/vehiculos/${v.id}`"
                class="min-w-0 truncate font-mono hover:underline"
              >
                {{ v.display_name }}
              </NuxtLink>
              <StatusChip :status="v.status" dark />
            </li>
          </ul>

          <p v-else class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
            Todas las unidades tienen conductor vinculado.
          </p>

          <NuxtLink
            v-if="resumen.sin_conductor > sinConductor.length"
            to="/app/mapa"
            class="btn btn-ghost mt-3 justify-self-start"
          >
            Ver las {{ resumen.sin_conductor }} en el mapa
          </NuxtLink>
        </section>
      </div>
    </div>
  </div>
</template>
