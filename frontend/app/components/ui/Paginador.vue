<script setup lang="ts">
/**
 * Paginación numerada con elisión.
 *
 * Muestra siempre la primera y la última página, y una ventana alrededor de
 * la actual: 1 … 4 5 [6] 7 8 … 50. Así el usuario sabe cuántas páginas hay en
 * total y puede saltar cerca, sin una fila de cincuenta botones.
 */
const props = withDefaults(
  defineProps<{
    pagina: number
    paginas: number
    total: number
    /** Cuántas páginas mostrar a cada lado de la actual. */
    ventana?: number
    etiqueta?: string
  }>(),
  { ventana: 2, etiqueta: 'registros' },
)

const emit = defineEmits<{ cambiar: [pagina: number] }>()

type Entrada = number | 'elision-izq' | 'elision-der'

const entradas = computed<Entrada[]>(() => {
  const { pagina, paginas, ventana } = props
  if (paginas <= 1) return [1]

  const desde = Math.max(2, pagina - ventana)
  const hasta = Math.min(paginas - 1, pagina + ventana)

  const salida: Entrada[] = [1]
  if (desde > 2) salida.push('elision-izq')
  for (let p = desde; p <= hasta; p++) salida.push(p)
  if (hasta < paginas - 1) salida.push('elision-der')
  if (paginas > 1) salida.push(paginas)
  return salida
})

function ir(p: number) {
  if (p >= 1 && p <= props.paginas && p !== props.pagina) emit('cambiar', p)
}
</script>

<template>
  <nav
    class="flex flex-wrap items-center justify-between gap-3 px-1 py-3 text-xs"
    :aria-label="`Paginación de ${etiqueta}`"
  >
    <p :style="{ color: 'var(--on-surface-muted)' }" class="tabular">
      {{ total }} {{ etiqueta }} · página {{ pagina }} de {{ paginas }}
    </p>

    <ul class="flex items-center gap-1">
      <li>
        <button
          type="button"
          class="pag-boton"
          :disabled="pagina <= 1"
          aria-label="Página anterior"
          @click="ir(pagina - 1)"
        >
          ‹
        </button>
      </li>

      <li v-for="(e, i) in entradas" :key="`${e}-${i}`">
        <span
          v-if="typeof e === 'string'"
          class="px-1.5 select-none"
          :style="{ color: 'var(--on-surface-muted)' }"
          aria-hidden="true"
        >
          …
        </span>
        <button
          v-else
          type="button"
          class="pag-boton tabular"
          :class="e === pagina && 'pag-boton-activo'"
          :aria-current="e === pagina ? 'page' : undefined"
          :aria-label="`Página ${e}`"
          @click="ir(e)"
        >
          {{ e }}
        </button>
      </li>

      <li>
        <button
          type="button"
          class="pag-boton"
          :disabled="pagina >= paginas"
          aria-label="Página siguiente"
          @click="ir(pagina + 1)"
        >
          ›
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.pag-boton {
  min-width: 1.875rem;
  height: 1.875rem;
  padding-inline: 0.375rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--on-surface-muted);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.12s ease, border-color 0.12s ease;
}
.pag-boton:hover:not(:disabled):not(.pag-boton-activo) {
  color: var(--on-surface);
  border-color: var(--border-strong);
}
.pag-boton:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pag-boton-activo {
  border-color: var(--action);
  color: var(--on-surface);
  background: color-mix(in srgb, var(--action) 18%, transparent);
  cursor: default;
}
</style>
