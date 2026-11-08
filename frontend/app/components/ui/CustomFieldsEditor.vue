<script setup lang="ts">
/**
 * Editor de campos personalizados (RF-27).
 *
 * Trabaja sobre filas con nombre y valor, no sobre un objeto, para que el
 * usuario pueda renombrar un campo sin perder su valor y para conservar el
 * orden mientras edita. Al guardar se convierte en el conjunto completo: lo
 * que no esté en la lista se elimina en Wialon.
 *
 * Los datos reales traen nombres de más de cincuenta caracteres, así que las
 * filas se apilan en vertical en pantallas angostas.
 */
interface Fila {
  clave: string
  valor: string
}

const modelo = defineModel<Record<string, string>>({ required: true })

const filas = ref<Fila[]>(
  Object.entries(modelo.value).map(([clave, valor]) => ({ clave, valor })),
)

const duplicados = computed(() => {
  const vistos = new Set<string>()
  const repetidos = new Set<string>()
  for (const f of filas.value) {
    const k = f.clave.trim().toLowerCase()
    if (!k) continue
    if (vistos.has(k)) repetidos.add(k)
    vistos.add(k)
  }
  return repetidos
})

function esDuplicada(f: Fila) {
  return duplicados.value.has(f.clave.trim().toLowerCase())
}

function agregar() {
  filas.value.push({ clave: '', valor: '' })
}

function quitar(indice: number) {
  filas.value.splice(indice, 1)
}

// Sincroniza hacia el modelo en cada cambio; las filas sin nombre se descartan.
watch(
  filas,
  (actuales) => {
    const salida: Record<string, string> = {}
    for (const f of actuales) {
      const k = f.clave.trim()
      if (k) salida[k] = f.valor
    }
    modelo.value = salida
  },
  { deep: true },
)

defineExpose({ hayDuplicados: computed(() => duplicados.value.size > 0) })
</script>

<template>
  <fieldset class="grid gap-2">
    <legend class="field-label mb-1">Campos personalizados</legend>

    <p v-if="!filas.length" class="field-hint">
      Sin campos. Agrega el primero con el botón de abajo.
    </p>

    <div v-for="(f, i) in filas" :key="i" class="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
      <label class="sr-only" :for="`campo-nombre-${i}`">Nombre del campo {{ i + 1 }}</label>
      <input
        :id="`campo-nombre-${i}`"
        v-model="f.clave"
        class="field-input"
        :aria-invalid="esDuplicada(f) ? 'true' : undefined"
        placeholder="cedula"
      />

      <label class="sr-only" :for="`campo-valor-${i}`">Valor del campo {{ i + 1 }}</label>
      <input
        :id="`campo-valor-${i}`"
        v-model="f.valor"
        class="field-input"
        placeholder="1020304050"
      />

      <button
        type="button"
        class="btn-row btn-row-danger justify-self-start sm:justify-self-auto"
        :aria-label="`Eliminar el campo ${f.clave || i + 1}`"
        @click="quitar(i)"
      >
        Eliminar
      </button>
    </div>

    <p v-if="duplicados.size" class="field-error" role="alert">
      Hay nombres de campo repetidos. Solo se guardará el último de cada uno.
    </p>

    <button type="button" class="btn btn-ghost mt-1 justify-self-start" @click="agregar">
      Agregar campo
    </button>
  </fieldset>
</template>
