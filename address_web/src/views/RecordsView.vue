<template>
  <div>
    <PageHeader title="拆分记录" subtitle="查看历史拆分任务记录，可重新下载结果" />

    <section class="card section-card">
      <div class="toolbar records-filters">
        <div class="filter-item">
          <label class="field-label" for="record-task-keyword">任务名称</label>
          <input id="record-task-keyword" v-model="taskKeyword" class="input" placeholder="请输入任务名称" />
        </div>
        <div class="filter-item">
          <label class="field-label" for="record-storage-filter">存储位置</label>
          <div class="custom-select" @click.stop>
            <button
              id="record-storage-filter"
              type="button"
              class="custom-select-trigger"
              :class="{ open: openSelect === 'storage' }"
              aria-haspopup="listbox"
              :aria-expanded="openSelect === 'storage'"
              @click="toggleSelect('storage')"
            >
              <span>{{ storageFilterLabel }}</span>
              <ChevronDown :size="17" aria-hidden="true" />
            </button>
            <div v-if="openSelect === 'storage'" class="custom-select-menu" role="listbox">
              <button
                v-for="item in storageOptions"
                :key="item.value"
                type="button"
                class="custom-select-option"
                :class="{ active: storageFilter === item.value }"
                role="option"
                :aria-selected="storageFilter === item.value"
                @click="selectStorage(item.value)"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
        </div>
        <div class="filter-item">
          <label class="field-label" for="record-status-filter">状态</label>
          <div class="custom-select" @click.stop>
            <button
              id="record-status-filter"
              type="button"
              class="custom-select-trigger"
              :class="{ open: openSelect === 'status' }"
              aria-haspopup="listbox"
              :aria-expanded="openSelect === 'status'"
              @click="toggleSelect('status')"
            >
              <span>{{ statusFilterLabel }}</span>
              <ChevronDown :size="17" aria-hidden="true" />
            </button>
            <div v-if="openSelect === 'status'" class="custom-select-menu" role="listbox">
              <button
                v-for="item in statusOptions"
                :key="item.value"
                type="button"
                class="custom-select-option"
                :class="{ active: statusFilter === item.value }"
                role="option"
                :aria-selected="statusFilter === item.value"
                @click="selectStatus(item.value)"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
        </div>
        <div class="filter-item">
          <span class="field-label">时间</span>
          <div class="date-range-field">
            <button type="button" class="date-segment" :class="{ filled: startDate, open: activeDateField === 'start' }" @click.stop="openDatePicker('start')">
              <span class="date-label">开始</span>
              <span v-if="startDate" class="date-value">{{ startDate }}</span>
              <CalendarDays class="date-icon" :size="15" aria-hidden="true" />
            </button>
            <span class="date-divider">至</span>
            <button type="button" class="date-segment" :class="{ filled: endDate, open: activeDateField === 'end' }" @click.stop="openDatePicker('end')">
              <span class="date-label">结束</span>
              <span v-if="endDate" class="date-value">{{ endDate }}</span>
              <CalendarDays class="date-icon" :size="15" aria-hidden="true" />
            </button>
          </div>
          <div v-if="activeDateField" class="date-picker-popover" @click.stop>
            <div class="date-picker-header">
              <button type="button" class="date-picker-icon-button" aria-label="上个月" @click="shiftCalendarMonth(-1)">
                <ChevronLeft :size="17" aria-hidden="true" />
              </button>
              <strong>{{ calendarTitle }}</strong>
              <button type="button" class="date-picker-icon-button" aria-label="下个月" @click="shiftCalendarMonth(1)">
                <ChevronRight :size="17" aria-hidden="true" />
              </button>
            </div>
            <div class="date-picker-weekdays">
              <span v-for="day in weekdays" :key="day">{{ day }}</span>
            </div>
            <div class="date-picker-grid">
              <button
                v-for="day in calendarDays"
                :key="day.value"
                type="button"
                class="date-picker-day"
                :class="{ muted: !day.inMonth, selected: day.value === activeDateValue, today: day.value === todayValue }"
                @click="selectCalendarDate(day.value)"
              >
                {{ day.label }}
              </button>
            </div>
            <div class="date-picker-actions">
              <button type="button" @click="clearActiveDate">清除</button>
              <button type="button" @click="selectCalendarDate(todayValue)">今天</button>
            </div>
          </div>
        </div>
        <button type="button" class="ghost-button records-reset-button" @click="resetFilters">重置</button>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { deleteSplitRecord, getSplitRecords } from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { statusOptions } from '../mock/data'
import type { SplitRecord, TableColumn } from '../types'

