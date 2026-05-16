from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class AddressFillJobStatus(StrEnum):
    completed = "completed"
    failed = "failed"
    running = "running"
    cancelled = "cancelled"


class AddressFillInputInspectResponse(BaseModel):
    filename: str
    totalRows: int
    columns: list[str]
    columnMode: str
    accepted: bool
    message: str


class AddressFillJobDetail(BaseModel):
    job_id: str
    client_id: str
    status: AddressFillJobStatus
    task_name: str
    input_source: str
    source_count: int = 0
    total_rows: int = 0
    success_rows: int = 0
    failed_rows: int = 0
    columns: list[str] = []
    column_mode: str = ""
    result_file: str | None = None
    created_at: str = ""
    updated_at: str = ""
    error: str | None = None


class AddressFillJobResponse(BaseModel):
    job_id: str
    status: AddressFillJobStatus
    total_rows: int
    processed_rows: int
    columns: list[str]
    preview: list[dict[str, Any]]
    download_url: str


class AddressFillRecordResponse(BaseModel):
    id: str
    taskName: str
    inputSource: str
    sourceCount: int
    total: int
    success: int
    failed: int
    status: str
    startedAt: str
    columnMode: str
    downloadUrl: str


class AddressFillWorkflowEvent(BaseModel):
    event_id: str
    job_id: str
    phase: str
    event_type: str
    title: str
    summary: str
    status: str
    sequence: int
    created_at: str
    payload: dict[str, Any] = {}


class AddressFillLatestWorkflowResponse(BaseModel):
    job: AddressFillJobDetail | None = None
    events: list[AddressFillWorkflowEvent] = []


class AddressFillResultDetailResponse(BaseModel):
    stats: dict[str, str]
    rows: list[dict[str, Any]]
    columns: list[str]
    columnMode: str
    failedRows: list[dict[str, Any]]
    downloadUrl: str
    page: int = 1
    pageSize: int = 200
    totalRows: int = 0


class AddressFillSplitResultResponse(BaseModel):
    id: str
    taskName: str
    total: int
    columnMode: str
    splitScheme: str
    startedAt: str


class FilledLevelEvidence(BaseModel):
    level: str
    value: str
    confidence: float = 0
    source_ids: list[str] = []
    source_urls: list[str] = []
    source_files: list[str] = []
    reason: str = ""


class AddressFillItem(BaseModel):
    row_id: str
    new_level_1: str = ""
    new_level_2: str = ""
    new_level_3: str = ""
    new_level_4: str = ""
    new_level_5: str = ""
    new_level_6: str = ""
    new_level_7: str = ""
    evidence: list[FilledLevelEvidence] = []
    unresolved_levels: list[str] = []


class AddressFillSessionOutput(BaseModel):
    items: list[AddressFillItem] = []
