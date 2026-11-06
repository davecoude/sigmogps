<script setup lang="ts">
const { toasts, cerrar } = useToast()
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-0 bottom-4 z-[2000] flex flex-col items-center gap-2 px-4"
    role="status"
    aria-live="polite"
  >
    <TransitionGroup
      enter-from-class="opacity-0 translate-y-2"
      enter-active-class="transition duration-200"
      leave-to-class="opacity-0"
      leave-active-class="transition duration-150"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex max-w-md items-start gap-3 rounded-md px-4 py-3 text-sm shadow-lg"
        :class="{
          'bg-teal-ink text-white': t.tono === 'exito',
          'bg-brand text-white': t.tono === 'error',
          'bg-ochre text-white': t.tono === 'aviso',
        }"
      >
        <span class="min-w-0">{{ t.mensaje }}</span>
        <button
          type="button"
          class="shrink-0 opacity-70 hover:opacity-100"
          aria-label="Cerrar aviso"
          @click="cerrar(t.id)"
        >
          ✕
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
