<script setup lang="ts">
/** <dialog> nativo: foco atrapado y cierre con Escape sin código propio. */
defineProps<{ titulo: string; descripcion?: string }>()
const emit = defineEmits<{ cerrar: [] }>()

const dialogo = ref<HTMLDialogElement | null>(null)

onMounted(() => {
  dialogo.value?.showModal()
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <dialog
    ref="dialogo"
    class="surface-dark m-auto w-[min(32rem,calc(100vw-2rem))] rounded-lg border p-0
           backdrop:bg-black/65"
    :style="{
      background: 'var(--surface)',
      color: 'var(--on-surface)',
      borderColor: 'var(--border)',
    }"
    :aria-label="titulo"
    @cancel.prevent="emit('cerrar')"
    @close="emit('cerrar')"
  >
    <header
      class="flex items-start justify-between gap-4 border-b p-5"
      :style="{ borderColor: 'var(--border)' }"
    >
      <div class="min-w-0">
        <h2 class="text-base font-semibold">{{ titulo }}</h2>
        <p v-if="descripcion" class="mt-1 text-sm" :style="{ color: 'var(--on-surface-muted)' }">
          {{ descripcion }}
        </p>
      </div>
      <button
        type="button"
        class="shrink-0 text-lg leading-none"
        :style="{ color: 'var(--on-surface-muted)' }"
        aria-label="Cerrar"
        @click="emit('cerrar')"
      >
        ✕
      </button>
    </header>
    <div class="p-5"><slot /></div>
  </dialog>
</template>
