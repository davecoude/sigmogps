<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'error' | 'warn' | 'info' }>(), { tone: 'error' })
</script>

<template>
  <div
    role="alert"
    class="flex gap-2.5 rounded-md border px-3.5 py-3 text-sm"
    :style="{
      borderColor:
        tone === 'warn'
          ? 'color-mix(in srgb, var(--color-ochre) 45%, transparent)'
          : tone === 'info'
            ? 'color-mix(in srgb, var(--color-teal) 45%, transparent)'
            : 'color-mix(in srgb, var(--danger) 45%, transparent)',
      background:
        tone === 'warn'
          ? 'color-mix(in srgb, var(--color-ochre) 12%, var(--surface))'
          : tone === 'info'
            ? 'color-mix(in srgb, var(--color-teal) 12%, var(--surface))'
            : 'color-mix(in srgb, var(--danger) 12%, var(--surface))',
      color:
        tone === 'warn'
          ? 'var(--color-ochre)'
          : tone === 'info'
            ? 'var(--color-teal-ink)'
            : 'var(--danger)',
    }"
  >
    <span aria-hidden="true">●</span>
    <span class="min-w-0"><slot /></span>
  </div>
</template>
