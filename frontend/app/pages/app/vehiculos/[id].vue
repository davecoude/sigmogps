<script setup lang="ts">
definePageMeta({ middleware: 'auth', layout: 'app', permiso: 'vehicles:read' })

const ruta = useRoute()
const id = computed(() => Number(ruta.params.id))

const { data: vehiculo, isPending, isError, error, refetch } = useVehicleDetail(id)
const { data: pasajeros, isPending: cargandoPasajeros } = useVehiclePassengers(id)

useHead({ title: () => `${vehiculo.value?.display_name ?? 'Vehículo'} · sigmoGPS` })

/**
 * Wialon entrega la marca de tiempo en segundos UNIX. El backend la normaliza
 * a ISO-8601 en UTC y aquí se presenta en la zona del usuario (sección 4.4).
 */
function horaLocal(iso: string) {
  return new Date(iso).toLocaleString('es-CO', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'America/Bogota',
  })
}

function haceCuanto(minutos: number | null) {
  if (minutos === null) return 'sin reporte'
  if (minutos < 1) return 'hace menos de un minuto'
  if (minutos < 60) return `hace ${Math.round(minutos)} min`
  const horas = minutos / 60
  if (horas < 24) return `hace ${Math.round(horas)} h`
  return `hace ${Math.round(horas / 24)} días`
}

const RUMBOS: Record<string, string> = {
  N: 'norte',
  NE: 'nororiente',
  E: 'oriente',
  SE: 'suroriente',
  S: 'sur',
  SO: 'suroccidente',
  O: 'occidente',
  NO: 'noroccidente',
}

