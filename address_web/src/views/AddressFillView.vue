<template>
  <div>
    <PageHeader title="地址补全" subtitle="基于拆分结果和资料来源补全 1-7 级地址层级" />

    <section class="card section-card fill-grid">
      <div class="fill-panel">
        <div class="panel-title">
          <h3>所需补充地址</h3>
          <button type="button" class="secondary-button" @click="openSplitPicker">
            <FileSearch :size="17" aria-hidden="true" />
            选择拆分结果
          </button>
        </div>

        <input
          ref="inputFileRef"
          type="file"
          accept=".xlsx,.xls"
          class="file-input"
          @change="handleInputFileChange"
        />
        <button type="button" class="upload-line" @click="inputFileRef?.click()">
          <FileSpreadsheet :size="28" aria-hidden="true" />
          <span>{{ inputLabel }}</span>
        </button>
        <p class="empty-note">{{ inspectText }}</p>
      </div>

    </section>

    <div class="fill-actions">
      <p v-if="errorMessage" class="error-note">{{ errorMessage }}</p>
      <button type="button" class="primary-button" :disabled="isSubmitting || !canSubmit" @click="submitFill">
        <Play :size="17" aria-hidden="true" />
        {{ isSubmitting ? '补全中…' : '启动地址补全' }}
      </button>
      <button v-if="isSubmitting" type="button" class="danger-button" :disabled="isCancelling" @click="cancelFill">
        <PauseCircle :size="17" aria-hidden="true" />
        {{ isCancelling ? '正在结束…' : '结束补全并保留结果' }}
      </button>
      <RouterLink class="ghost-button" to="/address-fill/records">补全历史记录</RouterLink>
    </div>

    <section v-if="isSubmitting || progress.percent > 0" class="card section-card progress-section">
      <div class="stream-header">
        <div>
          <h3>AI 补全对话流</h3>
          <p>{{ progress.summary.processed }} · {{ progress.summary.elapsed }}</p>
        </div>
        <div class="stream-percent">{{ progress.percent }}%</div>
      </div>

      <div v-if="agentRows.length > streamPageSize" class="stream-controls">
        <span>显示 {{ streamPageStart }}-{{ streamPageEnd }} / {{ agentRows.length }} 条</span>
        <button type="button" class="ghost-button locate-button" :disabled="!currentAgentRow" @click="locateCurrentAddress">
          <Target :size="16" aria-hidden="true" />
          定位当前处理地址
        </button>
        <div class="stream-pager">
          <button type="button" class="icon-button" :disabled="streamPage <= 1" aria-label="上一页" @click="changeStreamPage(streamPage - 1)">
            <ChevronLeft :size="16" aria-hidden="true" />
          </button>
          <button
            v-for="pageNo in streamPageButtons"
            :key="pageNo"
            type="button"
            class="stream-page-button"
            :class="{ active: pageNo === streamPage }"
            @click="changeStreamPage(pageNo)"
          >
            {{ pageNo }}
          </button>
          <button type="button" class="icon-button" :disabled="streamPage >= streamTotalPages" aria-label="下一页" @click="changeStreamPage(streamPage + 1)">
            <ChevronRight :size="16" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div ref="streamListRef" class="agent-stream" aria-live="polite">
        <div v-if="!agentRows.length" class="stream-empty">
          系统提示词和上传资料将在任务启动后加载。每条地址会生成一个折叠卡片，完成后实时刷新结果预览。
        </div>
        <article v-for="row in pagedAgentRows" :key="row.rowId" class="address-log-card">
          <button type="button" class="address-log-summary" @click="toggleAddressLog(row.rowId)">
            <div>
              <div class="address-log-title">
                <span class="row-pill">地址 {{ row.rowId }}</span>
                <strong>{{ row.address || '等待读取地址' }}</strong>
              </div>
              <p>{{ row.summary }}</p>
            </div>
            <span class="address-log-status" :class="row.status">{{ row.statusText }}</span>
          </button>
          <div v-if="expandedRows.includes(row.rowId)" class="address-log-detail">
            <div v-if="!row.entries.length" class="process-empty">还没有收到这条地址的补全过程。</div>
            <div v-else class="fill-steps">
              <div
                v-for="step in getFillSteps(row)"
                :key="step.key"
                class="fill-step"
                :class="step.status"
              >
                <span class="fill-step-index">{{ step.index }}</span>
                <div class="fill-step-body">
                  <div class="fill-step-head">
                    <strong>{{ step.label }}</strong>
                    <span class="fill-step-tag" :class="step.status">{{ step.statusText }}</span>
                  </div>
                  <p v-if="step.content" class="fill-step-content">{{ step.content }}</p>

                  <!-- Loading spinner for step 3 -->
                  <div v-if="step.loading" class="fill-step-loading">
                    <span class="spinner" />
                    <span>模型正在思考…</span>
                  </div>

                  <!-- Sub-steps for step 3 -->
                  <div v-if="step.subSteps.length" class="fill-substeps">
                    <div
                      v-for="sub in step.subSteps"
                      :key="sub.seq"
                      class="fill-substep"
                      :class="[`sub-${sub.subType}`, { expanded: expandedSubSteps.includes(`${row.rowId}-${sub.seq}`) }]"
                    >
                      <span class="fill-substep-seq">{{ step.index }}.{{ sub.seq }}</span>
                      <div class="fill-substep-body">
                        <button type="button" class="fill-substep-toggle" @click="toggleSubStep(`${row.rowId}-${sub.seq}`)">
                          <div class="fill-substep-head">
                            <strong>{{ sub.title }}</strong>
                            <small>{{ sub.time }}</small>
                          </div>
                          <p v-if="sub.content && !expandedSubSteps.includes(`${row.rowId}-${sub.seq}`)" class="fill-substep-preview">{{ subStepSummary(sub.content) }}</p>
                          <ChevronDown v-if="!expandedSubSteps.includes(`${row.rowId}-${sub.seq}`)" :size="14" class="fill-substep-chevron" />
                          <ChevronUp v-else :size="14" class="fill-substep-chevron" />
                        </button>
                        <div v-if="expandedSubSteps.includes(`${row.rowId}-${sub.seq}`)" class="fill-substep-detail">
                          <p v-if="sub.content" class="fill-substep-content">{{ sub.content }}</p>
                          <div v-if="sub.links.length" class="visited-links">
                            <a
                              v-for="link in sub.links"
                              :key="link.url"
                              :href="link.url"
                              target="_blank"
                              rel="noreferrer"
                            >
                              {{ link.title || link.url }}
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div v-if="step.status === 'doing'" class="fill-step-loading">
                      <span class="spinner" />
                      <span>模型正在思考…</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="result-section">
      <div class="section-heading">
        <h2>结果 Excel 预览</h2>
        <span>{{ resultTotal }} 条</span>
      </div>
      <div class="toolbar result-toolbar">
        <div class="toolbar-spacer" />
        <a class="secondary-button" :class="{ disabled: !downloadUrl }" :href="downloadUrl || undefined" target="_blank" rel="noreferrer">
          <Download :size="17" aria-hidden="true" />
          下载 Excel
        </a>
      </div>
      <BaseTable :columns="tableColumns" :rows="resultRows" />
      <PaginationBar
        :total-text="`${resultTotal} 条`"
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

    <div v-if="showSplitPicker" class="modal-mask" @click.self="showSplitPicker = false">
      <div class="modal-card split-picker">
        <div class="modal-body">
          <div class="modal-header">
            <div>
              <h3>选择拆分结果</h3>
              <p>只展示已完成且结果文件可用的拆分记录。</p>
            </div>
            <button type="button" class="close-button" aria-label="关闭弹窗" @click="showSplitPicker = false">
              <X :size="18" aria-hidden="true" />
            </button>
          </div>
          <BaseTable :columns="splitColumns" :rows="splitResults" row-key="id">
            <template #cell-actions="{ row }">
              <button type="button" class="action-link action-button" @click="selectSplitResult(row)">选择</button>
            </template>
          </BaseTable>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Download, FileSearch, FileSpreadsheet, PauseCircle, Play, Target, X } from 'lucide-vue-next'
