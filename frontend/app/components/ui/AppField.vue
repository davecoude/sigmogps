<script setup lang="ts">
defineProps<{
  id: string
  label: string
  type?: string
  error?: string | null
  hint?: string
  placeholder?: string
  autocomplete?: string
  required?: boolean
}>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <div class="field">
    <label :for="id" class="field-label">
      {{ label }}
      <span v-if="required" class="text-[var(--danger)]" aria-hidden="true">*</span>
    </label>
    <input
      :id="id"
      v-model="model"
      :type="type ?? 'text'"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? `${id}-error` : hint ? `${id}-hint` : undefined"
      class="field-input"
    />
    <p v-if="error" :id="`${id}-error`" class="field-error" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="field-hint">{{ hint }}</p>
  </div>
</template>
