/**
 * Cuántas filas de tabla caben en el espacio disponible.
 *
 * El tamaño de página no se fija a ojo: se mide el contenedor y se divide por
 * el alto real de una fila. Un portátil de 13" y un monitor de 27" muestran
 * cantidades distintas y ninguno obliga a hacer scroll.
 */
const ALTO_FILA = 45 // px · fila con padding p-3 y texto de 14 px
const ALTO_ENCABEZADO = 41 // px · thead
const ALTO_PAGINADOR = 56 // px · barra de paginación bajo la tabla

export function useFilasQueCaben(
  contenedor: Ref<HTMLElement | null>,
  { minimo = 5, maximo = 50 } = {},
) {
  const filas = ref(minimo)

  function recalcular() {
    const el = contenedor.value
    if (!el) return
    const disponible = el.clientHeight - ALTO_ENCABEZADO - ALTO_PAGINADOR
    const caben = Math.floor(disponible / ALTO_FILA)
    filas.value = Math.min(maximo, Math.max(minimo, caben))
  }

  let observador: ResizeObserver | null = null

  onMounted(() => {
    recalcular()
    observador = new ResizeObserver(recalcular)
    if (contenedor.value) observador.observe(contenedor.value)
  })

  onBeforeUnmount(() => {
    observador?.disconnect()
    observador = null
  })

  return { filas }
}
