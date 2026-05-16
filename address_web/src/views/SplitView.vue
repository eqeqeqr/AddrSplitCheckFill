<template>
  <div>
    <PageHeader
      title="地址拆分"
      subtitle="支持上传Excel文件或手动输入地址，拆分为明细地址信息及结果录别"
    />

    <section class="card section-card split-hero">
      <TabSwitcher v-model="activeTab" :tabs="splitTabs" compact />

      <div class="schema-panel">
        <label>
          <span class="field-label">拆分结果列方案</span>
          <select v-model="columnMode" class="select">
            <option v-for="item in columnModes" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </label>

        <p class="schema-note">
          {{ schemaNotice }}
        </p>
      </div>

      <div v-if="activeTab === 'upload'" class="upload-grid">
        <div class="card upload-panel">
          <input
            id="address-file"
            ref="fileInputRef"
            type="file"
            name="address-file"
            accept=".xlsx,.xls"
            class="file-input"
            @change="handleFileChange"
          />
          <label
            for="address-file"
            class="upload-dropzone"
            @dragover.prevent
            @drop.prevent="handleFileDrop"
          >
            <div class="excel-badge" aria-hidden="true">
              <FileSpreadsheet :size="34" :stroke-width="2.3" />
            </div>
            <h3>点击或拖拽 Excel 文件到此处上传</h3>
            <p>支持 .xlsx、.xls 格式，默认处理前 100 条，可在开始前调整数量</p>
          </label>

          <div v-if="selectedFile" class="file-card">
            <div class="file-meta">
              <span class="file-check" aria-hidden="true">
                <Check :size="14" :stroke-width="3" />
              </span>
              <span>{{ selectedFile.name }}</span>
            </div>
            <span class="muted">{{ selectedFileSize }}</span>
            <button type="button" class="ghost-icon" aria-label="移除已选择文件" @click="clearSelectedFile">
              <Trash2 :size="18" aria-hidden="true" />
            </button>
          </div>

          <p v-if="selectedFile" class="empty-note">
            {{ excelInspectText }}
          </p>
          <p class="empty-note">建议文件中包含一列地址数据，表头名称为：address/地址</p>
          <p v-if="errorMessage" class="error-note">{{ errorMessage }}</p>

          <button type="button" class="primary-button" :disabled="isProcessing || isInspectingExcel" @click="openSplitConfirm">
            <Play :size="17" aria-hidden="true" />
            {{ isProcessing ? '拆分中…' : '开始拆分' }}
          </button>
          <button v-if="isProcessing" type="button" class="danger-button split-stop-button" :disabled="isCancelling" @click="cancelCurrentSplit">
            <PauseCircle :size="17" aria-hidden="true" />
            {{ isCancelling ? '正在结束…' : '结束拆分并保留结果' }}
          </button>
        </div>

        <div class="card progress-panel">
          <h3>拆分进度</h3>
          <div class="progress-ring" :style="{ '--percent': String(progress.percent) }">
            <div class="progress-ring-inner">
              <strong>{{ progress.percent }}%</strong>
            </div>
          </div>
          <p class="progress-main">{{ progress.summary.processed }}</p>
          <p class="progress-sub">{{ progress.summary.elapsed }}</p>

          <div class="progress-steps">
            <div v-for="step in progress.steps" :key="step.key" class="progress-step">
              <div class="step-left">
                <span class="step-dot" :class="step.status" />
                <span>{{ step.label }}</span>
              </div>
              <span
                class="step-status"
                :class="step.status === 'doing' ? 'is-doing' : step.status === 'done' ? 'is-done' : step.status === 'interrupted' ? 'is-interrupted' : ''"
              >
                {{ step.text }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="manual-grid">
        <div class="manual-panel">
          <label class="field-label" for="manual-addresses">请输入地址（每行一个地址）</label>
          <textarea
            id="manual-addresses"
            v-model="manualInput"
            class="textarea"
            name="manual-addresses"
            placeholder="请输入待拆分地址…"
          />
          <div class="manual-foot">
            <span class="muted">已输入 {{ manualCount }} 行</span>
            <span class="muted">{{ manualCount }} 行地址</span>
          </div>
          <div class="manual-actions">
            <button type="button" class="ghost-button" @click="manualInput = ''">清空</button>
            <button type="button" class="primary-button" :disabled="isProcessing" @click="openSplitConfirm">
              <Play :size="17" aria-hidden="true" />
              {{ isProcessing ? '拆分中…' : '开始拆分' }}
            </button>
            <button v-if="isProcessing" type="button" class="danger-button" :disabled="isCancelling" @click="cancelCurrentSplit">
              <PauseCircle :size="17" aria-hidden="true" />
              {{ isCancelling ? '正在结束…' : '结束拆分' }}
            </button>
          </div>
          <p v-if="errorMessage" class="error-note">{{ errorMessage }}</p>
        </div>

        <div class="card progress-panel">
          <h3>拆分进度</h3>
          <div class="progress-ring" :style="{ '--percent': String(progress.percent) }">
            <div class="progress-ring-inner">
              <strong>{{ progress.percent }}%</strong>
            </div>
          </div>
          <p class="progress-main">{{ progress.summary.processed }}</p>
          <p class="progress-sub">{{ progress.summary.elapsed }}</p>

          <div class="progress-steps">
            <div v-for="step in progress.steps" :key="step.key" class="progress-step">
              <div class="step-left">
                <span class="step-dot" :class="step.status" />
                <span>{{ step.label }}</span>
              </div>
              <span
                class="step-status"
                :class="step.status === 'doing' ? 'is-doing' : step.status === 'done' ? 'is-done' : step.status === 'interrupted' ? 'is-interrupted' : ''"
              >
                {{ step.text }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="result-section">
      <div class="section-heading">
        <h2>拆分结果</h2>
        <span>显示前 20 行</span>
      </div>

      <div class="toolbar result-toolbar">
        <div class="toolbar-spacer" />
        <a
          class="secondary-button"
          :class="{ disabled: !downloadUrl }"
          :href="downloadUrl || undefined"
          target="_blank"
          rel="noreferrer"
        >
          <Download :size="17" aria-hidden="true" />
          导出 Excel
        </a>
        <button type="button" class="ghost-button" @click="showColumnModal = true">
          <SlidersHorizontal :size="17" aria-hidden="true" />
          设置列显示
        </button>
      </div>

      <p v-if="jobSummary" class="job-summary">{{ jobSummary }}</p>

      <BaseTable :columns="visibleColumns" :rows="previewRows" row-key="id">
        <template #cell-result="{ row }">
          <StatusBadge :text="row.result" />
        </template>
      </BaseTable>
    </section>

    <div v-if="showSplitConfirm" class="modal-mask" @click.self="showSplitConfirm = false">
      <div class="modal-card split-count-modal">
        <div class="modal-body">
          <div class="modal-header">
            <div>
              <h3>确认拆分条数</h3>
              <p>默认处理 100 条，可输入 1 到 {{ splitMaxRows.toLocaleString() }} 之间的数量。</p>
            </div>
            <button type="button" class="close-button" aria-label="关闭确认弹窗" @click="showSplitConfirm = false">
              <X :size="18" aria-hidden="true" />
            </button>
          </div>

          <label class="split-count-field">
            <span class="field-label">本次处理条数</span>
            <input
              v-model="splitCountInput"
              class="input"
              inputmode="numeric"
              name="split-count"
              placeholder="100…"
              type="number"
              min="1"
              :max="splitMaxRows"
            />
            <small>Excel 上传最多可处理该文件地址总量；手动输入最多可处理当前输入行数。</small>
          </label>

          <p v-if="splitCountError" class="error-note">{{ splitCountError }}</p>

          <div class="modal-footer">
            <button type="button" class="ghost-button" @click="showSplitConfirm = false">取消</button>
            <button type="button" class="primary-button" @click="confirmSplitCount">确定并开始</button>
          </div>
        </div>
      </div>
    </div>

    <ColumnSettingsModal
      v-if="showColumnModal"
      v-model="columnSettings"
      v-model:mode="columnMode"
      :modes="columnModes"
      @close="showColumnModal = false"
      @confirm="confirmColumns"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  Check,
  Download,
  FileSpreadsheet,
  PauseCircle,
  Play,
  SlidersHorizontal,
  Trash2,
  X,
} from 'lucide-vue-next'
import {
  buildDownloadUrl,
  cancelSplitJob,
  connectSplitProgress,
  createSplitJobId,
  getColumnSettings,
  getManualInputSeed,
  getSplitPreview,
  getSplitResultDetail,
  inspectExcelFile,
  submitManualAddress,
  uploadAddressFile,
  updateVisibleColumns,
} from '../api/address'
import type { SplitJobResponse, SplitProgressEvent } from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import ColumnSettingsModal from '../components/ColumnSettingsModal.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import TabSwitcher from '../components/TabSwitcher.vue'
import {
  columnModes,
  columnsByMode,
  settingsByMode,
  splitTabs,
} from '../mock/data'
import type { ColumnMode, ColumnSettingItem, ProgressStep, SplitResultRow, TableColumn } from '../types'

const route = useRoute()
const activeTab = ref('upload')
const showColumnModal = ref(false)
const manualInput = ref('')
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isProcessing = ref(false)
const isCancelling = ref(false)
const isInspectingExcel = ref(false)
const errorMessage = ref('')
const downloadUrl = ref('')
const resultColumns = ref<string[]>([])
const jobSummary = ref('')
const previewRows = ref<SplitResultRow[]>([])
const excelAddressRows = ref(0)
const excelAddressColumn = ref('')
const showSplitConfirm = ref(false)
const splitMaxRows = ref(100)
const splitCountInput = ref('100')
const splitCountError = ref('')
const columnMode = ref<ColumnMode>('level8')
const columnSettings = ref<ColumnSettingItem[]>(structuredClone(settingsByMode.level8))
const currentJobId = ref('')
const createIdleProgress = () => ({
  percent: 0,
  summary: {
    processed: '当前未开始拆分',
    elapsed: '上传文件或输入地址后，点击开始拆分',
  },
  steps: [
    { key: 'parse', label: '文件解析', status: 'waiting', text: '未开始' },
    { key: 'split', label: '地址识别与拆分', status: 'waiting', text: '未开始' },
    { key: 'summary', label: '结果汇总', status: 'waiting', text: '未开始' },
    { key: 'done', label: '完成', status: 'waiting', text: '未开始' },
  ] as ProgressStep[],
})

const progress = ref(createIdleProgress())
const SPLIT_STATE_KEY = 'address-split-current-state'
let progressTimer: number | undefined
let progressSocket: WebSocket | undefined
let progressStartedAt = 0
let progressTargetRows = 0
let isRestoringSplitState = false

const manualCount = computed(() =>
  manualInput.value.split('\n').map((item) => item.trim()).filter(Boolean).length,
)

const selectedFileSize = computed(() => {
  if (!selectedFile.value) {
    return ''
  }

  const mb = selectedFile.value.size / 1024 / 1024
  if (mb < 1) {
    return `${(selectedFile.value.size / 1024).toFixed(0)} KB`
  }

  return `${mb.toFixed(2)} MB`
})

const excelInspectText = computed(() => {
  if (isInspectingExcel.value) {
    return '正在检测 Excel 地址总量…'
  }

  if (excelAddressRows.value > 0) {
    return `检测到 ${excelAddressColumn.value || 'address/地址'} 地址总量：${excelAddressRows.value.toLocaleString()} 条，开始前可选择处理条数。`
  }

  return '尚未检测到地址总量，请确认文件包含 address/地址 字段。'
})

const visibleColumns = computed<TableColumn[]>(() =>
  getColumnsForDisplay().filter((column) => {
    if (columnMode.value !== 'raw') {
      return true
    }

    const setting = columnSettings.value.find((item) => item.key === column.key)
    if (!setting) {
      return true
    }

    return setting.visible
  }),
)

const schemaNotice = computed(() => {
  if (columnMode.value === 'raw') {
    return '原始字段自定义可按 PDF 字段任意勾选；原始字段不参与校验。'
  }

  return '8级和11级走固定接口列；校验规则按 level_1 到 level_11 的层级配置执行。'
})

const toTableColumn = (key: string): TableColumn => {
  const localColumn = columnsByMode[columnMode.value].find((column) => column.key === key)
  if (localColumn) {
    return localColumn
  }

  return {
    key,
    label: key,
    className: ['address', '地址', 'new_address'].includes(key) ? 'address-cell' : undefined,
    width: ['address', '地址', 'new_address'].includes(key) ? '280px' : undefined,
  }
}

const getColumnsForDisplay = () => {
  if (resultColumns.value.length > 0) {
    return resultColumns.value.map(toTableColumn)
  }

  return columnsByMode[columnMode.value]
}

const mapPreviewRows = (response: SplitJobResponse): SplitResultRow[] =>
  response.preview.map((row, index) => ({
    id: `${response.job_id}-${index}`,
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

const selectedRawFields = () =>
  columnSettings.value
    .filter((item) => item.visible)
    .map((item) => item.key)
    .filter((key) => key.startsWith('new_') && !['new_address', 'new_validation_status', 'new_violated_rule_ids'].includes(key))
    .map((key) => key.replace(/^new_/, ''))

const formatDuration = (totalSeconds: number) => {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return [hours, minutes, seconds].map((item) => String(item).padStart(2, '0')).join(':')
}

const setProgress = (
  processed: number,
  total: number,
  elapsedSeconds?: number,
  phase: 'parsing' | 'splitting' | 'summary' | 'done' | 'cancelled' | 'error' = 'splitting',
  message = '',
) => {
  const safeTotal = Math.max(total, 1)
  const safeProcessed = Math.min(Math.max(processed, 0), safeTotal)
  const splitDone = safeProcessed >= safeTotal
  const parsing = phase === 'parsing'
  const summaryDoing = phase === 'summary'
  const done = phase === 'done'
  const cancelled = phase === 'cancelled'
  const failed = phase === 'error'
  progress.value = {
    percent: Math.round((safeProcessed / safeTotal) * 100),
    summary: {
      processed: cancelled
        ? `已中断，保留 ${safeProcessed.toLocaleString()} / ${safeTotal.toLocaleString()} 条`
        : failed
        ? '拆分失败'
        : parsing
          ? '正在解析 Excel 文件'
          : `已处理 ${safeProcessed.toLocaleString()} / ${safeTotal.toLocaleString()} 条`,
      elapsed: cancelled
        ? (message || `耗时 ${formatDuration(elapsedSeconds ?? Math.floor((Date.now() - progressStartedAt) / 1000))}`)
        : failed
        ? (message || '请检查文件或稍后重试')
        : message || `耗时 ${formatDuration(elapsedSeconds ?? Math.floor((Date.now() - progressStartedAt) / 1000))}`,
    },
    steps: [
      { key: 'parse', label: '文件解析', status: parsing ? 'doing' : failed ? 'waiting' : 'done', text: parsing ? '处理中' : failed ? '未完成' : '已完成' },
      { key: 'split', label: '地址识别与拆分', status: cancelled ? 'interrupted' : failed ? 'waiting' : parsing ? 'waiting' : splitDone ? 'done' : 'doing', text: cancelled ? '拆分中断' : failed ? '未完成' : parsing ? '等待中' : splitDone ? '已完成' : '处理中' },
      { key: 'summary', label: '结果汇总', status: done || cancelled ? 'done' : summaryDoing ? 'doing' : 'waiting', text: done || cancelled ? '已完成' : summaryDoing ? '汇总中' : '等待中' },
      { key: 'done', label: '完成', status: done || cancelled ? 'done' : 'waiting', text: done ? '已完成' : cancelled ? '已保留结果' : '等待中' },
    ],
  }
  persistSplitState()
}

const persistSplitState = () => {
  const payload = {
    activeTab: activeTab.value,
    columnMode: columnMode.value,
    progress: progress.value,
    jobSummary: jobSummary.value,
    downloadUrl: downloadUrl.value,
    resultColumns: resultColumns.value,
    previewRows: previewRows.value,
    currentJobId: currentJobId.value,
    isProcessing: isProcessing.value,
    progressTargetRows,
    savedAt: Date.now(),
  }
  sessionStorage.setItem(SPLIT_STATE_KEY, JSON.stringify(payload))
}

const restoreSplitState = () => {
  const raw = sessionStorage.getItem(SPLIT_STATE_KEY)
  if (!raw) {
    return
  }

  try {
    const payload = JSON.parse(raw)
    const hasRealResult =
      Boolean(payload.downloadUrl) ||
      Boolean(payload.jobSummary) ||
      (Array.isArray(payload.previewRows) && payload.previewRows.length > 0)
    const isOldMockProgress =
      payload.progress?.percent === 68 &&
      payload.progress?.summary?.processed === '6,800 / 10,000 条'
    if (isOldMockProgress && !hasRealResult) {
      sessionStorage.removeItem(SPLIT_STATE_KEY)
      return
    }
    activeTab.value = payload.activeTab ?? activeTab.value
    columnMode.value = payload.columnMode ?? columnMode.value
    progress.value = payload.progress ?? createIdleProgress()
    jobSummary.value = payload.jobSummary ?? ''
    downloadUrl.value = payload.downloadUrl ?? ''
    resultColumns.value = Array.isArray(payload.resultColumns) ? payload.resultColumns : []
    previewRows.value = Array.isArray(payload.previewRows) ? payload.previewRows : previewRows.value
    currentJobId.value = payload.currentJobId ?? ''
    progressTargetRows = Number(payload.progressTargetRows) || progressTargetRows
    isProcessing.value = Boolean(payload.isProcessing && currentJobId.value && !payload.downloadUrl)
  } catch {
    sessionStorage.removeItem(SPLIT_STATE_KEY)
  }
}

const stopProgressTimer = () => {
  if (progressTimer !== undefined) {
    window.clearInterval(progressTimer)
    progressTimer = undefined
  }
  if (progressSocket !== undefined) {
    progressSocket.close()
    progressSocket = undefined
  }
}

const startProgressSocket = (jobId: string, targetRows: number) => {
  stopProgressTimer()
  progressTargetRows = Math.max(targetRows, 1)
  progressStartedAt = Date.now()
  setProgress(0, progressTargetRows, 0, 'parsing')
  progressSocket = connectSplitProgress(jobId, {
    onMessage: applyProgressEvent,
    onError: () => {
      if (isProcessing.value) {
        setProgress(0, progressTargetRows, undefined, 'parsing', '进度通道连接异常，等待接口返回结果')
      }
    },
  })
}

const reconnectProgressSocket = (jobId: string) => {
  if (!jobId) {
    return
  }
  if (progressSocket !== undefined) {
    progressSocket.close()
  }
  progressSocket = connectSplitProgress(jobId, {
    onMessage: applyProgressEvent,
    onError: () => {
      if (isProcessing.value) {
        progress.value.summary.elapsed = '进度通道连接异常，正在等待后端任务状态'
      }
    },
  })
}

const applyProgressEvent = (event: SplitProgressEvent) => {
  const total = event.total_rows || progressTargetRows || 1
  setProgress(
    event.processed_rows,
    total,
    event.elapsed_seconds,
    event.phase,
    event.phase === 'error' ? event.message : '',
  )
  if (event.phase === 'done' || event.phase === 'cancelled') {
    void loadCompletedJob(event.cached_job_id || event.job_id, event.phase)
  }
}

const loadCompletedJob = async (jobId: string, finalPhase: 'done' | 'cancelled' = 'done') => {
  try {
    const detail = await getSplitResultDetail(jobId, { page: 1, pageSize: 20 })
    const response: SplitJobResponse = {
      job_id: jobId,
      status: finalPhase === 'cancelled' ? 'cancelled' : 'completed',
      column_mode: detail.columnMode,
      total_rows: Number(detail.stats.total.replace(/,/g, '')) || detail.totalRows,
      processed_rows: detail.totalRows,
      columns: detail.columns,
      preview: detail.rows,
      download_url: detail.downloadUrl,
    }
    applySplitResult(response)
  } catch {
    // The long HTTP request may still apply the final result; keep progress visible.
  }
}

const applySplitResult = (response: SplitJobResponse) => {
  stopProgressTimer()
  const elapsed = Math.floor((Date.now() - progressStartedAt) / 1000)
  previewRows.value = mapPreviewRows(response)
  resultColumns.value = response.columns
  downloadUrl.value = buildDownloadUrl(response.download_url)
  jobSummary.value = `共 ${response.total_rows.toLocaleString()} 条，当前处理 ${response.processed_rows.toLocaleString()} 条，结果列方案：${response.column_mode}`
  setProgress(
    response.processed_rows,
    Math.max(response.processed_rows, progressTargetRows, 1),
    elapsed,
    response.status === 'cancelled' ? 'cancelled' : 'done',
    response.status === 'cancelled' ? '已结束拆分，已保留当前结果' : '',
  )
  currentJobId.value = ''
  isProcessing.value = false
  isCancelling.value = false
  persistSplitState()
}

const cancelCurrentSplit = async () => {
  if (!currentJobId.value) {
    return
  }
  isCancelling.value = true
  progress.value.summary.elapsed = '正在结束拆分，后端会保留已完成结果'
  persistSplitState()
  try {
    await cancelSplitJob(currentJobId.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '结束拆分失败'
    isCancelling.value = false
  }
}

const openSplitConfirm = async () => {
  errorMessage.value = ''
  splitCountError.value = ''

  if (activeTab.value === 'manual') {
    if (manualCount.value === 0) {
      errorMessage.value = '请先输入地址'
      return
    }
    splitMaxRows.value = manualCount.value
  } else {
    if (!selectedFile.value) {
      errorMessage.value = '请先选择 Excel 文件'
      return
    }
    if (isInspectingExcel.value) {
      errorMessage.value = '正在检测 Excel 地址总量，请稍后再开始'
      return
    }
    if (excelAddressRows.value <= 0) {
      await inspectSelectedFile(selectedFile.value)
    }
    if (excelAddressRows.value <= 0) {
      errorMessage.value = '未检测到可处理的 address/地址 地址数据'
      return
    }
    splitMaxRows.value = excelAddressRows.value
  }

  splitCountInput.value = String(Math.min(100, splitMaxRows.value))
  showSplitConfirm.value = true
}

const confirmSplitCount = () => {
  const value = Number(splitCountInput.value)
  if (!Number.isInteger(value)) {
    splitCountError.value = '请输入整数条数'
    return
  }
  if (value < 1) {
    splitCountError.value = '处理条数不能小于 1'
    return
  }
  if (value > splitMaxRows.value) {
    splitCountError.value = `处理条数不能大于最大数量 ${splitMaxRows.value.toLocaleString()}`
    return
  }

  showSplitConfirm.value = false
  void startSplit(value)
}

const startSplit = async (sampleSize: number) => {
  errorMessage.value = ''
  isProcessing.value = true
  const clientJobId = createSplitJobId()
  currentJobId.value = clientJobId
  startProgressSocket(clientJobId, sampleSize)

  try {
    if (activeTab.value === 'manual') {
      const response = await submitManualAddress({
        content: manualInput.value,
        columnMode: columnMode.value,
        rawFields: selectedRawFields(),
        sampleSize,
        clientJobId,
      })
      applySplitResult(response)
      return
    }

    if (!selectedFile.value) {
      throw new Error('请先选择 Excel 文件')
    }

    const response = await uploadAddressFile(selectedFile.value, {
      columnMode: columnMode.value,
      sampleSize,
      rawFields: selectedRawFields(),
      clientJobId,
    })
    applySplitResult(response)
  } catch (error) {
    stopProgressTimer()
    errorMessage.value = error instanceof Error ? error.message : '拆分失败，请稍后重试'
  } finally {
    if (!downloadUrl.value) {
      isProcessing.value = false
    }
  }
}

const inspectSelectedFile = async (file: File) => {
  isInspectingExcel.value = true
  excelAddressRows.value = 0
  try {
    const result = await inspectExcelFile(file)
    if (selectedFile.value === file) {
      excelAddressRows.value = result.address_rows || result.total_rows
      excelAddressColumn.value = result.address_column
    }
  } catch (error) {
    if (selectedFile.value === file) {
      errorMessage.value = error instanceof Error ? error.message : 'Excel 地址总量检测失败'
    }
  } finally {
    if (selectedFile.value === file) {
      isInspectingExcel.value = false
    }
  }
}

const setSelectedFile = (file: File | null) => {
  selectedFile.value = file
  excelAddressRows.value = 0
  excelAddressColumn.value = ''
  errorMessage.value = ''
  if (file) {
    void inspectSelectedFile(file)
  }
}

const clearSelectedFile = () => {
  setSelectedFile(null)
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  setSelectedFile(input.files?.[0] ?? null)
}

const handleFileDrop = (event: DragEvent) => {
  setSelectedFile(event.dataTransfer?.files?.[0] ?? null)
}

const confirmColumns = async () => {
  const result = await updateVisibleColumns({
    mode: columnMode.value,
    columns: columnSettings.value,
  })
  columnSettings.value = result.columns
  showColumnModal.value = false
}

const syncColumnMode = async (mode: ColumnMode) => {
  columnSettings.value = await getColumnSettings(mode)
  if (!isRestoringSplitState) {
    resultColumns.value = []
    downloadUrl.value = ''
    jobSummary.value = ''
    persistSplitState()
  }
}

watch(columnMode, syncColumnMode)

onMounted(async () => {
  const [seed, rows] = await Promise.all([
    getManualInputSeed(),
    getSplitPreview(),
  ])

  manualInput.value = seed
  previewRows.value = rows.slice(0, 3)
  progress.value = createIdleProgress()
  isRestoringSplitState = true
  activeTab.value = route.query.tab === 'manual' ? 'manual' : 'upload'
  columnMode.value = route.query.columns === 'raw' ? 'raw' : route.query.columns === 'level11' ? 'level11' : 'level8'
  showColumnModal.value = route.query.modal === 'columns'
  restoreSplitState()
  if (isProcessing.value && currentJobId.value) {
    reconnectProgressSocket(currentJobId.value)
  }
  window.setTimeout(() => {
    isRestoringSplitState = false
  }, 0)
})

onBeforeUnmount(stopProgressTimer)
</script>

<style scoped>
.split-hero {
  padding-top: 16px;
}

.schema-panel {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  gap: 16px;
  align-items: end;
  margin-top: 22px;
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

.upload-grid,
.manual-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: 22px;
  padding-top: 22px;
}

.upload-panel,
.progress-panel,
.manual-panel {
  padding: 24px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: #fff;
}

.upload-dropzone {
  min-height: 252px;
  border: 1px dashed #c4dbff;
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfdff 0%, #f6faff 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
}

.file-input {
  display: none;
}

.excel-badge {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
  color: #fff;
  font-size: 34px;
  font-weight: 800;
  display: grid;
  place-items: center;
}

.upload-dropzone h3 {
  margin: 18px 0 8px;
  font-size: 22px;
}

.upload-dropzone p {
  margin: 0;
  color: var(--text-sub);
}

.file-card {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 16px;
  align-items: center;
  margin-top: 18px;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
}

.file-check {
  width: 22px;
  height: 22px;
  display: inline-grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.14);
  color: var(--success);
}

.ghost-icon {
  color: #475569;
  cursor: pointer;
}

.error-note {
  margin: 12px 0 0;
  color: var(--danger);
  font-size: 14px;
  font-weight: 600;
}

.progress-panel h3 {
  margin: 0 0 18px;
  font-size: 18px;
}

.progress-ring {
  width: 148px;
  height: 148px;
  margin: 10px auto 16px;
  border-radius: 50%;
  background: conic-gradient(var(--primary) calc(var(--percent) * 1%), #d9e8ff 0);
  display: grid;
  place-items: center;
  --percent: 68;
}

.progress-ring-inner {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
}

.progress-ring-inner strong {
  color: var(--primary);
  font-size: 28px;
}

.progress-main,
.progress-sub {
  margin: 0;
  text-align: center;
}

.progress-main {
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
}

.progress-sub {
  color: var(--text-sub);
  margin-top: 8px;
}

.progress-steps {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid #edf2f7;
}

.progress-step,
.step-left {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.progress-step + .progress-step {
  margin-top: 14px;
}

.step-left {
  justify-content: flex-start;
}

.step-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
}

.step-dot.done {
  background: var(--success);
  border-color: var(--success);
}

.step-dot.doing {
  border-color: var(--primary);
  box-shadow: inset 0 0 0 4px rgba(31, 120, 255, 0.8);
  animation: progress-pulse 0.9s linear infinite;
}

.step-dot.interrupted {
  background: #f59e0b;
  border-color: #f59e0b;
}

.step-status {
  color: var(--text-muted);
  font-weight: 600;
}

.step-status.is-doing {
  color: var(--primary);
}

.step-status.is-done {
  color: var(--success);
}

.step-status.is-interrupted {
  color: #d97706;
}

@keyframes progress-pulse {
  0% {
    transform: scale(0.88);
    box-shadow: inset 0 0 0 4px rgba(31, 120, 255, 0.75), 0 0 0 0 rgba(31, 120, 255, 0.25);
  }

  100% {
    transform: scale(1);
    box-shadow: inset 0 0 0 4px rgba(31, 120, 255, 0.75), 0 0 0 8px rgba(31, 120, 255, 0);
  }
}

.manual-panel {
  margin-top: 22px;
}

.manual-grid .manual-panel {
  margin-top: 0;
}

.manual-foot,
.manual-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.manual-foot {
  margin-top: 12px;
  padding-bottom: 18px;
  border-bottom: 1px solid #edf2f7;
}

.manual-actions {
  margin-top: 18px;
}

.result-section {
  margin-top: 30px;
}

.result-toolbar {
  justify-content: flex-end;
  margin-bottom: 16px;
}

.job-summary {
  margin: -6px 0 14px;
  color: #64748b;
  font-size: 14px;
}

.secondary-button.disabled {
  pointer-events: none;
  color: #94a3b8;
  border-color: var(--border);
  background: #f8fafc;
}

.danger-button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  color: #b91c1c;
  border: 1px solid #fecaca;
  background: #fff5f5;
  font-weight: 700;
  cursor: pointer;
}

.danger-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.split-stop-button {
  margin-left: 12px;
}

.split-count-modal {
  width: min(100%, 460px);
}

.split-count-field {
  display: grid;
  gap: 8px;
  margin-top: 22px;
}

.split-count-field small {
  color: var(--text-muted);
  font-size: 13px;
}

.split-hero {
  position: relative;
  overflow: hidden;
  border-color: rgba(37, 99, 235, 0.12);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(246, 250, 253, 0.82)),
    linear-gradient(110deg, rgba(37, 99, 235, 0.08), rgba(20, 184, 166, 0.08));
}

.split-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(37, 99, 235, 0.08) 1px, transparent 1px),
    linear-gradient(180deg, rgba(37, 99, 235, 0.06) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.36), transparent 72%);
}