import {
  buildDownloadUrl,
  cancelAddressFillJob,
  connectFillProgress,
  createAddressFillJob,
  createSplitJobId,
  getAddressFillEvents,
  getAddressFillResultDetail,
  getAddressFillRowStates,
  getAddressFillSplitResults,
  inspectAddressFillInput,
} from '../api/address'
import type { AddressFillRowState, AddressFillSplitResult, FillProgressEvent } from '../api/address'
import BaseTable from '../components/BaseTable.vue'
import PageHeader from '../components/PageHeader.vue'
import PaginationBar from '../components/PaginationBar.vue'
import type { TableColumn } from '../types'

interface ProgressStep {
  key: string
  label: string
  status: 'waiting' | 'doing' | 'done' | 'interrupted'
  text: string
}

interface ProgressState {
  percent: number
  summary: {
    processed: string
    elapsed: string
  }
  steps: ProgressStep[]
}

interface AgentStreamEntry {
  id: string
  stage: string
  rowId: string
  title: string
  content: string
  detail: string
  links: Array<{ title: string; url: string; snippet?: string }>
  time: string
}

interface AgentRowLog {
  rowId: string
  address: string
  status: 'waiting' | 'running' | 'done' | 'interrupted'
  statusText: string
  summary: string
  entries: AgentStreamEntry[]
  step1Status: 'waiting' | 'doing' | 'done'
  step2Status: 'waiting' | 'doing' | 'done'
  step3Status: 'waiting' | 'doing' | 'done'
  step4Status: 'waiting' | 'doing' | 'done'
}

const FILL_STATE_KEY = 'address-fill-state'
const CLIENT_ID_KEY = 'address-fill-client-id'
const clientId = ref('')
const inputFile = ref<File | null>(null)
const selectedSplit = ref<AddressFillSplitResult | null>(null)
const sourceFiles = ref<File[]>([])
const inspectMessage = ref('请选择已拆分完成的 Excel，或直接上传同结构 Excel。')
const inputColumnMode = ref('')
const isSubmitting = ref(false)
const isCancelling = ref(false)
const errorMessage = ref('')
const latestJobId = ref('')
const downloadUrl = ref('')
const resultRows = ref<Array<Record<string, string | number | null>>>([])
const resultColumns = ref<string[]>([])
const resultTotal = ref(0)
const page = ref(1)
const pageSize = ref(20)
const showSplitPicker = ref(false)
const splitResults = ref<AddressFillSplitResult[]>([])
const inputFileRef = ref<HTMLInputElement | null>(null)
const streamListRef = ref<HTMLElement | null>(null)
const agentStream = ref<AgentStreamEntry[]>([])
const rowStates = ref<Map<string, AddressFillRowState>>(new Map())
const expandedRows = ref<string[]>([])
const expandedSubSteps = ref<string[]>([])
const streamPage = ref(1)
const streamPageSize = 10
let progressSocket: WebSocket | undefined
let progressTimer: number | undefined
let lastWorkflowEventId = ''
let progressStartedAt = 0
let progressTargetRows = 0
let streamSequence = 0

const splitColumns: TableColumn[] = [
  { key: 'taskName', label: '任务名称', width: '34%' },
  { key: 'splitScheme', label: '字段结构', width: '18%' },
  { key: 'total', label: '总条数', width: '12%' },
  { key: 'startedAt', label: '创建时间', width: '24%' },
  { key: 'actions', label: '操作', width: '12%' },
]

const createIdleProgress = (): ProgressState => ({
  percent: 0,
  summary: {
    processed: '当前未开始补全',
    elapsed: '上传文件后，点击启动地址补全',
  },
  steps: [
    { key: 'parse', label: '资料解析', status: 'waiting', text: '未开始' },
    { key: 'fill', label: '逐条补全', status: 'waiting', text: '未开始' },
    { key: 'summary', label: '结果汇总', status: 'waiting', text: '未开始' },
    { key: 'done', label: '完成', status: 'waiting', text: '未开始' },
  ],
})

const progress = ref<ProgressState>(createIdleProgress())

const inputLabel = computed(() => {
  if (selectedSplit.value) {
    return `已选择拆分结果：${selectedSplit.value.taskName}`
  }
  return inputFile.value ? `已上传：${inputFile.value.name}` : '上传同结构 Excel'
})

const inspectText = computed(() => inspectMessage.value)
const canSubmit = computed(() => Boolean(selectedSplit.value || inputFile.value))
const tableColumns = computed<TableColumn[]>(() =>
  resultColumns.value.map((key) => ({
    key,
    label: key,
    width: ['new_address', 'desc', 'new_fill_address'].includes(key) ? '260px' : undefined,
    className: ['new_address', 'desc', 'new_fill_address'].includes(key) ? 'address-cell' : undefined,
  })),
)
const totalPages = computed(() => Math.max(1, Math.ceil(resultTotal.value / pageSize.value)))
const pageButtons = computed(() => Array.from({ length: Math.min(totalPages.value, 5) }, (_, index) => index + 1))

