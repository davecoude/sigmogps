<script setup lang="ts">
/** Lee la superficie del contenedor: no sabe si está en claro u oscuro. */
withDefaults(
  defineProps<{
    variant?: 'primary' | 'ghost' | 'danger'
    shape?: 'pill' | 'square'
    loading?: boolean
    disabled?: boolean
    type?: 'button' | 'submit'
    block?: boolean
  }>(),
  { variant: 'primary', shape: 'square', type: 'button' },
)
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    class="btn"
    :class="[`btn-${variant}`, shape === 'pill' && 'btn-pill', block && 'w-full']"
  >
    <span
      v-if="loading"
      class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
    <slot />
  </button>
</template>
