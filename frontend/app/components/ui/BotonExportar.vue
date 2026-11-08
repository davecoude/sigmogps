<script setup lang="ts">
/**
 * Descarga de CSV.
 *
 * Es un enlace, no un fetch: el API vive bajo el mismo origen gracias al
 * proxy, así que el navegador manda la cookie de sesión solo y maneja la
 * descarga sin que haya que construir un blob ni un object URL.
 */
defineProps<{ recurso: 'vehicles' | 'drivers' | 'passengers'; etiqueta?: string }>()

const { puede } = useAuth()
const base = useRuntimeConfig().public.apiBaseUrl
</script>

<template>
  <a
    v-if="puede('export:csv')"
    :href="`${base}/exports/${recurso}.csv`"
    class="btn btn-ghost"
    download
  >
    {{ etiqueta ?? 'Exportar CSV' }}
  </a>
</template>
