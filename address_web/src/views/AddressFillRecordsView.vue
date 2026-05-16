<template>
  <div>
    <PageHeader title="补全历史记录" subtitle="查看地址补全任务记录和下载结果 Excel" />

    <section class="card section-card">
      <div class="records-filters">
        <div class="filter-item">
          <label class="field-label" for="fill-record-keyword">任务名称</label>
          <input id="fill-record-keyword" v-model="keyword" class="input" placeholder="请输入任务名称" />
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
        <RouterLink class="secondary-button" to="/address-fill">返回地址补全</RouterLink>
      </div>

      <BaseTable :columns="columns" :rows="pagedRecords" row-key="id">
        <template #cell-status="{ row }">
          <StatusBadge :text="row.status === 'success' ? '完成' : '部分失败'" :tone="row.status === 'success' ? 'success' : 'warning'" />
        </template>
        <template #cell-actions="{ row }">
          <span class="link-group">
            <a class="action-link" :href="row.downloadUrl" target="_blank" rel="noreferrer">下载</a>
            <button type="button" class="action-link action-button danger" :disabled="deletingId === row.id" @click="handleDelete(row)">{{ deletingId === row.id ? '删除中' : '删除' }}</button>
          </span>
        </template>
      </BaseTable>

      <PaginationBar
        :total-text="`${filteredRecords.length} 条`"
        :page-size-text="`${pageSize}条/页`"
        :page-size="pageSize"
        :page-size-options="[20, 50, 100]"
        :pages="pageButtons"
        :active-page="page"
        :tail-page="totalPages"
        @change="changePage"
        @page-size-change="changePageSize"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { deleteAddressFillRecord, getAddressFillRecords } from '../api/address'
import type { AddressFillRecord } from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import type { TableColumn } from '../types'

const records = ref<AddressFillRecord[]>([])
const keyword = ref('')
const startDate = ref('')
const endDate = ref('')
const page = ref(1)
const pageSize = ref(20)
const deletingId = ref('')
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const todayValue = formatDate(new Date())
const activeDateField = ref<'start' | 'end' | ''>('')
const calendarMonth = ref(startOfMonth(new Date()))

const handleDelete = async (row: AddressFillRecord) => {
  if (!confirm(`确定删除任务「${row.taskName}」？删除后无法恢复。`)) return
  deletingId.value = row.id
  try {
    await deleteAddressFillRecord(row.id)
    records.value = records.value.filter((item) => item.id !== row.id)
  } catch {
    alert('删除失败，请稍后重试')
  } finally {
    deletingId.value = ''
  }
}

const columns: TableColumn[] = [
  { key: 'taskName', label: '任务名称', width: '260px' },
  { key: 'inputSource', label: '输入来源', width: '120px' },
  { key: 'sourceCount', label: '资料数', width: '100px' },
  { key: 'columnMode', label: '字段结构', width: '110px' },
  { key: 'total', label: '总条数', width: '110px' },
  { key: 'success', label: '已补全', width: '110px' },
  { key: 'failed', label: '资料不足', width: '110px' },
  { key: 'status', label: '状态', width: '100px' },
  { key: 'startedAt', label: '创建时间', width: '170px' },
  { key: 'actions', label: '操作', width: '140px' },
]

function formatDate(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDate(value: string) {
  if (!value) return null
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

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

const closeFloatingControls = () => {
  activeDateField.value = ''
}

const openDatePicker = (field: 'start' | 'end') => {
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
    const byKeyword = !keyword.value || item.taskName.includes(keyword.value)
    const recordDate = item.startedAt.slice(0, 10)
    const afterStart = !startDate.value || recordDate >= startDate.value
    const beforeEnd = !endDate.value || recordDate <= endDate.value
    return byKeyword && afterStart && beforeEnd
  }),
)
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRecords.value.length / pageSize.value)))
const pageButtons = computed(() => Array.from({ length: Math.min(totalPages.value, 5) }, (_, index) => index + 1))
const pagedRecords = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRecords.value.slice(start, start + pageSize.value)
})

const changePage = (nextPage: number) => {
  if (nextPage >= 1 && nextPage <= totalPages.value) {
    page.value = nextPage
  }
}

const changePageSize = (nextPageSize: number) => {
  pageSize.value = nextPageSize
  page.value = 1
}

const resetFilters = () => {
  keyword.value = ''
  startDate.value = ''
  endDate.value = ''
  closeFloatingControls()
}

watch([keyword, startDate, endDate], () => {
  page.value = 1
})

onMounted(async () => {
  window.addEventListener('click', closeFloatingControls)
  records.value = await getAddressFillRecords()
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeFloatingControls)
})
</script>

<style scoped>
.records-filters {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(340px, 1fr) auto auto;
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
}

.date-segment.filled .date-label {
  font-size: 12px;
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

.action-button {
  min-height: auto;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.action-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
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

  .filter-item:nth-child(2) {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .records-filters {
    grid-template-columns: 1fr;
    padding: 12px;
  }
}
</style>
