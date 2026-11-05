/** Si ya hay sesión, la landing y el login llevan al panel (RF-03). */
export default defineNuxtRouteMiddleware(async () => {
  const { cargarSesion } = useAuth()
  const me = await cargarSesion()
  if (me) return navigateTo(me.must_change_password ? '/cambiar-clave' : '/app/mapa')
})
