<script setup lang="ts">
defineProps<{
  id: string
  label: string
  type?: string
  error?: string | null
  hint?: string
  autocomplete?: string
  required?: boolean
}>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <div class="grid gap-1.5">
    <label :for="id" class="text-sm font-medium text-ink-2">{{ label }}</label>
    <input
      :id="id"
      v-model="model"
      :type="type ?? 'text'"
      :autocomplete="autocomplete"
      :required="required"
      :aria-invalid="!!error"
      :aria-describedby="error ? `${id}-error` : hint ? `${id}-hint` : undefined"
      class="rounded-md border px-3.5 py-2.5 text-sm bg-paper transition-colors
             focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      :class="error ? 'border-brand-hi' : 'border-line-strong'"
    />
    <p v-if="error" :id="`${id}-error`" class="text-xs text-brand" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="text-xs text-muted">{{ hint }}</p>
  </div>
</template>
