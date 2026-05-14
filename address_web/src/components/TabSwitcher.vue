<template>
  <div class="tab-switcher" :class="{ compact }">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      class="tab-button"
      :class="{ active: modelValue === tab.value }"
      @click="$emit('update:modelValue', tab.value)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  tabs: Array<{ label: string; value: string }>
  compact?: boolean
}>()

defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()
</script>
