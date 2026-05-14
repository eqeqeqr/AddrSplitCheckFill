<template>
  <div>
    <RouterLink to="/records" class="back-link">← 返回</RouterLink>

    <section class="stats-grid">
      <article v-for="item in statCards" :key="item.label" class="card stat-card">
        <div class="stat-card-label">{{ item.label }}</div>
        <div class="stat-card-value">{{ item.value }}</div>
      </article>
    </section>

    <section class="card section-card">
      <div class="toolbar detail-tabs">
        <TabSwitcher v-model="activeTab" :tabs="detailTabs" compact />
      </div>

      <div class="schema-panel">
        <label>
          <span class="field-label">拆分结果列方案</span>
          <select v-model="columnMode" class="select">
            <option v-for="item in columnModes" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </label>

        <p class="schema-note">{{ schemaNotice }}</p>
      </div>

      <div class="toolbar detail-filters">
        <div class="filter-item">
          <span class="field-label">地域</span>
          <select v-model="regionFilter" class="select">
            <option v-for="item in regionOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>
        <div class="filter-item">
          <span class="field-label">省份</span>
          <select v-model="provinceFilter" class="select">
            <option v-for="item in provinceOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>
        <div class="filter-item detail-search">
          <span class="field-label">&nbsp;</span>
          <input v-model="keyword" class="input" placeholder="搜索原始地址" />
        </div>
        <button type="button" class="ghost-button" @click="resetFilters">重置</button>
      </div>

      <div class="toolbar detail-actions">
        <div class="toolbar-spacer" />
        <a class="secondary-button" :href="downloadUrl" target="_blank" rel="noreferrer">⇩ 导出结果</a>
        <button type="button" class="ghost-button" @click="showColumnModal = true">⚙ 列显示</button>
      </div>

      <BaseTable :columns="tableColumns" :rows="filteredRows" row-key="id">
        <template #cell-result="{ row }">
          <StatusBadge
            :text="row.result"
            :tone="row.result === '识别完成' ? 'default' : 'warning'"
          />
        </template>
      </BaseTable>

      <PaginationBar
        :total-text="`${formatNumber(totalRows)} 条`"
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

    <ColumnSettingsModal
      v-if="showColumnModal"
      v-model="columnSettings"
      v-model:mode="columnMode"
      :modes="columnModes"
      @close="showColumnModal = false"
      @confirm="saveColumns"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { buildDownloadUrl, getColumnSettings, getSplitResultDetail, updateVisibleColumns } from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import ColumnSettingsModal from '../components/ColumnSettingsModal.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import TabSwitcher from '../components/TabSwitcher.vue'
import {
  columnModes,
  columnsByMode,
  detailTabs,
  provinceOptions,
  regionOptions,
} from '../mock/data'
import type { ColumnMode, ColumnSettingItem, DetailStats, SplitResultRow, TableColumn } from '../types'

const route = useRoute()

const activeTab = ref('preview')
const showColumnModal = ref(false)
const regionFilter = ref('all')
const provinceFilter = ref('all')
const keyword = ref('')
const columnMode = ref<ColumnMode>('level8')
const stats = ref<DetailStats>({
  total: '0',
  success: '0',
  failed: '0',
  successRate: '0%',
})
const rows = ref<SplitResultRow[]>([])
const failedRows = ref<SplitResultRow[]>([])
const columnSettings = ref<ColumnSettingItem[]>([])
const resultColumns = ref<string[]>([])
const downloadUrl = ref('')
const page = ref(1)
const pageSize = ref(20)
const pageSizeOptions = [20, 50, 100]
const totalRows = ref(0)

const statCards = computed(() => [
  { label: '总条数', value: stats.value.total },
  { label: '拆分成功', value: stats.value.success },
  { label: '拆分失败', value: stats.value.failed },
  { label: '成功率', value: stats.value.successRate },
])

const totalPages = computed(() => Math.max(1, Math.ceil(totalRows.value / pageSize.value)))

const pageButtons = computed(() => {
  const visibleCount = Math.min(totalPages.value, 5)
  const half = Math.floor(visibleCount / 2)
  const start = Math.max(1, Math.min(page.value - half, totalPages.value - visibleCount + 1))
  return Array.from({ length: visibleCount }, (_, index) => start + index)
})

const tableColumns = computed<TableColumn[]>(() => {
  if (resultColumns.value.length > 0) {
    return resultColumns.value
      .map((key) => {
        const known = columnsByMode[columnMode.value].find((column) => column.key === key)
        return known ?? {
          key,
          label: key,
          width: ['address', '地址', 'new_address'].includes(key) ? '280px' : undefined,
          className: ['address', '地址', 'new_address'].includes(key) ? 'address-cell' : undefined,
        }
      })
      .filter((column) => {
        if (columnMode.value !== 'raw') {
          return true
        }

        const setting = columnSettings.value.find((item) => item.key === column.key)
        return setting ? setting.visible : true
      })
  }

  return columnsByMode[columnMode.value].filter((column) =>
    columnSettings.value.find((item) => item.key === column.key)?.visible,
  )
})

const schemaNotice = computed(() => {
  if (columnMode.value === 'raw') {
    return '原始字段自定义按 PDF 字段展示；原始字段不参与校验。'
  }

  return '固定标准列由接口返回；校验规则按 level_1 到 level_11 的层级配置执行。'
})

