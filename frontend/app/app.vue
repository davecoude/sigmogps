<script setup lang="ts">
/**
 * Mientras se resuelve la sesión, el panel muestra una pantalla de arranque
 * en vez de quedar en blanco (DEP-04). La landing y el login sí se renderizan
 * en el servidor, así que no la necesitan.
 */
const { cargado } = useAuth()
const route = useRoute()

const arrancando = computed(() => route.path.startsWith('/app') && !cargado.value)
</script>

<template>
  <div>
    <NuxtRouteAnnouncer />
    <NuxtLoadingIndicator color="#EB162C" />
    <BootScreen v-if="arrancando" />
    <NuxtLayout v-else>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
