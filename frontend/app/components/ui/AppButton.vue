<script setup lang="ts">
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
    :class="[
      'inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold',
      'transition-colors disabled:opacity-55 disabled:cursor-not-allowed',
      shape === 'pill' ? 'rounded-full' : 'rounded-md',
      block && 'w-full',
      variant === 'primary' && 'bg-brand text-white hover:bg-brand-hi',
      variant === 'ghost' && 'border border-line-strong text-ink hover:bg-wash-2',
      variant === 'danger' && 'bg-brand-hi text-white hover:bg-brand',
    ]"
  >
    <span
      v-if="loading"
      class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
    <slot />
  </button>
</template>