.split-hero > * {
  position: relative;
}

.schema-panel {
  border-color: rgba(37, 99, 235, 0.14);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.upload-panel,
.manual-panel,
.progress-panel {
  position: relative;
  overflow: hidden;
  border-color: rgba(37, 99, 235, 0.13);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 20px 52px rgba(36, 52, 78, 0.08);
}

.upload-panel::after,
.progress-panel::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 3px;
  background: linear-gradient(90deg, #2563eb, #0f766e, #d97706);
  opacity: 0.82;
}

.upload-dropzone {
  position: relative;
  border-color: rgba(37, 99, 235, 0.3);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(246, 250, 253, 0.92)),
    repeating-linear-gradient(135deg, rgba(37, 99, 235, 0.06) 0 1px, transparent 1px 12px);
  transition: transform 0.24s var(--ease-out), border-color 0.24s ease, box-shadow 0.24s ease, background-color 0.24s ease;
}

.upload-dropzone:hover {
  transform: translateY(-3px);
  border-color: rgba(37, 99, 235, 0.55);
  box-shadow: 0 22px 54px rgba(37, 99, 235, 0.14);
}

.excel-badge {
  background: linear-gradient(135deg, #10b981, #2563eb);
  box-shadow: 0 18px 38px rgba(16, 185, 129, 0.24);
  animation: badge-float 3.8s var(--ease-out) infinite;
}

.upload-dropzone h3 {
  color: var(--ink);
  letter-spacing: 0;
  text-wrap: balance;
}

.file-card {
  border-color: rgba(16, 185, 129, 0.2);
  background: linear-gradient(135deg, rgba(236, 253, 245, 0.78), rgba(255, 255, 255, 0.9));
}

.file-meta {
  min-width: 0;
}

.file-meta span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ghost-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: inline-grid;
  place-items: center;
  color: #64748b;
  transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.ghost-icon:hover {
  color: var(--danger);
  background: #fff1f2;
  transform: translateY(-1px);
}

.progress-panel h3 {
  color: var(--ink);
  font-size: 20px;
}

.progress-ring {
  background:
    conic-gradient(#2563eb calc(var(--percent) * 1%), rgba(201, 213, 227, 0.72) 0),
    linear-gradient(135deg, #2563eb, #0f766e);
  box-shadow: 0 22px 46px rgba(37, 99, 235, 0.14);
  transition: background 0.3s ease;
}

.progress-ring-inner {
  box-shadow: inset 0 0 0 1px rgba(221, 230, 240, 0.9);
}

.progress-ring-inner strong {
  color: var(--primary);
  font-variant-numeric: tabular-nums;
}

.progress-step {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.74);
}

.step-dot.doing {
  animation: progress-pulse 1.1s var(--ease-out) infinite;
}

.manual-panel {
  display: flex;
  flex-direction: column;
}

.manual-panel .textarea {
  margin-top: 8px;
  min-height: 280px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(249, 251, 253, 0.94)),
    linear-gradient(90deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px);
  background-size: auto, 40px 100%;
}

.manual-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.result-section {
  animation: content-rise 0.38s var(--ease-out) both;
}

.job-summary {
  padding: 10px 12px;
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 12px;
  background: rgba(233, 241, 255, 0.6);
}

@keyframes badge-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

@keyframes content-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1180px) {
  .upload-grid,
  .manual-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .schema-panel {
    grid-template-columns: 1fr;
  }

  .upload-panel,
  .manual-panel,
  .progress-panel {
    padding: 18px;
  }

  .upload-dropzone {
    min-height: 220px;
  }

  .manual-foot,
  .manual-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .split-stop-button {
    margin-left: 0;
    margin-top: 10px;
  }
}
</style>