const addressFromRow = (rowId: string) => {
  const index = Number(rowId) - 1
  const row = Number.isFinite(index) ? resultRows.value[index] : undefined
  const fromResult = row?.new_address === undefined || row?.new_address === null ? '' : String(row.new_address)
  if (fromResult) return fromResult
  const startEntry = agentStream.value.find((e) => e.rowId === rowId && e.stage === 'address_start')
  if (startEntry?.content) {
    const match = startEntry.content.match(/^(.+?)，(?:归属|当前)/)
    return match ? match[1] : startEntry.content
  }
  return ''
}

const formatToolCall = (payload: Record<string, unknown> | undefined) => {
  const toolName = String(payload?.tool_name ?? '')
  if (!toolName || toolName === 'tool_call_output_item') {
    return ''
  }
  let args: Record<string, unknown> = {}
  if (typeof payload?.arguments === 'string') {
    try {
      args = JSON.parse(payload.arguments) as Record<string, unknown>
    } catch {
      args = { arguments: payload.arguments }
    }
  }
  const names: Record<string, string> = {
    read_local_candidates: '读取系统候选',
    list_available_sources: '查看上传资料列表',
    read_source_chunks: '检索上传资料片段',
    read_prefetched_web_search_results: '读取预搜索结果',
    web_search: '联网搜索',
  }
  const prefix = names[toolName] ?? toolName
  return typeof args.query === 'string' ? `${prefix}：${args.query}` : prefix
}

const extractLinks = (payload: Record<string, unknown> | undefined) => {
  const rawLinks = payload?.links
  if (!Array.isArray(rawLinks)) return []
  return rawLinks
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const link = item as Record<string, unknown>
      const url = String(link.url ?? '').trim()
      if (!url) return null
      return {
        title: String(link.title ?? url).trim(),
        url,
        snippet: String(link.snippet ?? '').trim(),
      }
    })
    .filter((item): item is { title: string; url: string; snippet: string } => item !== null)
}

const formatWorkflowContent = (title: string, summary: string, payload: Record<string, unknown>) => {
  if (title.includes('工具调用')) {
    return formatToolCall(payload)
  }
  if (title.includes('浏览网站')) {
    const count = extractLinks(payload).length
    return count ? `联网搜索找到 ${count} 个可参考网站。` : summary
  }
  if (title.includes('候选汇总')) {
    return summary
  }
  if (title.includes('模型自主补全')) {
    const missing = Array.isArray(payload.missing_levels) ? `缺失字段：${payload.missing_levels.join('、')}` : ''
    return missing ? `模型先不调用工具，直接判断。${missing}` : '模型先不调用工具，直接判断。'
  }
  if (title.includes('外部辅助补全')) {
    return summary
  }
  return summary
}

const agentRows = computed<AgentRowLog[]>(() => {
  const rowIds = new Set<string>()
  for (const entry of agentStream.value) {
    if (entry.rowId) rowIds.add(entry.rowId)
  }
  for (let index = 1; index <= resultTotal.value; index += 1) {
    rowIds.add(String(index))
  }
  return Array.from(rowIds)
    .sort((a, b) => Number(a) - Number(b))
    .map((rowId) => {
      const entries = agentStream.value.filter((entry) => entry.rowId === rowId)
      const state = rowStates.value.get(rowId)
      const status = state?.status || (entries.some((e) => e.stage === 'address_end') ? 'done' : entries.length > 0 ? 'running' : 'waiting')
      const summary = status === 'done'
        ? '已完成全层级地址标准化补全，结果已写入 Excel 预览。'
        : status === 'running'
        ? '智能推理中…'
        : status === 'interrupted'
        ? '补全已中断'
        : '等待 AI 开始处理。'
      const statusText = status === 'done' ? '已完成' : status === 'running' ? '处理中' : status === 'interrupted' ? '已中断' : '等待中'
      return {
        rowId,
        address: state?.address || addressFromRow(rowId),
        status,
        statusText,
        summary,
        entries,
        step1Status: state?.step1_status || 'waiting',
        step2Status: state?.step2_status || 'waiting',
        step3Status: state?.step3_status || 'waiting',
        step4Status: state?.step4_status || 'waiting',
      }
    })
})

const streamTotalPages = computed(() => Math.max(1, Math.ceil(agentRows.value.length / streamPageSize)))
const streamPageStartIndex = computed(() => (streamPage.value - 1) * streamPageSize)
const streamPageStart = computed(() => agentRows.value.length ? streamPageStartIndex.value + 1 : 0)
const streamPageEnd = computed(() => Math.min(streamPageStartIndex.value + streamPageSize, agentRows.value.length))
const pagedAgentRows = computed(() => agentRows.value.slice(streamPageStartIndex.value, streamPageEnd.value))
const streamPageButtons = computed(() => {
  const total = streamTotalPages.value
  const start = Math.max(1, Math.min(streamPage.value - 2, total - 4))
  return Array.from({ length: Math.min(total, 5) }, (_, index) => start + index)
})
const currentAgentRow = computed(() => {
  const running = agentRows.value.find((row) => row.status === 'running')
  if (running) return running
  if (isSubmitting.value) {
    return agentRows.value.find((row) => row.status === 'waiting') ?? null
  }
  return null
})

const changeStreamPage = (nextPage: number) => {
  streamPage.value = Math.min(Math.max(nextPage, 1), streamTotalPages.value)
  void nextTick(() => {
    if (streamListRef.value) {
      streamListRef.value.scrollTop = 0
    }
  })
}

const locateCurrentAddress = () => {
  const target = currentAgentRow.value
  if (!target) return
  const index = agentRows.value.findIndex((row) => row.rowId === target.rowId)
  if (index < 0) return
  streamPage.value = Math.floor(index / streamPageSize) + 1
  if (!expandedRows.value.includes(target.rowId)) {
    expandedRows.value = [...expandedRows.value, target.rowId]
  }
  void nextTick(() => {
    if (streamListRef.value) {
      streamListRef.value.scrollTop = 0
    }
  })
}

