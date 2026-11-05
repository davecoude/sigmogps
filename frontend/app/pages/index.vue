<script setup lang="ts">
definePageMeta({ layout: false })

useHead({
  title: 'sigmoGPS · Monitoreo de flota en tiempo real',
  meta: [
    {
      name: 'description',
      content:
        'Posición, estado y conductor de cada vehículo de tu flota, leídos de Wialon y presentados para decidir en segundos.',
    },
  ],
})

// Sin bloquear el render: la landing se prerrenderiza y debe pintar al instante.
const { user, cargarSesion } = useAuth()
onMounted(() => cargarSesion())

const kpis = [
  { valor: '24/7', texto: 'Monitoreo continuo' },
  { valor: '<10 s', texto: 'Refresco de posición' },
  { valor: '3', texto: 'Roles con permisos propios' },
  { valor: '100%', texto: 'Cambios reflejados en Wialon' },
]

const pasos = [
  {
    n: '01',
    titulo: 'Conectamos tu cuenta',
    texto: 'El backend se autentica con tu token y mantiene la sesión viva sin que nadie la toque.',
  },
  {
    n: '02',
    titulo: 'Traducimos el dato',
    texto: 'Cada unidad se convierte en un modelo propio con unidades, estado y hora local.',
  },
  {
    n: '03',
    titulo: 'Tu equipo opera',
    texto: 'Cada rol ve lo suyo: el visualizador consulta, el operador edita, el admin gobierna.',
  },
]
</script>

