<template>
  <section>
    <h1 class="page-title">{{ title }}</h1>
    <p class="page-subtitle">{{ subtitle }}</p>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle: string
}>()
</script>
