import {
  detailColumns,
  detailStats,
  settingsByMode,
  manualInputSeed,
  progressSteps,
  validationRules,
  uploadProgress,
  uploadSummary,
} from '../mock/data'
import type { ColumnMode, ColumnSettingItem, SplitRecord, ValidationRule } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8008/api'

const wait = async (ms = 120) => new Promise((resolve) => window.setTimeout(resolve, ms))

const clone = <T>(value: T): T => {
  try {
    return structuredClone(value)
  } catch {
    return JSON.parse(JSON.stringify(value)) as T
  }
}

export interface SplitJobResponse {
  job_id: string
  status: string
  column_mode: ColumnMode
  total_rows: number
  processed_rows: number
  columns: string[]
  preview: Array<Record<string, string | number | null>>
  download_url: string
}

export interface SplitProgressEvent {
  job_id: string
  event_type?: 'progress' | 'agent_stream' | 'stage'
  phase: 'parsing' | 'splitting' | 'summary' | 'done' | 'cancelled' | 'error'
  processed_rows: number
  total_rows: number
  elapsed_seconds: number
  message?: string
  cached_job_id?: string
  stage?: string
  row_id?: string
  title?: string
  content?: string
  payload?: Record<string, unknown>
}

export interface SplitResultDetailResponse {
  stats: {
    total: string
    success: string
    failed: string
    successRate: string
  }
  rows: Array<Record<string, string | number | null>>
  columns: string[]
  columnMode: ColumnMode
  failedRows: Array<Record<string, string | number | null>>
  downloadUrl: string
  page: number
  pageSize: number
  totalRows: number
}

export interface ExcelInspectResponse {
  filename: string
  total_rows: number
  address_rows: number
  address_column: string
  columns: string[]
}

export interface RedisConfig {
  id?: string
  mode: 'local' | 'remote' | 'disabled'
  host: string
  port: number
  db: number
  password: string
  active?: boolean
  updatedAt?: string
}

export interface RedisConfigListResponse {
  activeId: string
  configs: RedisConfig[]
}

export interface RedisConfigActivateResponse {
  activeId: string
  config: RedisConfig
}

export interface RedisTestResponse {
  ok: boolean
  message: string
}

export interface RedisStatusResponse {
  available: boolean
  mode: 'local' | 'remote' | 'disabled'
  host: string
  port: number
  db: number
  message: string
}

export interface ModelConfig {
  id?: string
  provider: string
  baseUrl: string
  apiKey: string
  model: string
  active?: boolean
  updatedAt?: string
}

export interface ModelConfigListResponse {
  activeId: string
  models: ModelConfig[]
}

export interface ModelConfigTestResponse {
  ok: boolean
  message: string
}

export interface ModelConfigActivateResponse {
  activeId: string
  model: ModelConfig
}

export interface ValidationRuleImportResponse {
  imported: number
  rules: ValidationRule[]
}

export interface AddressFillInputInspectResponse {
  filename: string
  totalRows: number
  columns: string[]
  columnMode: 'level8' | 'level11' | ''
  accepted: boolean
  message: string
}

export interface AddressFillSplitResult {
  id: string
  taskName: string
  total: number
  columnMode: string
  splitScheme: string
  startedAt: string
}

export interface AddressFillWorkflowEvent {
  event_id: string
  job_id: string
  phase: string
  event_type: string
  title: string
  summary: string
  status: string
  sequence: number
  created_at: string
  payload: Record<string, unknown>
}

export interface AddressFillJobDetail {
  job_id: string
  client_id: string
  status: string
  task_name: string
  input_source: string
  source_count: number
  total_rows: number
  success_rows: number
  failed_rows: number
  columns: string[]
  column_mode: string
  result_file?: string
  created_at: string
  updated_at: string
  error?: string
}

export interface AddressFillLatestWorkflowResponse {
  job: AddressFillJobDetail | null
  events: AddressFillWorkflowEvent[]
}

export interface AddressFillJobResponse {
  job_id: string
  status: string
  total_rows: number
  processed_rows: number
  columns: string[]
  preview: Array<Record<string, string | number | null>>
  download_url: string
}

export interface AddressFillResultDetailResponse {
  stats: {
    total: string
    success: string
    failed: string
    successRate: string
  }
  rows: Array<Record<string, string | number | null>>
  columns: string[]
  columnMode: string
  failedRows: Array<Record<string, string | number | null>>
  downloadUrl: string
  page: number
  pageSize: number
  totalRows: number
}

