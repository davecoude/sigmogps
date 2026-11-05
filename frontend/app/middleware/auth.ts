/** Guard de rutas privadas (RF-04). Espejo del RBAC del backend, no su reemplazo. */
export default defineNuxtRouteMiddleware(async (to) => {
  const { cargarSesion } = useAuth()
  const me = await cargarSesion()

  if (!me) {
    return navigateTo({ path: '/ingresar', query: { destino: to.fullPath } })
  }

  if (me.must_change_password && to.path !== '/cambiar-clave') {
    return navigateTo('/cambiar-clave')
  }

  // Cada ruta declara el permiso que exige en su `definePageMeta`.
  const requerido = to.meta.permiso as string | undefined
  if (requerido && !me.permissions.includes(requerido)) {
    return navigateTo('/app/mapa')
  }
})