const records = ref<SplitRecord[]>([])
const taskKeyword = ref('')
const storageFilter = ref('all')
const statusFilter = ref('all')
const startDate = ref('')
const endDate = ref('')
const page = ref(1)
const pageSize = ref(20)
const deletingId = ref('')
const message = ref('')
const messageType = ref<'success' | 'danger'>('success')
let messageTimer: number | undefined
const pageSizeOptions = [20, 50, 100]
const storageOptions = [
  { label: '全部', value: 'all' },
  { label: 'Redis', value: 'redis' },
  { label: 'SQLite', value: 'sqlite' },
]
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const todayValue = formatDate(new Date())
const openSelect = ref<'storage' | 'status' | ''>('')
const activeDateField = ref<'start' | 'end' | ''>('')
const calendarMonth = ref(startOfMonth(new Date()))

const storageFilterLabel = computed(() => storageOptions.find((item) => item.value === storageFilter.value)?.label ?? '全部')
const statusFilterLabel = computed(() => statusOptions.find((item) => item.value === statusFilter.value)?.label ?? '全部')
const activeDateValue = computed(() => (activeDateField.value === 'start' ? startDate.value : activeDateField.value === 'end' ? endDate.value : ''))
const calendarTitle = computed(() => `${calendarMonth.value.getFullYear()}年${String(calendarMonth.value.getMonth() + 1).padStart(2, '0')}月`)
const calendarDays = computed(() => {
  const monthStart = calendarMonth.value
  const firstDay = new Date(monthStart)
  firstDay.setDate(1 - firstDay.getDay())
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(firstDay)
    date.setDate(firstDay.getDate() + index)
    return {
      label: String(date.getDate()),
      value: formatDate(date),
      inMonth: date.getMonth() === monthStart.getMonth(),
    }
  })
})

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

function formatDate(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDate(value: string) {
  if (!value) {
    return null
  }

  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

const closeFloatingControls = () => {
  openSelect.value = ''
  activeDateField.value = ''
}

const toggleSelect = (type: 'storage' | 'status') => {
  activeDateField.value = ''
  openSelect.value = openSelect.value === type ? '' : type
}

const selectStorage = (value: string) => {
  storageFilter.value = value
  openSelect.value = ''
}

const selectStatus = (value: string) => {
  statusFilter.value = value
  openSelect.value = ''
}

const openDatePicker = (field: 'start' | 'end') => {
  openSelect.value = ''
  activeDateField.value = activeDateField.value === field ? '' : field
  const selected = parseDate(field === 'start' ? startDate.value : endDate.value)
  calendarMonth.value = startOfMonth(selected ?? new Date())
}

const shiftCalendarMonth = (offset: number) => {
  calendarMonth.value = new Date(calendarMonth.value.getFullYear(), calendarMonth.value.getMonth() + offset, 1)
}

const selectCalendarDate = (value: string) => {
  if (activeDateField.value === 'start') {
    startDate.value = value
  } else if (activeDateField.value === 'end') {
    endDate.value = value
  }
  activeDateField.value = ''
}

const clearActiveDate = () => {
  if (activeDateField.value === 'start') {
    startDate.value = ''
  } else if (activeDateField.value === 'end') {
    endDate.value = ''
  }
  activeDateField.value = ''
}

const filteredRecords = computed(() =>
  records.value.filter((item) => {
    const byKeyword = !taskKeyword.value || item.taskName.includes(taskKeyword.value)
    const byStorage = storageFilter.value === 'all' || item.storageBackend === storageFilter.value
    const byStatus = statusFilter.value === 'all' || item.status === statusFilter.value
    const recordDate = item.startedAt.slice(0, 10)
    const afterStart = !startDate.value || recordDate >= startDate.value
    const beforeEnd = !endDate.value || recordDate <= endDate.value
    return byKeyword && byStorage && byStatus && afterStart && beforeEnd
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
  storageFilter.value = 'all'
  statusFilter.value = 'all'
  startDate.value = ''
  endDate.value = ''
  closeFloatingControls()
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

watch([taskKeyword, storageFilter, statusFilter, startDate, endDate], () => {
  page.value = 1
})

onMounted(async () => {
  window.addEventListener('click', closeFloatingControls)
  await loadRecords()
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeFloatingControls)
})
</script>

<style scoped>
.records-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.25fr) minmax(130px, 0.65fr) minmax(140px, 0.72fr) minmax(280px, 1.25fr) auto;
  align-items: end;
  gap: 14px;
  margin-bottom: 22px;
  padding: 14px;
  border: 1px solid rgba(221, 230, 240, 0.88);
  border-radius: 14px;
  background: rgba(246, 249, 253, 0.72);
}

.filter-item {
  position: relative;
  display: grid;
  gap: 6px;
  min-width: 0;
}

.filter-item .field-label {
  color: #334155;
  font-size: 13px;
  line-height: 1.2;
}

.filter-item :deep(.input),
.custom-select-trigger,
.records-reset-button {
  height: 42px;
}

.filter-item :deep(.input) {
  border-color: rgba(201, 213, 227, 0.82);
  border-radius: 10px;
  background: rgba(241, 245, 249, 0.82);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.42);
}

.filter-item :deep(.input::placeholder) {
  color: #94a3b8;
}

.filter-item :deep(.input:focus) {
  background: #fff;
}

.custom-select {
  position: relative;
}

.custom-select-trigger {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 14px;
  border: 1px solid rgba(201, 213, 227, 0.82);
  border-radius: 12px;
  background: rgba(241, 245, 249, 0.82);
  color: var(--text-main);
  font-weight: 650;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.42);
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.custom-select-trigger svg {
  color: #334155;
  transition: transform 0.2s ease, color 0.2s ease;
}

.custom-select-trigger.open {
  border-color: rgba(37, 99, 235, 0.48);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
}

.custom-select-trigger.open svg {
  color: #2563eb;
  transform: rotate(180deg);
}

.custom-select-menu {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 8px);
  z-index: 30;
  display: grid;
  gap: 4px;
  padding: 6px;
  border: 1px solid rgba(201, 213, 227, 0.9);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.14);
  animation: popover-in 0.16s ease both;
}