interface FillSubStep {
  seq: number
  subType: string
  title: string
  content: string
  links: Array<{ title: string; url: string; snippet?: string }>
  time: string
}

interface FillStep {
  key: string
  index: number
  label: string
  status: 'waiting' | 'doing' | 'done'
  statusText: string
  content: string
  loading: boolean
  subSteps: FillSubStep[]
}

const FILL_STEP_DEFS = [
  { key: 'analyze', label: '层级研判：识别原始地址缺失层级' },
  { key: 'target', label: '任务定标：确定需补全的目标地址层级' },
  { key: 'reasoning', label: '智能推理：模型分析与地址补全' },
  { key: 'output', label: '结果生成：完成全层级地址标准化补全' },
]

const getFillSteps = (row: AgentRowLog): FillStep[] => {
  const entries = row.entries
  const stepEvents = entries.filter((e) => e.stage === 'step')
  const subStepEntries = entries.filter((e) => e.stage === 'sub_step')

  const findStepEvent = (stepNum: number) =>
    stepEvents.find((e) => { try { return JSON.parse(e.detail).step === stepNum } catch { return false } })

  const hasResultSubStep = subStepEntries.some((e) => {
    try { return JSON.parse(e.detail).sub_type === 'result' } catch { return false }
  })

  const step1Status = row.step1Status
  const step2Status = row.step2Status
  const step3Status = row.step3Status
  const step4Status = row.step4Status

  const step3Loading = step3Status === 'doing' && !hasResultSubStep

  const subSteps: FillSubStep[] = subStepEntries.map((e) => {
    let subType = 'reasoning'
    let seq = 0
    try {
      const d = JSON.parse(e.detail)
      subType = d.sub_type || 'reasoning'
      seq = d.sub_step || 0
    } catch { /* ignore */ }
    return { seq, subType, title: e.title, content: e.content, links: e.links, time: e.time }
  })

  const getStepStatusText = (status: string) => {
    if (status === 'done') return '已完成'
    if (status === 'doing') return '进行中'
    return '等待中'
  }

  const steps: FillStep[] = [
    {
      key: 'analyze',
      index: 1,
      label: FILL_STEP_DEFS[0].label,
      status: step1Status as 'waiting' | 'doing' | 'done',
      statusText: getStepStatusText(step1Status),
      content: findStepEvent(1)?.content || '',
      loading: false,
      subSteps: [],
    },
    {
      key: 'target',
      index: 2,
      label: FILL_STEP_DEFS[1].label,
      status: step2Status as 'waiting' | 'doing' | 'done',
      statusText: getStepStatusText(step2Status),
      content: findStepEvent(2)?.content || '',
      loading: false,
      subSteps: [],
    },
    {
      key: 'reasoning',
      index: 3,
      label: FILL_STEP_DEFS[2].label,
      status: step3Status as 'waiting' | 'doing' | 'done',
      statusText: getStepStatusText(step3Status),
      content: '',
      loading: step3Loading && subSteps.length === 0,
      subSteps,
    },
    {
      key: 'output',
      index: 4,
      label: FILL_STEP_DEFS[3].label,
      status: step4Status as 'waiting' | 'doing' | 'done',
      statusText: getStepStatusText(step4Status),
      content: findStepEvent(4)?.content || '',
      loading: false,
      subSteps: [],
    },
  ]
  return steps
}

const toggleAddressLog = (rowId: string) => {
  expandedRows.value = expandedRows.value.includes(rowId)
    ? expandedRows.value.filter((item) => item !== rowId)
    : [...expandedRows.value, rowId]
}

const toggleSubStep = (key: string) => {
  expandedSubSteps.value = expandedSubSteps.value.includes(key)
    ? expandedSubSteps.value.filter((item) => item !== key)
    : [...expandedSubSteps.value, key]
}

const subStepSummary = (content: string) => {
  if (!content) return ''
  const firstLine = content.split('\n')[0].trim()
  return firstLine.length > 80 ? firstLine.slice(0, 80) + '…' : firstLine
}

const pushAgentStream = (event: FillProgressEvent) => {
  // [DEBUG] 工具输出单独打日志，因为下面会跳过这类事件
  if (event.stage === 'tool_call' && event.payload?.tool_name === 'tool_call_output_item') {
    const output = String(event.payload?.output ?? event.content ?? event.message ?? '')
    console.log(
      `%c[Tool Output]%c ${new Date().toLocaleTimeString()} | row=${event.row_id ?? ''}\n${output.slice(0, 2000)}`,
      'color:#f97316;font-weight:bold', 'color:inherit',
      event.payload,
    )
    return
  }
  const content = event.stage === 'tool_call'
    ? formatToolCall(event.payload)
    : event.content || event.message || ''
  if (!content) return
  const entryId = String(event.payload?.event_id ?? `${Date.now()}-${streamSequence++}`)
  if (agentStream.value.some((item) => item.id === entryId)) return
  if (event.payload?.event_id && typeof event.payload.event_id === 'string') {
    lastWorkflowEventId = event.payload.event_id
  }
  const isSubStep = event.stage === 'sub_step'
  const isStep = event.stage === 'step'
  const detail = isSubStep
    ? JSON.stringify({ step: event.payload?.step, sub_step: event.payload?.sub_step, sub_type: event.payload?.sub_type })
    : isStep ? JSON.stringify({ step: event.payload?.step }) : ''
  const entry: AgentStreamEntry = {
    id: entryId,
    stage: event.stage ?? 'reasoning',
    rowId: event.row_id ?? '',
    title: event.title || '补全事件',
    content,
    detail,
    links: extractLinks(event.payload),
    time: new Date().toLocaleTimeString(),
  }
  agentStream.value.push(entry)
  if (agentStream.value.length > 300) {
    agentStream.value = agentStream.value.slice(-300)
  }
  void nextTick(() => {
    if (streamListRef.value) {
      streamListRef.value.scrollTop = streamListRef.value.scrollHeight
    }
  })
}

