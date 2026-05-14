<template>
  <span class="status-pill" :class="toneClass">
    {{ text }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  tone?: 'default' | 'success' | 'warning' | 'danger'
}>()

const toneClass = computed(() => props.tone ?? 'default')
</script>