function iniciales(nombre: string) {
  return nombre
    .split(/\s+/)
    .map((p) => p[0] ?? '')
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
</script>

<template>
  <div class="flex h-dvh flex-col">
    <!-- ───────── cabecera ───────── -->
    <header
      class="flex flex-wrap items-center gap-3 border-b p-4"
      :style="{ borderColor: 'var(--border)' }"
    >
      <NuxtLink to="/app/mapa" class="btn-row">&larr; Mapa</NuxtLink>

      <div class="mr-auto flex min-w-0 items-baseline gap-3">
        <h1 class="truncate font-mono text-lg font-semibold">
          {{ vehiculo?.display_name ?? '…' }}
        </h1>
        <StatusChip v-if="vehiculo" :status="vehiculo.status" dark />
      </div>

      <span
        v-if="vehiculo && vehiculo.plate && vehiculo.name !== vehiculo.plate"
        class="text-xs"
        :style="{ color: 'var(--on-surface-muted)' }"
      >
        Unidad en Wialon: {{ vehiculo.name }}
      </span>
    </header>

    <!-- ───────── contenido ───────── -->
    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      <div v-if="isPending" class="grid gap-3 lg:grid-cols-2" aria-busy="true">
        <div
          v-for="n in 4"
          :key="n"
          class="h-52 animate-pulse rounded-md"
          :style="{ background: 'var(--surface)' }"
        />
      </div>

      <div v-else-if="isError" class="mx-auto max-w-md">
        <AppAlert>{{ (error as Error)?.message ?? 'No se pudo cargar el vehículo.' }}</AppAlert>
        <AppButton class="mt-3" variant="ghost" block @click="refetch()">Reintentar</AppButton>
      </div>

      <div v-else-if="vehiculo" class="grid gap-3 lg:grid-cols-2">
        <!-- ─── última lectura (RF-12) ─── -->
        <section class="panel p-4">
          <h2 class="mb-3 text-sm font-semibold">Última lectura</h2>

          <div v-if="vehiculo.position">
            <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
              <dt :style="{ color: 'var(--on-surface-muted)' }">Velocidad</dt>
              <dd class="text-right font-mono tabular">{{ vehiculo.position.speed_kmh }} km/h</dd>

              <dt :style="{ color: 'var(--on-surface-muted)' }">Rumbo</dt>
              <dd class="text-right font-mono tabular">
                <template v-if="vehiculo.position.cardinal">
                  {{ vehiculo.position.cardinal }}
                  <span :style="{ color: 'var(--on-surface-muted)' }">
                    ({{ vehiculo.position.course_degrees }}°,
                    {{ RUMBOS[vehiculo.position.cardinal] ?? 'sin dato' }})
                  </span>
                </template>
                <span v-else :style="{ color: 'var(--on-surface-muted)' }">sin dato</span>
              </dd>

              <dt :style="{ color: 'var(--on-surface-muted)' }">Coordenadas</dt>
              <dd class="text-right font-mono text-xs tabular">
                {{ vehiculo.position.latitude.toFixed(6) }},
                {{ vehiculo.position.longitude.toFixed(6) }}
              </dd>

              <dt :style="{ color: 'var(--on-surface-muted)' }">Altitud</dt>
              <dd class="text-right font-mono tabular">
                {{ vehiculo.position.altitude_m ?? '—' }} m
              </dd>

              <dt :style="{ color: 'var(--on-surface-muted)' }">Satélites</dt>
              <dd class="text-right font-mono tabular">
                {{ vehiculo.position.satellites ?? '—' }}
              </dd>

              <dt :style="{ color: 'var(--on-surface-muted)' }">Reportado</dt>
              <dd class="text-right">
                <span class="font-mono text-xs tabular">
                  {{ horaLocal(vehiculo.position.reported_at) }}
                </span>
                <span class="block text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                  {{ haceCuanto(vehiculo.minutes_since_report) }}
                </span>
              </dd>
            </dl>

            <p class="field-hint mt-3 border-t pt-2.5" :style="{ borderColor: 'var(--border)' }">
              Wialon reporta la hora en segundos UNIX y la velocidad sin unidad. El API las
              normaliza a ISO-8601 UTC y km/h; la hora se muestra en America/Bogota.
            </p>
          </div>

          <p v-else class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
            Esta unidad nunca ha reportado una posición válida.
          </p>
        </section>

        <!-- ─── mapa ─── -->
        <section class="panel overflow-hidden" style="min-height: 18rem">
          <ClientOnly>
            <FleetMap
              v-if="vehiculo.position"
              :vehicles="[vehiculo]"
              :selected-id="vehiculo.id"
            />
            <div
              v-else
              class="grid h-full place-items-center p-6 text-center text-sm"
              :style="{ color: 'var(--on-surface-muted)' }"
            >
              Sin posición que mostrar en el mapa.
            </div>
          </ClientOnly>
        </section>

        <!-- ─── conductor (RF-13) ─── -->
        <section class="panel p-4">
          <h2 class="mb-3 text-sm font-semibold">Conductor vinculado</h2>

          <div v-if="vehiculo.driver_name" class="flex items-center gap-3">
            <span
              class="grid size-10 shrink-0 place-items-center rounded-full text-sm font-semibold"
              :style="{ background: 'var(--surface-sunken)' }"
              aria-hidden="true"
            >
              {{ iniciales(vehiculo.driver_name) }}
            </span>
            <div class="min-w-0">
              <p class="truncate font-medium">{{ vehiculo.driver_name }}</p>
              <NuxtLink
                to="/app/conductores"
                class="text-xs hover:underline"
                :style="{ color: 'var(--on-surface-muted)' }"
              >
                Ver en conductores
              </NuxtLink>
            </div>
          </div>

          <div v-else class="grid gap-2">
            <p class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
              Sin conductor vinculado en Wialon.
            </p>
            <NuxtLink to="/app/conductores" class="btn btn-ghost justify-self-start">
              Vincular uno
            </NuxtLink>
          </div>
        </section>

        <!-- ─── pasajeros (RF-09) ─── -->
        <section class="panel p-4">
          <div class="mb-3 flex items-baseline justify-between gap-3">
            <h2 class="text-sm font-semibold">Pasajeros asignados</h2>
            <span
              v-if="pasajeros?.length"
              class="font-mono text-xs tabular"
              :style="{ color: 'var(--on-surface-muted)' }"
            >
              {{ pasajeros.length }}
            </span>
          </div>

          <p v-if="cargandoPasajeros" class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
            Cargando asignaciones…
          </p>

          <ul
            v-else-if="pasajeros?.length"
            class="divide-y"
            :style="{ borderColor: 'var(--border)' }"
          >
            <li
              v-for="p in pasajeros"
              :key="p.id"
              class="flex items-baseline justify-between gap-3 py-2 text-sm"
            >
              <span class="min-w-0 truncate">{{ p.name }}</span>
              <span
                class="shrink-0 font-mono text-xs"
                :style="{ color: 'var(--on-surface-muted)' }"
              >
                {{ p.code || '—' }}
              </span>
            </li>
          </ul>

          <div v-else class="grid gap-2">
            <p class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
              Ningún pasajero asignado a este vehículo.
            </p>
            <NuxtLink to="/app/pasajeros" class="btn btn-ghost justify-self-start">
              Asignar uno
            </NuxtLink>
          </div>
        </section>

        <!-- ─── campos personalizados ─── -->
        <section class="panel p-4 lg:col-span-2">
          <div class="mb-3 flex items-baseline justify-between gap-3">
            <h2 class="text-sm font-semibold">Campos personalizados</h2>
            <span
              class="font-mono text-xs tabular"
              :style="{ color: 'var(--on-surface-muted)' }"
            >
              {{ vehiculo.custom_fields.length }}
            </span>
          </div>

          <dl
            v-if="vehiculo.custom_fields.length"
            class="grid gap-x-8 text-sm sm:grid-cols-2 lg:grid-cols-3"
          >
            <div
              v-for="c in vehiculo.custom_fields"
              :key="c.id"
              class="flex items-baseline justify-between gap-3 border-b py-1.5"
              :style="{ borderColor: 'var(--border)' }"
            >
              <dt class="min-w-0 truncate text-xs" :style="{ color: 'var(--on-surface-muted)' }">
                {{ c.name }}
              </dt>
              <dd class="shrink-0 text-right font-mono text-xs">{{ c.value || '—' }}</dd>
            </div>
          </dl>

          <p v-else class="text-sm" :style="{ color: 'var(--on-surface-muted)' }">
            Esta unidad no tiene campos personalizados en Wialon.
          </p>
        </section>
      </div>
    </div>
  </div>
</template>
