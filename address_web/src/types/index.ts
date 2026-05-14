export interface NavItem {
  label: string
  path?: string
  icon: string
}

export interface SplitResultRow {
  id: string
  rawAddress: string
  [key: string]: string | undefined
  province: string
  city: string
  district: string
  street: string
  road: string
  roadNo: string
  building: string
  roomNo: string
  result: string
  region?: string
}

export type ColumnMode = 'level8' | 'level11' | 'raw'

export interface ProgressStep {
  key: string
  label: string
  status: 'done' | 'doing' | 'waiting' | 'interrupted'
  text: string
}

export interface SplitRecord {
  id: string
  taskName: string
  source: string
  total: number
  success: number
  failed: number
  status: 'success' | 'partial'
  startedAt: string
  downloadUrl?: string
  columnMode?: ColumnMode
  splitScheme?: string
  storageBackend?: 'sqlite' | 'redis' | string
  storageHost?: string
  storagePort?: number | null
  storageDb?: number | null
  storageLabel?: string
}

export interface ValidationRule {
  ruleId: string
  pattern: string
  levels: string[]
}

export interface ColumnSettingItem {
  key: string
  label: string
  visible: boolean
  fixed?: boolean
  description?: string
}

export interface SelectOption {
  label: string
  value: string
}

export interface TableColumn {
  key: string
  label: string
  width?: string
  className?: string
}

export interface DetailStats {
  total: string
  success: string
  failed: string
  successRate: string
}
