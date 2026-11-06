<script setup lang="ts">
defineProps<{ id: string; label: string; hint?: string; error?: string | null }>()
const model = defineModel<number | string | null>({ required: true })
</script>

<template>
  <div class="field">
    <label :for="id" class="field-label">{{ label }}</label>
    <select
      :id="id"
      v-model="model"
      class="field-input"
      :aria-invalid="error ? 'true' : undefined"
    >
      <slot />
    </select>
    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    <p v-else-if="hint" class="field-hint">{{ hint }}</p>
  </div>
</template>
