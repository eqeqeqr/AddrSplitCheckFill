<template>
  <div class="pagination">
    <div class="toolbar">
      <span class="field-label">共 {{ totalText }}</span>
      <select
        class="select"
        style="width: 120px"
        :value="pageSize"
        :disabled="!pageSizeOptions?.length"
        @change="handlePageSizeChange"
      >
        <option v-if="!pageSizeOptions?.length">{{ pageSizeText }}</option>
        <option v-for="size in pageSizeOptions" v-else :key="size" :value="size">{{ size }}条/页</option>
      </select>
    </div>

    <div class="pagination-controls">
      <button type="button" class="page-arrow" :disabled="activePage <= 1" @click="$emit('change', activePage - 1)">
        〈
      </button>
      <button
        v-for="page in pages"
        :key="page"
        type="button"
        class="page-chip"
        :class="{ active: page === activePage }"
        @click="$emit('change', page)"
      >
        {{ page }}
      </button>
      <span v-if="showTailPage" class="muted">…</span>
      <button v-if="showTailPage" type="button" class="page-chip" @click="$emit('change', tailPage)">
        {{ tailPage }}
      </button>
      <button type="button" class="page-arrow" :disabled="activePage >= tailPage" @click="$emit('change', activePage + 1)">
        〉
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  totalText: string
  pageSizeText: string
  pages: number[]
  activePage: number
  tailPage: number
  pageSize?: number
  pageSizeOptions?: number[]
}>()

const emit = defineEmits<{
  (event: 'change', page: number): void
  (event: 'pageSizeChange', pageSize: number): void
}>()

const showTailPage = computed(() => props.tailPage > 1 && !props.pages.includes(props.tailPage))

const handlePageSizeChange = (event: Event) => {
  const value = Number((event.target as HTMLSelectElement).value)
  if (Number.isFinite(value) && value !== props.pageSize) {
    emit('pageSizeChange', value)
  }
}
</script>