export interface AddressFillRecord {
  id: string
  taskName: string
  inputSource: string
  sourceCount: number
  total: number
  success: number
  failed: number
  status: 'success' | 'partial'
  startedAt: string
  columnMode: string
  downloadUrl: string
}

const requestJson = async <T>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${url}`, init)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail ?? response.statusText)
  }

  return response.json() as Promise<T>
}

export const buildDownloadUrl = (downloadUrl: string) => {
  if (!downloadUrl) {
    return ''
  }

  if (downloadUrl.startsWith('http')) {
    return downloadUrl
  }

  return `${API_BASE_URL.replace(/\/api$/, '')}${downloadUrl}`
}

export const uploadAddressFile = async (
  file: File,
  payload: { columnMode: ColumnMode; sampleSize?: number; rawFields?: string[]; clientJobId?: string },
) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('column_mode', payload.columnMode)
  formData.append('sample_size', String(payload.sampleSize ?? 100))
  if (payload.clientJobId) {
    formData.append('client_job_id', payload.clientJobId)
  }
  if (payload.columnMode === 'raw' && payload.rawFields) {
    formData.append('raw_fields', JSON.stringify(payload.rawFields))
  }

  return requestJson<SplitJobResponse>('/splits', {
    method: 'POST',
    body: formData,
  })
}

export const inspectExcelFile = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  return requestJson<ExcelInspectResponse>('/excels/inspect', {
    method: 'POST',
    body: formData,
  })
}

export const submitManualAddress = async (payload: {
  content: string
  columnMode: ColumnMode
  rawFields?: string[]
  sampleSize?: number
  clientJobId?: string
}) => {
  const addresses = payload.content
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, payload.sampleSize)

  return requestJson<SplitJobResponse>('/splits/text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      addresses,
      column_mode: payload.columnMode,
      raw_fields: payload.columnMode === 'raw' ? payload.rawFields : undefined,
      client_job_id: payload.clientJobId,
    }),
  })
}

export const createSplitJobId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replace(/-/g, '')
  }

  return `${Date.now()}${Math.random().toString(16).slice(2)}`
}

export const connectSplitProgress = (
  jobId: string,
  handlers: {
    onMessage: (event: SplitProgressEvent) => void
    onError?: () => void
    onClose?: () => void
  },
) => {
  const base = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
  const socket = new WebSocket(`${base}/api/ws/splits/${jobId}`)
  let heartbeatTimer: ReturnType<typeof setTimeout> | undefined

  const resetHeartbeat = () => {
    if (heartbeatTimer !== undefined) clearTimeout(heartbeatTimer)
    heartbeatTimer = setTimeout(() => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }, 30_000)
  }

  socket.addEventListener('message', (event) => {
    resetHeartbeat()
    try {
      handlers.onMessage(JSON.parse(event.data) as SplitProgressEvent)
    } catch {
      // Ignore malformed progress frames; the final HTTP response still applies.
    }
  })
  socket.addEventListener('error', () => {
    if (heartbeatTimer !== undefined) clearTimeout(heartbeatTimer)
    handlers.onError?.()
  })
  socket.addEventListener('close', () => {
    if (heartbeatTimer !== undefined) clearTimeout(heartbeatTimer)
    handlers.onClose?.()
  })

  resetHeartbeat()
  return socket
}

export const getSplitProgress = async (_taskId?: string) => {
  await wait()
  return {
    percent: uploadProgress,
    summary: {
      processed: uploadSummary.processed,
      elapsed: uploadSummary.remaining,
    },
    steps: clone(progressSteps),
  }
}

export const getSplitPreview = async () => {
  await wait()
  return []
}

export const getValidationRuleList = async () => {
  try {
    return requestJson<ValidationRule[]>('/validation-rules')
  } catch {
    return clone(validationRules)
  }
}

export const createValidationRule = async (payload: {
  ruleId: string
  pattern: string
  levels: string[]
}) =>
  requestJson<ValidationRule>('/validation-rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const updateValidationRule = async (
  id: string,
  payload: {
    ruleId: string
    pattern: string
    levels: string[]
  },
) =>
  requestJson<ValidationRule>(`/validation-rules/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const deleteValidationRule = async (id: string) =>
  requestJson<{ deleted: boolean }>(`/validation-rules/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })

export const importValidationRules = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  return requestJson<ValidationRuleImportResponse>('/validation-rules/import', {
    method: 'POST',
    body: formData,
  })
}

const mapRecord = (item: any): SplitRecord => ({
  id: item.id,
  taskName: item.taskName,
  source: item.source,
  total: item.total,
  success: item.success,
  failed: item.failed,
  status: item.status,
  startedAt: item.startedAt,
  downloadUrl: buildDownloadUrl(item.downloadUrl),
  columnMode: item.columnMode,
  splitScheme: item.splitScheme,
  storageBackend: item.storageBackend,
  storageHost: item.storageHost,
  storagePort: item.storagePort,
  storageDb: item.storageDb,
  storageLabel: item.storageLabel,
})

export const deleteSplitRecord = async (id: string) =>
  requestJson<{ deleted: boolean }>(`/splits/${id}`, {
    method: 'DELETE',
  })

export const cancelSplitJob = async (id: string) =>
  requestJson<{ cancelled: boolean }>(`/splits/${id}/cancel`, {
    method: 'POST',
  })

export const downloadSplitRecord = (downloadUrl: string) => buildDownloadUrl(downloadUrl)

export const getSplitRecords = async () => {
  const records = await requestJson<any[]>('/splits')
  return records.map(mapRecord)
}

export const getSplitResultDetail = async (
  id?: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<SplitResultDetailResponse> => {
  if (id) {
    const search = new URLSearchParams({
      page: String(params.page ?? 1),
      page_size: String(params.pageSize ?? 20),
    })
    return requestJson<SplitResultDetailResponse>(`/splits/${id}/result?${search.toString()}`)
  }

  return {
    stats: clone(detailStats),
    rows: [],
    columns: detailColumns.map((item) => item.key),
    columnMode: 'level8' as ColumnMode,
    failedRows: [],
    downloadUrl: '',
    page: 1,
    pageSize: 20,
    totalRows: 0,
  }
}

export const getColumnSettings = async (mode: ColumnMode) => {
  await wait()
  return clone(settingsByMode[mode])
}

export const updateVisibleColumns = async (payload: {
  mode: ColumnMode
  columns: ColumnSettingItem[]
}) => {
  await wait()
  return clone(payload)
}

export const getManualInputSeed = async () => {
  await wait()
  return manualInputSeed
}

export const getRedisConfig = async () => requestJson<RedisConfig>('/environment/redis')

export const getRedisConfigs = async () => requestJson<RedisConfigListResponse>('/environment/redis/configs')

export const getRedisStatus = async () => requestJson<RedisStatusResponse>('/environment/redis/status')

export const saveRedisConfig = async (payload: RedisConfig) =>
  requestJson<RedisConfig>('/environment/redis', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const saveRedisConfigProfile = async (payload: RedisConfig) =>
  requestJson<RedisConfig>('/environment/redis/configs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const deleteRedisConfig = async (id: string) =>
  requestJson<{ deleted: boolean }>(`/environment/redis/configs/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })

export const activateRedisConfig = async (id: string) =>
  requestJson<RedisConfigActivateResponse>(`/environment/redis/configs/${encodeURIComponent(id)}/activate`, {
    method: 'POST',
  })

export const disconnectRedisConfig = async () =>
  requestJson<RedisConfig>('/environment/redis/disconnect', {
    method: 'POST',
  })

export const testRedisConfig = async (payload: RedisConfig) =>
  requestJson<RedisTestResponse>('/environment/redis/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const getModelConfigs = async () => requestJson<ModelConfigListResponse>('/environment/models')

export const saveModelConfig = async (payload: ModelConfig) =>
  requestJson<ModelConfig>('/environment/models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const deleteModelConfig = async (id: string) =>
  requestJson<{ deleted: boolean }>(`/environment/models/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })

export const testModelConfig = async (payload: ModelConfig) =>
  requestJson<ModelConfigTestResponse>('/environment/models/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const activateModelConfig = async (id: string) =>
  requestJson<ModelConfigActivateResponse>(`/environment/models/${encodeURIComponent(id)}/activate`, {
    method: 'POST',
  })

export const inspectAddressFillInput = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  return requestJson<AddressFillInputInspectResponse>('/address-fill/inputs/inspect', {
    method: 'POST',
    body: formData,
  })
}

export const getAddressFillSplitResults = async () =>
  requestJson<AddressFillSplitResult[]>('/address-fill/split-results')

export const createAddressFillJob = async (payload: {
  clientId: string
  inputFile?: File | null
  splitJobId?: string
  sourceFiles?: File[]
  clientJobId?: string
}) => {
  const formData = new FormData()
  formData.append('client_id', payload.clientId)
  if (payload.clientJobId) {
    formData.append('client_job_id', payload.clientJobId)
  }
  if (payload.inputFile) {
    formData.append('input_file', payload.inputFile)
  }
  if (payload.splitJobId) {
    formData.append('split_job_id', payload.splitJobId)
  }
  for (const file of payload.sourceFiles ?? []) {
    formData.append('source_files', file)
  }

  return requestJson<AddressFillJobResponse>('/address-fill/jobs', {
    method: 'POST',
    body: formData,
  })
}

export const getAddressFillLatestWorkflow = async (clientId: string) => {
  const search = new URLSearchParams({ client_id: clientId })
  return requestJson<AddressFillLatestWorkflowResponse>(`/address-fill/workflow/latest?${search.toString()}`)
}

export const getAddressFillEvents = async (jobId: string, afterEventId?: string) => {
  const search = new URLSearchParams()
  if (afterEventId) {
    search.set('after_event_id', afterEventId)
  }
  const suffix = search.toString() ? `?${search.toString()}` : ''
  const response = await fetch(`${API_BASE_URL}/address-fill/jobs/${jobId}/events${suffix}`)
  if (response.status === 404) return []
  if (!response.ok) return []
  return response.json() as Promise<AddressFillWorkflowEvent[]>
}

export const getAddressFillResultDetail = async (
  id: string,
  params: { page?: number; pageSize?: number } = {},
) => {
  const search = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 20),
  })
  return requestJson<AddressFillResultDetailResponse>(`/address-fill/jobs/${id}/result?${search.toString()}`)
}

export const getAddressFillRecords = async () => {
  const records = await requestJson<AddressFillRecord[]>('/address-fill/jobs')
  return records.map((item) => ({ ...item, downloadUrl: buildDownloadUrl(item.downloadUrl) }))
}

export const cancelAddressFillJob = async (id: string) =>
  requestJson<{ cancelled: boolean }>(`/address-fill/jobs/${id}/cancel`, {
    method: 'POST',
  })

export const deleteAddressFillRecord = async (id: string) =>
  requestJson<{ deleted: boolean }>(`/address-fill/jobs/${id}`, {
    method: 'DELETE',
  })

export interface AddressFillRowState {
  job_id: string
  row_id: string
  address: string
  status: 'waiting' | 'running' | 'done' | 'interrupted'
  step1_status: 'waiting' | 'doing' | 'done'
  step2_status: 'waiting' | 'doing' | 'done'
  step3_status: 'waiting' | 'doing' | 'done'
  step4_status: 'waiting' | 'doing' | 'done'
  updated_at: string
}

export const getAddressFillRowStates = async (jobId: string): Promise<AddressFillRowState[]> => {
  try {
    return await requestJson<AddressFillRowState[]>(`/address-fill/jobs/${jobId}/row-states`)
  } catch {
    return []
  }
}

export interface FillProgressEvent extends Omit<SplitProgressEvent, 'phase' | 'event_type'> {
  phase: SplitProgressEvent['phase'] | 'filling' | 'agent'
  event_type?: 'progress' | 'agent_stream' | 'stage' | 'step_state_update' | 'full_row_states'
}

export const connectFillProgress = (
  jobId: string,
  handlers: {
    onMessage: (event: FillProgressEvent) => void
    onError?: () => void
    onClose?: () => void
  },
) => {
  const base = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
  const socket = new WebSocket(`${base}/api/ws/address-fill/${jobId}`)
  let heartbeatTimer: ReturnType<typeof setTimeout> | undefined

  const resetHeartbeat = () => {
    if (heartbeatTimer !== undefined) clearTimeout(heartbeatTimer)
    heartbeatTimer = setTimeout(() => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }, 30_000)
  }

  socket.addEventListener('message', (event) => {
    resetHeartbeat()
    try {
      handlers.onMessage(JSON.parse(event.data) as FillProgressEvent)
    } catch {
      // ignore malformed progress frames
    }
  })
  socket.addEventListener('error', () => {
    if (heartbeatTimer !== undefined) clearTimeout(heartbeatTimer)
    handlers.onError?.()
  })
  socket.addEventListener('close', () => {
    if (heartbeatTimer !== undefined) clearTimeout(heartbeatTimer)
    handlers.onClose?.()
  })

  resetHeartbeat()
  return socket
}