.custom-select-option {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  color: #334155;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.custom-select-option:hover,
.custom-select-option.active {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.78);
}

.date-range-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 5px;
  border: 1px solid rgba(147, 197, 253, 0.48);
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.96);
}

.date-segment {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border-radius: 9px;
  background: rgba(241, 245, 249, 0.82);
  color: #64748b;
  cursor: pointer;
  transition: background-color 0.22s ease, box-shadow 0.22s ease, padding 0.22s ease;
}

.date-segment.filled {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  justify-content: stretch;
  gap: 8px;
  padding: 0 9px;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(147, 197, 253, 0.28);
}

.date-label {
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  pointer-events: none;
  transform: translateX(0);
  transition: color 0.22s ease, font-size 0.22s ease, transform 0.22s ease;
}

.date-segment.filled .date-label {
  color: #64748b;
  font-size: 12px;
  transform: translateX(-1px);
}

.date-value {
  min-width: 0;
  color: var(--text-main);
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  pointer-events: none;
  animation: date-value-in 0.22s ease both;
}

.date-icon {
  flex: 0 0 auto;
  color: #1d4ed8;
  pointer-events: none;
  transform: translateX(0);
  transition: color 0.22s ease, transform 0.22s ease;
}

.date-segment.filled .date-icon {
  color: #2563eb;
  transform: translateX(1px);
}

.date-divider {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.9);
  font-size: 12px;
  font-weight: 850;
}

.date-segment.open {
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.36), 0 0 0 3px rgba(37, 99, 235, 0.11);
}

.records-reset-button {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 10px;
  color: #475569;
  border-color: rgba(201, 213, 227, 0.82);
  background: rgba(241, 245, 249, 0.82);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.42);
}

.date-picker-popover {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 35;
  width: min(330px, 100%);
  padding: 14px;
  border: 1px solid rgba(201, 213, 227, 0.9);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 22px 56px rgba(15, 23, 42, 0.16);
  animation: popover-in 0.16s ease both;
}

.date-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.date-picker-header strong {
  color: var(--ink);
  font-size: 14px;
}

.date-picker-icon-button {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 10px;
  color: #475569;
  background: rgba(241, 245, 249, 0.88);
  cursor: pointer;
}

.date-picker-icon-button:hover {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.85);
}

.date-picker-weekdays,
.date-picker-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.date-picker-weekdays {
  margin-bottom: 6px;
}

.date-picker-weekdays span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  text-align: center;
}

.date-picker-grid {
  gap: 4px;
}

.date-picker-day {
  display: inline-grid;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.date-picker-day:hover {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.7);
}

.date-picker-day.muted {
  color: #94a3b8;
}

.date-picker-day.today {
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.3);
}

.date-picker-day.selected {
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #0f766e);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.26);
}

.date-picker-actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-top: 12px;
}

.date-picker-actions button {
  min-height: 32px;
  padding: 0 10px;
  border-radius: 10px;
  color: #1d4ed8;
  font-weight: 800;
  cursor: pointer;
}

.date-picker-actions button:hover {
  background: rgba(219, 234, 254, 0.76);
}

@keyframes date-value-in {
  from {
    opacity: 0;
    transform: translateY(3px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes popover-in {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 1180px) {
  .records-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-item:nth-child(4),
  .records-reset-button {
    grid-column: 1 / -1;
    width: 100%;
  }
}

@media (max-width: 640px) {
  .records-filters {
    grid-template-columns: 1fr;
    padding: 12px;
  }
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
