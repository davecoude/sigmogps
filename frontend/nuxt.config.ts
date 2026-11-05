import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2026-11-05',
  devtools: { enabled: true },

  css: [
    'leaflet/dist/leaflet.css',
    'leaflet.markercluster/dist/MarkerCluster.css',
    'leaflet.markercluster/dist/MarkerCluster.Default.css',
    '~/assets/css/main.css',
  ],

  vite: {
    plugins: [
      tailwindcss()
    ],
  },

  runtimeConfig: {
    public: {
      // Se sobreescribe con NUXT_PUBLIC_API_BASE_URL en Vercel.
      apiBaseUrl: 'http://localhost:8000/api/v1',
    },
  },

  app: {
    // Se inyecta mientras arranca el JS en las rutas sin SSR (DEP-04).
    spaLoadingTemplate: '~/spa-loading-template.html',

    head: {
      htmlAttrs: { lang: 'es-CO' },
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap',
        },
      ],
    },
  },

  components: [{ path: '~/components', pathPrefix: false }],

  // Nuxt solo auto-importa composables/ y utils/. La estructura por
  // features (ARQ-08) necesita declararse aquí.
  imports: {
    dirs: ['composables/**', 'features/**'],
  },

  // La landing se prerrenderiza: es lo que mide Lighthouse (UX-07).
  // El panel es solo cliente; no tiene sentido renderizarlo en el servidor
  // cuando la sesión vive en una cookie HttpOnly del backend.
  routeRules: {
    '/': { prerender: true },
    '/app/**': { ssr: false },
  },

  typescript: { strict: true },
})