const catchUpMissedEvents = async () => {
  if (!latestJobId.value) return
  try {
    const events = await getAddressFillEvents(latestJobId.value, lastWorkflowEventId || undefined)
    for (const event of events) {
      if (event.phase !== 'agent') continue
      if (agentStream.value.some((entry) => entry.id === event.event_id)) continue
      lastWorkflowEventId = event.event_id

      const content = formatWorkflowContent(event.title, event.summary, event.payload)
      if (!content) continue
      if (event.title.includes('工具调用') && event.payload?.tool_name === 'tool_call_output_item') continue

      const title = event.title.replace(/^第\s*(\S+)\s*行：/, '地址 $1 · ')
      const payloadStage = typeof event.payload?.stage === 'string' ? event.payload.stage : ''
      const isSubStep = event.payload?.sub_step !== undefined
      const isStep = !isSubStep && event.payload?.step !== undefined
      let stage = payloadStage
      if (!stage) {
        const isEnd = event.title.includes('模型推理完毕') || event.title.includes('结束')
        const isStart = !isEnd && event.title.includes('模型推理')
        stage = isSubStep ? 'sub_step' : isStep ? 'step' : isStart ? 'address_start' : isEnd ? 'address_end' : 'reasoning'
      }
      pushAgentStream({
        job_id: latestJobId.value,
        event_type: 'agent_stream',
        phase: 'agent',
        stage,
        row_id: String(event.payload?.row_id ?? ''),
        title,
        content,
        processed_rows: 0,
        total_rows: 0,
        elapsed_seconds: 0,
        payload: { event_id: event.event_id, row_id: event.payload?.row_id, ...event.payload },
      } as FillProgressEvent)
    }
    if (events.length > 0) {
      await nextTick()
      if (streamListRef.value) {
        streamListRef.value.scrollTop = streamListRef.value.scrollHeight
      }
    }
  } catch {
    // websocket is primary; catch-up is best-effort
  }
}

const ensureClientId = () => {
  const saved = localStorage.getItem(CLIENT_ID_KEY)
  if (saved) {
    clientId.value = saved
    return
  }
  clientId.value = createSplitJobId()
  localStorage.setItem(CLIENT_ID_KEY, clientId.value)
}

const formatDuration = (seconds: number) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':')
}

const currentElapsedSeconds = () => (
  progressStartedAt > 0 ? Math.max(0, Math.floor((Date.now() - progressStartedAt) / 1000)) : 0
)

const updateElapsedTicker = () => {
  if (!isSubmitting.value || progressStartedAt <= 0) return
  progress.value.summary.elapsed = `耗时 ${formatDuration(currentElapsedSeconds())}`
}

const stopProgressTimer = () => {
  if (progressTimer !== undefined) {
    window.clearInterval(progressTimer)
    progressTimer = undefined
  }
}

const startProgressTimer = (startedAt = Date.now()) => {
  stopProgressTimer()
  progressStartedAt = startedAt
  updateElapsedTicker()
  progressTimer = window.setInterval(updateElapsedTicker, 1000)
}

const setProgress = (
  processed: number,
  total: number,
  elapsedSeconds: number | undefined,
  phase: string,
  message = '',
) => {
  const percent = total > 0 ? Math.min(Math.round((processed / total) * 100), 100) : 0
  const parsing = phase === 'parsing'
  const summaryDoing = phase === 'summary'
  const done = phase === 'done'
  const cancelled = phase === 'cancelled'
  const failed = phase === 'error'
  const elapsed = progressStartedAt > 0
    ? Math.max(elapsedSeconds ?? 0, currentElapsedSeconds())
    : elapsedSeconds ?? 0

  progress.value = {
    percent,
    summary: {
      processed: failed
        ? (message || '补全失败')
        : cancelled
        ? `已补全 ${processed.toLocaleString()} / ${total.toLocaleString()} 条（已中断）`
        : done
        ? `已补全 ${processed.toLocaleString()} / ${total.toLocaleString()} 条`
        : `已补全 ${processed.toLocaleString()} / ${total.toLocaleString()} 条`,
      elapsed: cancelled
        ? (message || `耗时 ${formatDuration(elapsed)}`)
        : failed
        ? (message || '请检查文件或稍后重试')
        : message || `耗时 ${formatDuration(elapsed)}`,
    },
    steps: [
      { key: 'parse', label: '资料解析', status: parsing ? 'doing' : failed ? 'waiting' : 'done', text: parsing ? '处理中' : failed ? '未完成' : '已完成' },
      { key: 'fill', label: '逐条补全', status: cancelled ? 'interrupted' : failed ? 'waiting' : parsing ? 'waiting' : done || summaryDoing ? 'done' : 'doing', text: cancelled ? '补全中断' : failed ? '未完成' : parsing ? '等待中' : done || summaryDoing ? '已完成' : '处理中' },
      { key: 'summary', label: '结果汇总', status: done || cancelled ? 'done' : summaryDoing ? 'doing' : 'waiting', text: done || cancelled ? '已完成' : summaryDoing ? '汇总中' : '等待中' },
      { key: 'done', label: '完成', status: done ? 'done' : cancelled ? 'interrupted' : 'waiting', text: done ? '已完成' : cancelled ? '已保留结果' : '等待中' },
    ],
  }
}

const persistFillState = () => {
  const rowStatesObj: Record<string, AddressFillRowState> = {}
  rowStates.value.forEach((value, key) => {
    rowStatesObj[key] = value
  })
  const payload = {
    progress: progress.value,
    latestJobId: latestJobId.value,
    isSubmitting: isSubmitting.value,
    downloadUrl: downloadUrl.value,
    resultColumns: resultColumns.value,
    resultRows: resultRows.value,
    resultTotal: resultTotal.value,
    agentStream: agentStream.value,
    rowStates: rowStatesObj,
    lastWorkflowEventId,
    progressTargetRows,
    progressStartedAt,
    streamPage: streamPage.value,
    savedAt: Date.now(),
  }
  sessionStorage.setItem(FILL_STATE_KEY, JSON.stringify(payload))
}

const restoreFillState = () => {
  const raw = sessionStorage.getItem(FILL_STATE_KEY)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    progress.value = payload.progress ?? createIdleProgress()
    latestJobId.value = payload.latestJobId ?? ''
    downloadUrl.value = payload.downloadUrl ?? ''
    resultColumns.value = Array.isArray(payload.resultColumns) ? payload.resultColumns : []
    resultRows.value = Array.isArray(payload.resultRows) ? payload.resultRows : []
    resultTotal.value = payload.resultTotal ?? 0
    agentStream.value = Array.isArray(payload.agentStream) ? payload.agentStream : []
    if (payload.rowStates && typeof payload.rowStates === 'object') {
      rowStates.value = new Map(Object.entries(payload.rowStates) as [string, AddressFillRowState][])
    }
    lastWorkflowEventId = typeof payload.lastWorkflowEventId === 'string' ? payload.lastWorkflowEventId : ''
    progressTargetRows = Number(payload.progressTargetRows) || 0
    streamPage.value = Math.max(1, Number(payload.streamPage) || 1)
    const jobStillRunning = Boolean(payload.isSubmitting && latestJobId.value)
    isSubmitting.value = jobStillRunning
    progressStartedAt = Number(payload.progressStartedAt) || (jobStillRunning ? Number(payload.savedAt) || Date.now() : 0)
    if (!jobStillRunning && payload.progress?.percent > 0) {
      isSubmitting.value = false
    }
  } catch {
    sessionStorage.removeItem(FILL_STATE_KEY)
  }
}

