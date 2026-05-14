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
  phase: 'parsing' | 'splitting' | 'summary' | 'done' | 'cancelled' | 'error'
  processed_rows: number
  total_rows: number
  elapsed_seconds: number
  message?: string
  cached_job_id?: string
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
  mode: 'local' | 'remote' | 'disabled'
  host: string
  port: number
  db: number
  password: string
  updatedAt?: string
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

export interface ValidationRuleImportResponse {
  imported: number
  rules: ValidationRule[]
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

  socket.addEventListener('message', (event) => {
    try {
      handlers.onMessage(JSON.parse(event.data) as SplitProgressEvent)
    } catch {
      // Ignore malformed progress frames; the final HTTP response still applies.
    }
  })
  socket.addEventListener('error', () => handlers.onError?.())
  socket.addEventListener('close', () => handlers.onClose?.())

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

export const getRedisStatus = async () => requestJson<RedisStatusResponse>('/environment/redis/status')

export const saveRedisConfig = async (payload: RedisConfig) =>
  requestJson<RedisConfig>('/environment/redis', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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