const activeRows = computed(() => (activeTab.value === 'preview' ? rows.value : failedRows.value))

const filteredRows = computed(() =>
  activeRows.value.filter((item) => {
    const byRegion = regionFilter.value === 'all' || item.region === regionFilter.value
    const byProvince = provinceFilter.value === 'all' || item.province === provinceFilter.value
    const byKeyword = !keyword.value || item.rawAddress.includes(keyword.value)
    return byRegion && byProvince && byKeyword
  }),
)

const resetFilters = () => {
  regionFilter.value = 'all'
  provinceFilter.value = 'all'
  keyword.value = ''
}

const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN').format(value)

const saveColumns = async () => {
  const result = await updateVisibleColumns({
    mode: columnMode.value,
    columns: columnSettings.value,
  })
  columnSettings.value = result.columns
  showColumnModal.value = false
}

const syncColumnMode = async (mode: ColumnMode) => {
  columnSettings.value = await getColumnSettings(mode)
}

watch(columnMode, syncColumnMode)

const loadDetail = async () => {
  const detail = await getSplitResultDetail(String(route.params.id), {
    page: page.value,
    pageSize: pageSize.value,
  })
  stats.value = detail.stats
  rows.value = detail.rows.map((row, index) => ({
    id: `${route.params.id}-${page.value}-${index}`,
    rawAddress: String(row.address ?? row['地址'] ?? row.rawAddress ?? ''),
    province: String(row.new_level_1 ?? row.level_1 ?? row.new_prov ?? row.prov ?? ''),
    city: String(row.new_level_2 ?? row.level_2 ?? row.new_city ?? row.city ?? ''),
    district: String(row.new_level_3 ?? row.level_3 ?? row.new_district ?? row.district ?? ''),
    street: String(row.new_level_4 ?? row.level_4 ?? row.new_town ?? row.town ?? ''),
    road: String(row.new_level_5 ?? row.level_5 ?? row.new_road ?? row.road ?? ''),
    roadNo: String(row.new_level_6 ?? row.level_6 ?? row.new_roadno ?? row.roadno ?? ''),
    building: String(row.new_level_7 ?? row.level_7 ?? row.new_poi ?? row.poi ?? ''),
    roomNo: String(row.new_level_8 ?? row.level_8 ?? row.new_houseno ?? row.houseno ?? ''),
    result: '识别完成',
    ...Object.fromEntries(Object.entries(row).map(([key, value]) => [key, String(value ?? '')])),
  }))
  failedRows.value = detail.failedRows.map((row, index) => ({
    id: `failed-${route.params.id}-${index}`,
    rawAddress: String(row.address ?? row['地址'] ?? row.rawAddress ?? ''),
    province: String(row.new_level_1 ?? row.level_1 ?? row.new_prov ?? row.prov ?? ''),
    city: String(row.new_level_2 ?? row.level_2 ?? row.new_city ?? row.city ?? ''),
    district: String(row.new_level_3 ?? row.level_3 ?? row.new_district ?? row.district ?? ''),
    street: String(row.new_level_4 ?? row.level_4 ?? row.new_town ?? row.town ?? ''),
    road: String(row.new_level_5 ?? row.level_5 ?? row.new_road ?? row.road ?? ''),
    roadNo: String(row.new_level_6 ?? row.level_6 ?? row.new_roadno ?? row.roadno ?? ''),
    building: String(row.new_level_7 ?? row.level_7 ?? row.new_poi ?? row.poi ?? ''),
    roomNo: String(row.new_level_8 ?? row.level_8 ?? row.new_houseno ?? row.houseno ?? ''),
    result: '待人工确认',
    ...Object.fromEntries(Object.entries(row).map(([key, value]) => [key, String(value ?? '')])),
  }))
  columnMode.value = route.query.columns === 'raw' ? 'raw' : route.query.columns === 'level11' ? 'level11' : detail.columnMode
  resultColumns.value = detail.columns
  downloadUrl.value = buildDownloadUrl(detail.downloadUrl)
  page.value = detail.page
  pageSize.value = detail.pageSize
  totalRows.value = detail.totalRows || detail.rows.length
  columnSettings.value = await getColumnSettings(columnMode.value)
}

const changePage = async (nextPage: number) => {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) {
    return
  }

  page.value = nextPage
  await loadDetail()
}

const changePageSize = async (nextPageSize: number) => {
  if (!pageSizeOptions.includes(nextPageSize) || nextPageSize === pageSize.value) {
    return
  }

  pageSize.value = nextPageSize
  page.value = 1
  await loadDetail()
}

onMounted(async () => {
  await loadDetail()
  activeTab.value = route.query.tab === 'failed' ? 'failed' : 'preview'
  showColumnModal.value = route.query.modal === 'columns'
})
</script>

<style scoped>
.detail-tabs {
  margin-bottom: 24px;
}

.schema-panel {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  gap: 16px;
  align-items: end;
  margin-bottom: 22px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #f8fbff;
}

.schema-panel label {
  display: grid;
  gap: 8px;
}

.schema-note {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.detail-filters {
  align-items: flex-end;
  margin-bottom: 18px;
}

.filter-item {
  display: grid;
  gap: 8px;
  width: 180px;
}

.detail-search {
  width: 360px;
}

.detail-actions {
  margin-bottom: 16px;
}
</style>
