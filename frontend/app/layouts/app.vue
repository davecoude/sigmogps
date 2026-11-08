<script setup lang="ts">
const { user, salir, puede } = useAuth()
const route = useRoute()

const enlaces = computed(() =>
  [
    { to: '/app/mapa', icono: '◉', texto: 'Mapa', permiso: 'vehicles:read' },
    { to: '/app/tablero', icono: '▤', texto: 'Tablero', permiso: 'vehicles:read' },
    { to: '/app/conductores', icono: '⚇', texto: 'Conductores', permiso: 'drivers:read' },
    { to: '/app/pasajeros', icono: '⚉', texto: 'Pasajeros', permiso: 'passengers:read' },
    { to: '/app/usuarios', icono: '⚿', texto: 'Usuarios', permiso: 'users:manage' },
    { to: '/app/auditoria', icono: '≡', texto: 'Auditoría', permiso: 'audit:read' },
  ].filter((e) => puede(e.permiso)),
)

const iniciales = computed(() =>
  (user.value?.full_name ?? '')
    .split(' ')
    .map((p) => p[0] ?? '')
    .join('')
    .slice(0, 2)
    .toUpperCase(),
)
</script>

<template>
  <!-- Alto exacto de la ventana y sin desborde: así el contenido recibe el
       espacio que sobra y puede decidir cuánto cabe dentro. -->
  <div class="surface-dark flex h-dvh overflow-hidden flex-col bg-console text-console-ink md:flex-row">
    <!-- Riel de navegación. En móvil pasa abajo, al alcance del pulgar. -->
    <nav
      class="order-2 flex shrink-0 items-center gap-1 border-t border-console-line bg-console-3
             px-3 py-2 md:order-1 md:w-16 md:flex-col md:border-r md:border-t-0 md:py-4"
      aria-label="Secciones"
    >
      <span class="hidden md:mb-3 md:grid md:size-8 md:place-items-center md:rounded-md md:bg-brand-hi">
        <svg viewBox="0 0 24 24" class="size-4" aria-hidden="true">
          <path d="M12 22c4.5-5.2 7-9 7-12a7 7 0 1 0-14 0c0 3 2.5 6.8 7 12z" fill="#fff" />
          <circle cx="12" cy="10" r="2.7" fill="#EB162C" />
        </svg>
      </span>

      <NuxtLink
        v-for="e in enlaces"
        :key="e.to"
        :to="e.to"
        :title="e.texto"
        :aria-current="route.path === e.to ? 'page' : undefined"
        class="grid flex-1 place-items-center rounded-md py-2 text-lg transition-colors md:size-10 md:flex-none"
        :class="
          route.path === e.to
            ? 'bg-console-2 text-brand-dark'
            : 'text-console-muted hover:text-console-ink'
        "
      >
        <span aria-hidden="true">{{ e.icono }}</span>
        <span class="sr-only">{{ e.texto }}</span>
      </NuxtLink>

      <span class="hidden md:block md:flex-1" />

      <button
        type="button"
        class="grid size-10 place-items-center rounded-full bg-console-2 text-xs font-semibold
               text-console-ink transition-colors hover:bg-brand-hi hover:text-white"
        :title="`${user?.full_name} · ${user?.role.name} · Cerrar sesión`"
        @click="salir()"
      >
        {{ iniciales }}
        <span class="sr-only">Cerrar sesión</span>
      </button>
    </nav>

    <main class="order-1 min-h-0 min-w-0 flex-1 overflow-hidden md:order-2">
      <slot />
    </main>
  </div>
</template>