const stopProgressSocket = () => {
  if (progressSocket !== undefined) {
    progressSocket.close()
    progressSocket = undefined
  }
}

const startProgressSocket = (jobId: string, targetRows: number) => {
  stopProgressSocket()
  progressTargetRows = Math.max(targetRows, 1)
  startProgressTimer()
  setProgress(0, progressTargetRows, 0, 'parsing')
  progressSocket = connectFillProgress(jobId, {
    onMessage: applyProgressEvent,
    onError: () => {
      if (isSubmitting.value) {
        setProgress(0, progressTargetRows, undefined, 'parsing', '进度通道连接异常，正在重连…')
      }
    },
    onClose: () => {
      if (isSubmitting.value) {
        window.setTimeout(() => {
          if (isSubmitting.value && latestJobId.value) {
            reconnectProgressSocket(latestJobId.value)
          }
        }, 2000)
      }
    },
  })
  void catchUpMissedEvents()
}

const reconnectProgressSocket = (jobId: string) => {
  if (!jobId) return
  stopProgressSocket()
  if (progressStartedAt <= 0) {
    progressStartedAt = Date.now()
  }
  if (progressTimer === undefined) {
    startProgressTimer(progressStartedAt)
  }
  progressSocket = connectFillProgress(jobId, {
    onMessage: applyProgressEvent,
    onError: () => {
      if (isSubmitting.value) {
        progress.value.summary.elapsed = '进度通道连接异常，正在重连…'
      }
    },
    onClose: () => {
      if (isSubmitting.value) {
        window.setTimeout(() => {
          if (isSubmitting.value && latestJobId.value) {
            reconnectProgressSocket(latestJobId.value)
          }
        }, 2000)
      }
    },
  })
  void catchUpMissedEvents()
}

const applyProgressEvent = (event: FillProgressEvent) => {
  // [DEBUG] 控制台输出所有 WebSocket 事件
  const ts = new Date().toLocaleTimeString()

  if (event.event_type === 'full_row_states') {
    const rowStatesData = (event as any).row_states
    if (Array.isArray(rowStatesData)) {
      const newMap = new Map<string, AddressFillRowState>()
      for (const state of rowStatesData) {
        newMap.set(state.row_id, state)
      }
      rowStates.value = newMap
    }
    persistFillState()
    return
  }

  if (event.event_type === 'step_state_update') {
    const rowId = event.row_id ?? ''
    if (rowId) {
      rowStates.value.set(rowId, {
        job_id: event.job_id ?? latestJobId.value,
        row_id: rowId,
        address: (event as any).address ?? '',
        status: (event as any).status ?? 'waiting',
        step1_status: (event as any).step1_status ?? 'waiting',
        step2_status: (event as any).step2_status ?? 'waiting',
        step3_status: (event as any).step3_status ?? 'waiting',
        step4_status: (event as any).step4_status ?? 'waiting',
        updated_at: new Date().toISOString(),
      })
    }
    persistFillState()
    return
  }

  if (event.event_type === 'agent_stream') {
    const stage = event.stage ?? ''
    const rowId = event.row_id ?? ''
    const title = event.title ?? ''
    const content = event.content ?? event.message ?? ''
    const toolName = String(event.payload?.tool_name ?? '')
    const query = typeof event.payload?.query === 'string' ? event.payload.query : ''
    console.log(
      `%c[Agent Stream]%c ${ts} | row=${rowId} | stage=${stage} | tool=${toolName}\n%c${title}%c\n${content}${query ? '\nquery: ' + query : ''}`,
      'color:#8b5cf6;font-weight:bold', 'color:inherit',
      'color:#1d4ed8;font-weight:bold', 'color:inherit',
      event.payload,
    )
    pushAgentStream(event)
    if (event.stage === 'address_end' || event.payload?.preview_refresh === true) {
      loadResult()
    }
    persistFillState()
    return
  }
  if (event.event_type === 'stage') {
    console.log(
      `%c[Stage]%c ${ts} | phase=${event.phase} | ${event.message ?? ''}`,
      'color:#f97316;font-weight:bold', 'color:inherit',
    )
    return
  }
  console.log(
    `%c[Progress]%c ${ts} | phase=${event.phase} | processed=${event.processed_rows}/${event.total_rows} | ${event.elapsed_seconds ?? 0}s | ${event.message ?? ''}`,
    'color:#10b981;font-weight:bold', 'color:inherit',
  )
  if (event.total_rows > 0) {
    progressTargetRows = event.total_rows
  }
  const total = progressTargetRows || event.total_rows || 1
  setProgress(
    event.processed_rows ?? 0,
    total,
    event.elapsed_seconds ?? 0,
    event.phase,
    event.phase === 'error' ? event.message : '',
  )
  if (event.phase === 'filling') {
    loadResult()
  }
  if (event.phase === 'done' || event.phase === 'cancelled') {
    stopProgressTimer()
    loadResult()
    isSubmitting.value = false
    isCancelling.value = false
    window.setTimeout(() => {
      void catchUpMissedEvents()
    }, 500)
  }
  persistFillState()
}

const loadResult = async () => {
  if (!latestJobId.value) return
  try {
    const detail = await getAddressFillResultDetail(latestJobId.value, { page: page.value, pageSize: pageSize.value })
    resultRows.value = detail.rows
    resultColumns.value = detail.columns
    resultTotal.value = detail.totalRows
    downloadUrl.value = buildDownloadUrl(detail.downloadUrl)
  } catch {
    // keep existing result
  }
}

const openSplitPicker = async () => {
  errorMessage.value = ''
  splitResults.value = await getAddressFillSplitResults()
  showSplitPicker.value = true
}

