<template>
  <div class="page-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <div class="app-frame">
      <AppSidebar />
      <main id="main-content" class="content-panel" tabindex="-1">
        <header class="topbar">
          <button type="button" class="user-entry" aria-label="打开管理员菜单">
            <span class="user-icon">
              <UserRound :size="17" aria-hidden="true" />
            </span>
            <span>管理员</span>
            <ChevronDown :size="16" aria-hidden="true" />
          </button>
        </header>
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { ChevronDown, UserRound } from 'lucide-vue-next'
import AppSidebar from '../components/AppSidebar.vue'
</script>
