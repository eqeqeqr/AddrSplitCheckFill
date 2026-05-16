<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="brand-mark" />
      <span>地址拆分工具</span>
    </div>

    <nav class="nav-list">
      <component
        :is="item.path ? 'RouterLink' : 'div'"
        v-for="item in navigationItems"
        :key="item.label"
        :to="item.path"
        class="nav-item"
        :class="{ active: item.path && route.path.startsWith(item.path), mutedItem: !item.path }"
        :aria-current="item.path && route.path.startsWith(item.path) ? 'page' : undefined"
      >
        <span class="nav-icon" aria-hidden="true">
          <component :is="navIconMap[item.icon] ?? Circle" :size="20" :stroke-width="2.2" />
        </span>
        <span>{{ item.label }}</span>
      </component>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import type { Component } from 'vue'
import { Circle, ClipboardList, FileSearch, MapPinned, Settings2, ShieldCheck } from 'lucide-vue-next'
import { navigationItems } from '../mock/data'

const route = useRoute()
const navIconMap: Record<string, Component> = {
  home: MapPinned,
  fill: FileSearch,
  validation: ShieldCheck,
  record: ClipboardList,
  config: Settings2,
}
</script>

<style scoped>
.sidebar {
  width: 236px;
  padding: 26px 18px;
  border-right: 1px solid var(--border);
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #101828;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 30px;
}

.brand-mark {
  width: 26px;
  height: 26px;
  background: linear-gradient(135deg, #2563eb 0%, #14b8a6 100%);
  border-radius: 50% 50% 50% 10%;
  position: relative;
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
}

.brand-mark::after {
  content: "";
  position: absolute;
  left: 8px;
  top: 8px;
  width: 10px;
  height: 10px;
  background: #fff;
  border-radius: 50%;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 56px;
  padding: 0 18px;
  border-radius: 12px;
  color: #1f2937;
  font-size: 16px;
  font-weight: 600;
  position: relative;
  transition: color 0.2s ease, background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.nav-item.active {
  color: #0f5bd7;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(20, 184, 166, 0.12));
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}

.nav-item:hover {
  color: #0f5bd7;
  background: rgba(37, 99, 235, 0.07);
  transform: translateX(2px);
}

.nav-item.mutedItem {
  cursor: default;
}

.nav-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.22);
  display: grid;
  place-items: center;
  flex: none;
}

@media (max-width: 1100px) {
  .sidebar {
    width: 100%;
    padding: 18px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .brand {
    margin-bottom: 16px;
  }

  .nav-list {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .nav-item {
    justify-content: center;
    min-height: 50px;
    padding: 0 10px;
    font-size: 14px;
  }

  .nav-item:hover {
    transform: translateY(-1px);
  }
}

@media (max-width: 640px) {
  .nav-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .nav-item {
    justify-content: flex-start;
  }
}
</style>
