<template>
  <div>
    <PageHeader title="拆分记录" subtitle="查看历史拆分任务记录，可重新下载结果" />

    <section class="card section-card">
      <div class="toolbar records-filters">
        <div class="filter-item">
          <span class="field-label">任务名称</span>
          <input v-model="taskKeyword" class="input" placeholder="请输入任务名称" />
        </div>
        <div class="filter-item">
          <span class="field-label">状态</span>
          <select v-model="statusFilter" class="select">
            <option v-for="item in statusOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>
        <div class="filter-item">
          <span class="field-label">时间</span>
          <div class="date-field">
            <span>选择日期范围</span>
            <span>🗓</span>
          </div>
        </div>
        <button type="button" class="ghost-button" @click="resetFilters">重置</button>
      </div>

      <BaseTable :columns="recordColumns" :rows="pagedRecords" row-key="id">
        <template #cell-total="{ row }">{{ formatNumber(row.total) }}</template>
        <template #cell-success="{ row }">{{ formatNumber(row.success) }}</template>
        <template #cell-failed="{ row }">{{ formatNumber(row.failed) }}</template>
        <template #cell-splitScheme="{ row }">
          <span class="scheme-chip" :title="row.splitScheme || formatColumnMode(row.columnMode)">
            {{ formatSplitScheme(row) }}
          </span>
        </template>
        <template #cell-storage="{ row }">
          <span class="storage-cell" :class="row.storageBackend === 'redis' ? 'redis' : 'sqlite'">
            <strong>{{ row.storageBackend === 'redis' ? 'Redis' : 'SQLite' }}</strong>
            <small v-if="row.storageBackend === 'redis'">
              {{ row.storageHost }} / {{ row.storagePort }} / {{ row.storageDb }}
            </small>
          </span>
        </template>
        <template #cell-status="{ row }">
          <StatusBadge
            :text="row.status === 'success' ? '完成' : '部分失败'"
            :tone="row.status === 'success' ? 'success' : 'warning'"
          />
        </template>
        <template #cell-actions="{ row }">
          <span class="link-group">
            <RouterLink class="action-link" :to="`/records/${row.id}`">查看</RouterLink>
            <a class="action-link" :href="row.downloadUrl" target="_blank" rel="noreferrer">下载</a>
            <button
              type="button"
              class="action-link action-button danger"
              :disabled="deletingId === row.id"
              @click="removeRecord(row.id)"
            >
              {{ deletingId === row.id ? '删除中' : '删除' }}
            </button>
          </span>
        </template>
      </BaseTable>

      <PaginationBar
        :total-text="`${formatNumber(filteredRecords.length)} 条`"
        :page-size-text="`${pageSize}条/页`"
        :page-size="pageSize"
        :page-size-options="pageSizeOptions"
        :pages="pageButtons"
        :active-page="page"
        :tail-page="totalPages"
        @change="changePage"
        @page-size-change="changePageSize"
      />
    </section>

    <div v-if="message" class="records-toast" :class="{ success: messageType === 'success', danger: messageType === 'danger' }">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { deleteSplitRecord, getSplitRecords } from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { statusOptions } from '../mock/data'
import type { SplitRecord, TableColumn } from '../types'

const records = ref<SplitRecord[]>([])
const taskKeyword = ref('')
const statusFilter = ref('all')
const page = ref(1)
const pageSize = ref(20)
const deletingId = ref('')
const message = ref('')
const messageType = ref<'success' | 'danger'>('success')
let messageTimer: number | undefined
const pageSizeOptions = [20, 50, 100]

const recordColumns: TableColumn[] = [
  { key: 'taskName', label: '任务名称', width: '250px' },
  { key: 'source', label: '数据来源', width: '120px' },
  { key: 'splitScheme', label: '拆分方案', width: '150px' },
  { key: 'storage', label: '存储位置', width: '170px' },
  { key: 'total', label: '总条数', width: '110px' },
  { key: 'success', label: '成功条数', width: '120px' },
  { key: 'failed', label: '失败条数', width: '120px' },
  { key: 'status', label: '状态', width: '110px' },
  { key: 'startedAt', label: '开始时间', width: '180px' },
  { key: 'actions', label: '操作', width: '150px' },
]

const filteredRecords = computed(() =>
  records.value.filter((item) => {
    const byKeyword = !taskKeyword.value || item.taskName.includes(taskKeyword.value)
    const byStatus = statusFilter.value === 'all' || item.status === statusFilter.value
    return byKeyword && byStatus
  }),
)

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRecords.value.length / pageSize.value)))