<template>
  <div class="bg-paper text-ink">
    <!-- ───────── navegación ───────── -->
    <header class="border-b border-line">
      <nav
        class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6"
        aria-label="Principal"
      >
        <NuxtLink to="/" class="inline-flex items-center gap-2 text-lg font-bold tracking-tight">
          <svg viewBox="0 0 24 24" class="size-5" aria-hidden="true">
            <path d="M12 22c4.5-5.2 7-9 7-12a7 7 0 1 0-14 0c0 3 2.5 6.8 7 12z" fill="#EB162C" />
            <circle cx="12" cy="10" r="2.7" fill="#fff" />
          </svg>
          sigmo<span class="text-brand">GPS</span>
        </NuxtLink>

        <div class="hidden gap-7 text-sm font-medium text-ink-2 md:flex">
          <a href="#modulos" class="hover:text-ink">Módulos</a>
          <a href="#como-funciona" class="hover:text-ink">Cómo funciona</a>
        </div>

        <!-- Con sesión activa, acceso directo al panel (RF-03). -->
        <NuxtLink v-if="user" to="/app/mapa">
          <AppButton shape="pill">Ir al panel</AppButton>
        </NuxtLink>
        <NuxtLink v-else to="/ingresar">
          <AppButton shape="pill">Iniciar sesión</AppButton>
        </NuxtLink>
      </nav>
    </header>

    <!-- ───────── hero ───────── -->
    <section class="mx-auto max-w-6xl px-4 pb-10 pt-14 text-center sm:px-6 sm:pt-20">
      <span
        class="inline-flex items-center gap-2 rounded-full bg-brand-soft px-3.5 py-1.5 text-xs font-semibold text-brand"
      >
        <span class="size-1.5 rounded-full bg-brand" aria-hidden="true" />
        Conectado a Wialon en tiempo real
      </span>

      <h1 class="mx-auto mt-5 max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
        Toda tu flota en <span class="text-brand">un solo mapa</span>, al segundo
      </h1>

      <p class="mx-auto mt-5 max-w-xl text-base text-ink-2 sm:text-lg">
        Posición, estado y conductor de cada vehículo, leídos directamente de tu cuenta de
        Wialon y presentados para que un operador decida en cinco segundos.
      </p>

      <div class="mt-7 flex flex-wrap justify-center gap-3">
        <NuxtLink :to="user ? '/app/mapa' : '/ingresar'">
          <AppButton shape="pill">{{ user ? 'Ir al panel' : 'Iniciar sesión' }}</AppButton>
        </NuxtLink>
        <a href="#modulos"><AppButton shape="pill" variant="ghost">Ver módulos</AppButton></a>
      </div>
    </section>

    <!-- Ilustración en SVG, no un mapa real: la landing se mide con Lighthouse
         y las teselas costarían el LCP (UX-07). -->
    <section class="mx-auto max-w-6xl px-4 sm:px-6" aria-hidden="true">
      <div class="overflow-hidden rounded-lg border border-line bg-wash-2">
        <svg viewBox="0 0 1200 420" class="h-auto w-full">
          <rect width="1200" height="420" fill="#F7F4FA" />
          <path d="M980 0 L1060 140 L1010 270 L1090 420 L1200 420 L1200 0 Z" fill="#DCE8EC" />
          <g stroke="#E4DDEA" stroke-width="3">
            <path v-for="y in 7" :key="`h${y}`" :d="`M0 ${y * 55} H1200`" />
            <path v-for="x in 11" :key="`v${x}`" :d="`M${x * 105} 0 V420`" />
          </g>
          <path d="M0 340 Q 260 280 470 340 T 940 310" stroke="#D6CCDE" stroke-width="7" fill="none" />
          <path d="M150 0 V420" stroke="#D6CCDE" stroke-width="7" />
          <path d="M0 150 H1200" stroke="#D6CCDE" stroke-width="7" />

          <g>
            <circle cx="300" cy="150" r="17" fill="#1E8C93" stroke="#fff" stroke-width="4" />
            <circle cx="620" cy="248" r="17" fill="#6B6B6B" stroke="#fff" stroke-width="4" />
            <circle cx="860" cy="120" r="17" fill="#EB162C" stroke="#fff" stroke-width="4" />
            <circle cx="470" cy="340" r="23" fill="#A81A2B" stroke="#fff" stroke-width="4" />
            <text
              x="470" y="347" text-anchor="middle" fill="#fff"
              font-size="15" font-weight="700" font-family="Inter, sans-serif"
            >12</text>
          </g>
        </svg>
      </div>
      <p class="mt-2 text-right text-[11px] text-muted">
        Ilustración. En el panel el mapa usa teselas de OpenStreetMap.
      </p>
    </section>

    <!-- ───────── cifras ───────── -->
    <section class="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <dl class="grid grid-cols-2 gap-7 border-y border-line py-8 lg:grid-cols-4">
        <div v-for="k in kpis" :key="k.texto" class="flex items-baseline gap-3">
          <dt class="sr-only">{{ k.texto }}</dt>
          <dd class="flex items-baseline gap-3">
            <span class="text-3xl font-bold tracking-tight tabular sm:text-4xl">{{ k.valor }}</span>
            <span class="max-w-[11ch] text-[11px] font-semibold uppercase tracking-wider text-muted">
              {{ k.texto }}
            </span>
          </dd>
        </div>
      </dl>
    </section>

    <!-- ───────── módulos ───────── -->
    <section id="modulos" class="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <div class="grid gap-9 lg:grid-cols-[1fr_1.25fr]">
        <div>
          <p class="text-xs font-semibold uppercase tracking-widest text-brand">
            Por qué sigmoGPS
          </p>
          <h2 class="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            El dato crudo de Wialon no sirve para decidir
          </h2>
          <p class="mt-4 max-w-md text-ink-2">
            Llega en timestamps UNIX, velocidades sin unidad y rumbos en grados. sigmoGPS lo
            traduce a estados que un operador entiende sin manual.
          </p>
        </div>

        <div class="grid gap-3.5 sm:grid-cols-2">
          <article class="rounded-lg border border-line bg-wash-2 p-5">
            <div class="grid size-9 place-items-center rounded-md bg-ink text-paper" aria-hidden="true">◉</div>
            <h3 class="mt-3 font-semibold">Estado derivado</h3>
            <p class="mt-1.5 text-sm text-muted">
              En movimiento, detenido o sin señal, calculado con umbrales documentados.
            </p>
          </article>

          <article class="rounded-lg border border-line bg-wash-2 p-5">
            <div class="grid size-9 place-items-center rounded-md bg-ink text-paper" aria-hidden="true">⏱</div>
            <h3 class="mt-3 font-semibold">Hora local</h3>
            <p class="mt-1.5 text-sm text-muted">
              UTC en el API, America/Bogota en pantalla. Sin ambigüedad.
            </p>
          </article>

          <article class="rounded-lg border border-line bg-paper p-5 sm:col-span-2">
            <div class="grid size-9 place-items-center rounded-md bg-ink text-paper" aria-hidden="true">⊞</div>
            <h3 class="mt-3 font-semibold">Conductores y pasajeros, editables desde aquí</h3>
            <p class="mt-1.5 text-sm text-muted">
              Cada alta, cambio y baja queda escrita en Wialon. Lo que ves en sigmoGPS es lo que
              hay en la plataforma, no una copia que se desactualiza.
            </p>
          </article>
        </div>
      </div>
    </section>

    <!-- ───────── cómo funciona ───────── -->
    <section id="como-funciona" class="mx-auto max-w-6xl border-t border-line px-4 py-14 sm:px-6">
      <p class="text-xs font-semibold uppercase tracking-widest text-muted">Cómo funciona</p>
      <ol class="mt-6 grid gap-7 sm:grid-cols-3">
        <li v-for="p in pasos" :key="p.n" class="border-t-2 border-brand pt-4">
          <span class="font-mono text-xs font-medium text-brand">{{ p.n }}</span>
          <h3 class="mt-2 text-lg font-semibold">{{ p.titulo }}</h3>
          <p class="mt-1.5 text-sm text-muted">{{ p.texto }}</p>
        </li>
      </ol>
    </section>

    <!-- ───────── llamado a la acción ───────── -->
    <section class="mx-auto max-w-6xl px-4 pb-14 sm:px-6">
      <div class="grid justify-items-center gap-4 rounded-xl bg-ink px-6 py-12 text-center">
        <h2 class="max-w-lg text-2xl font-semibold tracking-tight text-wash sm:text-3xl">
          Entra y mira dónde está tu flota ahora mismo
        </h2>
        <p class="max-w-md text-sm text-[#B9B2C2]">
          Credenciales entregadas por tu administrador. El primer ingreso pide cambiar la
          contraseña.
        </p>
        <NuxtLink :to="user ? '/app/mapa' : '/ingresar'">
          <AppButton shape="pill">{{ user ? 'Ir al panel' : 'Iniciar sesión' }}</AppButton>
        </NuxtLink>
      </div>
    </section>

    <!-- ───────── pie ───────── -->
    <footer class="border-t border-line">
      <div
        class="mx-auto flex max-w-6xl flex-wrap justify-between gap-4 px-4 py-6 text-xs text-muted sm:px-6"
      >
        <span>sigmoGPS · Bogotá, Colombia</span>
        <span>Telemetría vía Wialon · Mapas © colaboradores de OpenStreetMap</span>
      </div>
    </footer>
  </div>
</template>