const selectSplitResult = (row: AddressFillSplitResult) => {
  selectedSplit.value = row
  inputFile.value = null
  inputColumnMode.value = row.columnMode
  inspectMessage.value = `已选择 ${row.splitScheme}，共 ${row.total.toLocaleString()} 行。`
  showSplitPicker.value = false
}

const handleInputFileChange = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null
  inputFile.value = file
  selectedSplit.value = null
  inputColumnMode.value = ''
  if (!file) {
    inspectMessage.value = '请选择已拆分完成的 Excel，或直接上传同结构 Excel。'
    return
  }
  const result = await inspectAddressFillInput(file)
  inputColumnMode.value = result.columnMode
  inspectMessage.value = `${result.message}；共 ${result.totalRows.toLocaleString()} 行。`
  if (!result.accepted) {
    errorMessage.value = result.message
  }
}

const submitFill = async () => {
  if (!canSubmit.value) {
    errorMessage.value = '请先选择拆分结果或上传 Excel'
    return
  }
  isSubmitting.value = true
  isCancelling.value = false
  errorMessage.value = ''
  progress.value = createIdleProgress()
  agentStream.value = []
  rowStates.value = new Map()
  streamPage.value = 1
  streamSequence = 0
  lastWorkflowEventId = ''
  try {
    const response = await createAddressFillJob({
      clientId: clientId.value,
      inputFile: inputFile.value,
      splitJobId: selectedSplit.value?.id,
      sourceFiles: sourceFiles.value,
      clientJobId: createSplitJobId(),
    })
    latestJobId.value = response.job_id
    resultRows.value = response.preview
    resultColumns.value = response.columns
    resultTotal.value = response.total_rows
    downloadUrl.value = buildDownloadUrl(response.download_url)
    startProgressSocket(response.job_id, response.total_rows || 0)
    persistFillState()
  } catch (error) {
    stopProgressTimer()
    errorMessage.value = error instanceof Error ? error.message : '地址补全失败'
    isSubmitting.value = false
  }
}

const cancelFill = async () => {
  if (!latestJobId.value || isCancelling.value) return
  isCancelling.value = true
  try {
    await cancelAddressFillJob(latestJobId.value)
  } catch {
    isCancelling.value = false
  }
}

const changePage = async (nextPage: number) => {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value || !latestJobId.value) {
    return
  }
  page.value = nextPage
  await loadResult()
}

const changePageSize = async (nextPageSize: number) => {
  pageSize.value = nextPageSize
  page.value = 1
  if (latestJobId.value) {
    await loadResult()
  }
}

watch(
  () => agentRows.value.length,
  () => {
    if (streamPage.value > streamTotalPages.value) {
      streamPage.value = streamTotalPages.value
    }
  },
)

const initRowStates = async (jobId: string) => {
  try {
    const states = await getAddressFillRowStates(jobId)
    if (states.length > 0) {
      const newMap = new Map<string, AddressFillRowState>()
      for (const state of states) {
        newMap.set(state.row_id, state)
      }
      rowStates.value = newMap
    }
  } catch {
    // ignore
  }
}

onMounted(async () => {
  ensureClientId()
  restoreFillState()
  if (isSubmitting.value && latestJobId.value) {
    startProgressTimer(progressStartedAt || Date.now())
    reconnectProgressSocket(latestJobId.value)
    void initRowStates(latestJobId.value)
  } else if (latestJobId.value) {
    void catchUpMissedEvents()
    void initRowStates(latestJobId.value)
  }
})

onBeforeUnmount(() => {
  stopProgressTimer()
  stopProgressSocket()
  persistFillState()
})
</script>

<style scoped>
.fill-grid {
  display: block;
}

.fill-panel {
  display: grid;
  gap: 14px;
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #fff;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-title h3 {
  margin: 0;
  font-size: 18px;
}

.file-input {
  display: none;
}

.upload-line {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 72px;
  padding: 0 18px;
  border: 1px dashed #bfdbfe;
  border-radius: 14px;
  color: #1e40af;
  background: #f8fbff;
  font-weight: 800;
  cursor: pointer;
}

.source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-chip {
  max-width: 220px;
  padding: 7px 10px;
  overflow: hidden;
  border-radius: 999px;
  color: #0f766e;
  background: #ecfdf5;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 750;
}

.fill-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin: 18px 0;
}

@media (max-width: 900px) {
  .stream-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .stream-controls > span {
    margin-right: 0;
  }

  .locate-button,
  .stream-pager {
    width: 100%;
  }

  .stream-pager {
    justify-content: space-between;
  }
}

.error-note {
  margin: 0 auto 0 0;
  color: var(--danger);
  font-weight: 700;
}

.progress-section {
  margin: 0 0 18px;
}

.stream-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.stream-header h3 {
  margin: 0 0 4px;
  font-size: 18px;
}

.stream-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 650;
}

.stream-percent {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 18px;
  font-weight: 850;
}

.stream-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #f8fbff;
}

.stream-controls > span {
  margin-right: auto;
  color: #64748b;
  font-size: 13px;
  font-weight: 750;
}

.locate-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding-inline: 12px;
}

.stream-pager {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.icon-button,
.stream-page-button {
  display: inline-grid;
  place-items: center;
  min-width: 34px;
  height: 34px;
  border: 1px solid #c7d7ee;
  border-radius: 9px;
  color: #334155;
  background: #fff;
  font-weight: 800;
  cursor: pointer;
}

.icon-button:disabled,
.stream-page-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.stream-page-button.active {
  color: #fff;
  border-color: #1d4ed8;
  background: #1d4ed8;
}

.agent-stream {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #f8fafc;
}

.stream-empty {
  padding: 18px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  color: #64748b;
  background: #fff;
  text-align: center;
  font-weight: 650;
}

.address-log-card {
  overflow: hidden;
  border: 1px solid #dbe4f0;
  border-radius: 10px;
  background: #fff;
}

.address-log-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 14px 16px;
  border: 0;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.address-log-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.address-log-title strong {
  overflow-wrap: anywhere;
  color: #0f172a;
}

.row-pill {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: 999px;
  color: #1d4ed8;
  background: #dbeafe;
  font-size: 12px;
  font-weight: 850;
}

.address-log-summary p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 650;
}

