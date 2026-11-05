<script setup lang="ts">
defineProps<{ tone?: 'error' | 'warn' | 'info' }>()
</script>

<template>
  <div
    role="alert"
    class="flex gap-2.5 rounded-md border px-3.5 py-3 text-sm"
    :class="[
      (tone ?? 'error') === 'error' && 'border-brand/30 bg-brand-soft text-brand',
      tone === 'warn' && 'border-ochre/30 bg-ochre-soft text-ochre',
      tone === 'info' && 'border-teal/30 bg-teal-soft text-teal-ink',
    ]"
  >
    <span aria-hidden="true">●</span>
    <span class="min-w-0"><slot /></span>
  </div>
</template>