const pageButtons = computed(() => {
  const visibleCount = Math.min(totalPages.value, 5)
  const half = Math.floor(visibleCount / 2)
  const start = Math.max(1, Math.min(page.value - half, totalPages.value - visibleCount + 1))
  return Array.from({ length: visibleCount }, (_, index) => start + index)
})

const pagedRecords = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRecords.value.slice(start, start + pageSize.value)
})

const resetFilters = () => {
  taskKeyword.value = ''
  statusFilter.value = 'all'
}

const loadRecords = async () => {
  records.value = await getSplitRecords()
}

const showMessage = (text: string, type: 'success' | 'danger') => {
  message.value = text
  messageType.value = type
  if (messageTimer !== undefined) {
    window.clearTimeout(messageTimer)
  }
  messageTimer = window.setTimeout(() => {
    message.value = ''
    messageTimer = undefined
  }, 4000)
}

const removeRecord = async (id: string) => {
  if (deletingId.value) {
    return
  }

  if (!window.confirm('确认删除这条拆分记录吗？删除后需要重新执行任务才能生成记录。')) {
    return
  }

  deletingId.value = id
  try {
    await deleteSplitRecord(id)
    records.value = records.value.filter((item) => item.id !== id)
    await loadRecords()
    if (page.value > totalPages.value) {
      page.value = totalPages.value
    }
    showMessage('拆分记录已删除', 'success')
  } catch (error) {
    showMessage(error instanceof Error ? error.message : '删除拆分记录失败', 'danger')
  } finally {
    deletingId.value = ''
  }
}

const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN').format(value)

const formatColumnMode = (mode?: SplitRecord['columnMode']) => {
  if (mode === 'level8') {
    return '8级标准列'
  }
  if (mode === 'level11') {
    return '11级标准列'
  }
  if (mode === 'raw') {
    return '原始字段自定义'
  }
  return '-'
}

const formatSplitScheme = (row: SplitRecord) => {
  const scheme = row.splitScheme || formatColumnMode(row.columnMode)
  if (row.columnMode === 'raw' || scheme.startsWith('原始字段自定义')) {
    const fieldCount = scheme.match(/\((.*)\)/)?.[1]?.split(',').filter(Boolean).length
    return fieldCount ? `原始字段自定义（${fieldCount}列）` : '原始字段自定义'
  }

  return scheme
}

const changePage = (nextPage: number) => {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) {
    return
  }

  page.value = nextPage
}

const changePageSize = (nextPageSize: number) => {
  if (!pageSizeOptions.includes(nextPageSize) || nextPageSize === pageSize.value) {
    return
  }

  pageSize.value = nextPageSize
  page.value = 1
}

watch([taskKeyword, statusFilter], () => {
  page.value = 1
})

onMounted(async () => {
  await loadRecords()
})
</script>

<style scoped>
.records-filters {
  align-items: flex-end;
  margin-bottom: 22px;
}

.filter-item {
  display: grid;
  gap: 8px;
}

.filter-item:nth-child(1) {
  width: 290px;
}

.filter-item:nth-child(2) {
  width: 190px;
}

.filter-item:nth-child(3) {
  width: 240px;
}

.scheme-chip {
  display: inline-block;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.storage-cell {
  display: grid;
  gap: 2px;
  line-height: 1.25;
}

.storage-cell strong {
  font-size: 14px;
}

.storage-cell small {
  color: var(--text-muted);
  font-size: 12px;
}

.storage-cell.redis strong {
  color: #0f766e;
}

.storage-cell.sqlite strong {
  color: #475569;
}

:deep(.data-table th:last-child),
:deep(.data-table td:last-child) {
  position: sticky;
  right: 0;
  z-index: 2;
  background: #fff;
  box-shadow: -10px 0 18px rgba(15, 23, 42, 0.04);
}

:deep(.data-table th:last-child) {
  z-index: 3;
  background: #f7f9fd;
}

.link-group {
  display: inline-flex;
  gap: 12px;
  align-items: center;
  white-space: nowrap;
}

.action-button {
  min-height: auto;
  padding: 0;
  border: 0;
  background: transparent;
}

.action-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.records-toast {
  position: fixed;
  right: 28px;
  top: 24px;
  z-index: 100;
  max-width: min(360px, calc(100vw - 56px));
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: #fff;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.16);
  font-weight: 700;
}

.records-toast.success {
  color: #047857;
  border-color: rgba(16, 185, 129, 0.35);
  background: #ecfdf5;
}

.records-toast.danger {
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.35);
  background: #fef2f2;
}
</style>