.address-log-status {
  flex: 0 0 auto;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.address-log-status.waiting {
  color: #64748b;
  background: #e2e8f0;
}

.address-log-status.running {
  color: #1d4ed8;
  background: #dbeafe;
}

.address-log-status.done {
  color: #047857;
  background: #d1fae5;
}

.address-log-detail {
  display: grid;
  gap: 12px;
  padding: 0 16px 16px 30px;
}

.fill-steps {
  display: grid;
  gap: 10px;
}

.fill-step {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 10px;
  align-items: start;
}

.fill-step-index {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
}

.fill-step.doing .fill-step-index {
  background: #dbeafe;
  color: #1d4ed8;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
}

.fill-step.done .fill-step-index {
  background: #d1fae5;
  color: #047857;
}

.fill-step-body {
  min-width: 0;
}

.fill-step-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.fill-step-head strong {
  color: #1e293b;
  font-size: 14px;
}

.fill-step-tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 750;
}

.fill-step-tag.waiting {
  color: #94a3b8;
  background: #f1f5f9;
}

.fill-step-tag.doing {
  color: #1d4ed8;
  background: #dbeafe;
}

.fill-step-tag.done {
  color: #047857;
  background: #d1fae5;
}

.fill-step-content {
  margin: 4px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.fill-step-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: #6366f1;
  font-size: 13px;
  font-weight: 650;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #c7d2fe;
  border-top-color: #6366f1;
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.fill-substeps {
  display: grid;
  gap: 8px;
  margin-top: 8px;
  padding-left: 4px;
  border-left: 2px solid #e2e8f0;
}

.fill-substep {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: 8px;
  align-items: start;
}

.fill-substep-seq {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 750;
  text-align: right;
  padding-top: 2px;
}

.fill-substep-body {
  min-width: 0;
}

.fill-substep-toggle {
  display: block;
  width: 100%;
  padding: 4px 6px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.fill-substep-toggle:hover {
  background: #f1f5f9;
}

.fill-substep-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.fill-substep-head strong {
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.fill-substep-head small {
  margin-left: auto;
  color: #94a3b8;
  font-size: 11px;
  white-space: nowrap;
}

.fill-substep-preview {
  margin: 2px 0 0;
  color: #94a3b8;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fill-substep-chevron {
  position: absolute;
  right: 6px;
  top: 6px;
  color: #94a3b8;
}

.fill-substep {
  position: relative;
}

.fill-substep-detail {
  padding: 4px 6px 4px 36px;
}

.fill-substep-content {
  margin: 2px 0 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.55;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.sub-tool_call .fill-substep-seq {
  color: #f97316;
}

.sub-tool_output .fill-substep-seq {
  color: #a855f7;
}

.sub-reasoning .fill-substep-seq {
  color: #6366f1;
}

.sub-result .fill-substep-seq {
  color: #10b981;
}

.sub-retry .fill-substep-seq {
  color: #ef4444;
}

.visited-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.visited-links a {
  max-width: 320px;
  padding: 4px 8px;
  overflow: hidden;
  border: 1px solid #bae6fd;
  border-radius: 999px;
  color: #0369a1;
  background: #f0f9ff;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 700;
}

.visited-links a:hover {
  border-color: #38bdf8;
  background: #e0f2fe;
}

.process-empty {
  color: #94a3b8;
  font-size: 13px;
  font-weight: 650;
}

.progress-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}

.progress-panel {
  display: grid;
  gap: 14px;
  align-content: start;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: #fff;
}

.progress-panel h3 {
  margin: 0;
  font-size: 18px;
}

.progress-ring {
  --percent: 0;
  --size: 110px;
  --half: calc(var(--size) / 2);
  --stroke: 8px;
  --radius: calc(var(--half) - var(--stroke));
  --circumference: calc(2 * 3.14159265 * var(--radius));
  position: relative;
  width: var(--size);
  height: var(--size);
  border-radius: 999px;
  background: conic-gradient(
    #3b82f6 calc(var(--percent) * 1%),
    #e2e8f0 calc(var(--percent) * 1%)
  );
  place-self: center;
}

.progress-ring-inner {
  position: absolute;
  inset: var(--stroke);
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #fff;
  font-size: 22px;
}

.progress-main {
  margin: 0;
  text-align: center;
  font-weight: 700;
  color: #1e293b;
}

.progress-sub {
  margin: 0;
  text-align: center;
  font-size: 13px;
  color: #64748b;
}

.progress-steps {
  display: grid;
  gap: 10px;
  margin-top: 6px;
}

.progress-step {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.step-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #cbd5e1;
}

.step-dot.doing {
  background: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
  animation: pulse-dot 1.4s ease-in-out infinite;
}

.step-dot.done {
  background: #10b981;
}

.step-dot.interrupted {
  background: #f59e0b;
}

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25); }
  50% { box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.12); }
}

.step-status {
  font-size: 13px;
  font-weight: 700;
  color: #94a3b8;
}

.step-status.is-doing {
  color: #3b82f6;
}

.step-status.is-done {
  color: #10b981;
}

.step-status.is-interrupted {
  color: #f59e0b;
}

.danger-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  border: 1px solid #fca5a5;
  border-radius: 10px;
  color: #b91c1c;
  background: #fef2f2;
  font-weight: 750;
  cursor: pointer;
}

.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-section {
  margin-top: 24px;
}

.result-toolbar {
  justify-content: flex-end;
  margin-bottom: 14px;
}

.secondary-button.disabled {
  pointer-events: none;
  color: #94a3b8;
  border-color: var(--border);
  background: #f8fafc;
}

.split-picker {
  width: min(860px, calc(100dvw - 40px));
  max-height: min(760px, calc(100dvh - 40px));
}

.action-button {
  min-height: auto;
  padding: 0;
  border: 0;
  background: transparent;
}

.split-picker :deep(.modal-body) {
  min-height: 0;
}

.split-picker :deep(.table-wrap) {
  flex: 1 1 auto;
  min-height: 0;
  max-height: min(520px, calc(100dvh - 190px));
  overflow-y: auto;
  overflow-x: hidden;
}

.split-picker :deep(.data-table) {
  min-width: 0;
  table-layout: fixed;
}

.split-picker :deep(.data-table th),
.split-picker :deep(.data-table td) {
  padding-inline: 14px;
  overflow-wrap: anywhere;
}

.split-picker :deep(.data-table th:last-child),
.split-picker :deep(.data-table td:last-child) {
  text-align: center;
}

@media (max-width: 900px) {
  .fill-grid {
    grid-template-columns: 1fr;
  }

  .fill-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .error-note {
    margin-right: 0;
  }
}
</style>
