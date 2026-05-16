<template>
  <div class="page-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <div class="app-frame">
      <AppSidebar />
      <main id="main-content" class="content-panel" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppSidebar from '../components/AppSidebar.vue'
</script>
