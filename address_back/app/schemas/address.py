from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ColumnMode(StrEnum):
    level8 = "level8"
    level11 = "level11"
    raw = "raw"


class SplitJobStatus(StrEnum):
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class SplitJobResponse(BaseModel):
    job_id: str
    status: SplitJobStatus
    column_mode: ColumnMode
    total_rows: int
    processed_rows: int
    columns: list[str]
    preview: list[dict[str, Any]]
    download_url: str


class ExcelInspectResponse(BaseModel):
    filename: str
    total_rows: int
    address_rows: int
    address_column: str
    columns: list[str]


class SplitJobDetail(BaseModel):
    job_id: str
    status: SplitJobStatus
    column_mode: ColumnMode
    total_rows: int
    processed_rows: int
    columns: list[str]
    task_name: str = ""
    source: str = ""
    success_rows: int = 0
    failed_rows: int = 0
    created_at: str = ""
    raw_fields: list[str] | None = None
    result_file: str | None = None
    cache_key: str | None = None
    error: str | None = None
    storage_backend: str = "sqlite"
    storage_host: str = ""
    storage_port: int | None = None
    storage_db: int | None = None


class SplitRecordResponse(BaseModel):
    id: str
    taskName: str
    source: str
    total: int
    success: int
    failed: int
    status: str
    startedAt: str
    columnMode: ColumnMode
    splitScheme: str
    downloadUrl: str
    storageBackend: str
    storageHost: str = ""
    storagePort: int | None = None
    storageDb: int | None = None
    storageLabel: str


class SplitResultDetailResponse(BaseModel):
    stats: dict[str, str]
    rows: list[dict[str, Any]]
    columns: list[str]
    columnMode: ColumnMode
    failedRows: list[dict[str, Any]]
    downloadUrl: str
    page: int = 1
    pageSize: int = 200
    totalRows: int = 0


class ColumnSchemaResponse(BaseModel):
    raw_fields: list[str]
    level8_fields: list[str]
    level11_fields: list[str]
    level_descriptions: dict[str, str]
    validation_level_options: list[str]


class AddressSplitRequest(BaseModel):
    addresses: list[str] = Field(min_length=1)
    column_mode: ColumnMode = ColumnMode.level11
    raw_fields: list[str] | None = None
    client_job_id: str | None = None


VALIDATION_LEVELS = {f"level_{index}" for index in range(1, 12)}


class ValidationRuleResponse(BaseModel):
    ruleId: str
    pattern: str
    levels: list[str]


class ValidationRulePayload(BaseModel):
    ruleId: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    levels: list[str] = Field(min_length=1)

    @field_validator("levels")
    @classmethod
    def validate_levels(cls, value: list[str]) -> list[str]:
        normalized = []
        for item in value:
            level = item.strip()
            if level not in VALIDATION_LEVELS:
                raise ValueError("校验层级仅支持 level_1 到 level_11")
            if level not in normalized:
                normalized.append(level)
        return normalized


class ValidationRuleImportResponse(BaseModel):
    imported: int
    rules: list[ValidationRuleResponse]


class RedisConfigPayload(BaseModel):
    id: str | None = None
    mode: str = "local"
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0)
    password: str = ""


class RedisConfigResponse(RedisConfigPayload):
    id: str = ""
    active: bool = False
    updatedAt: str = ""


class RedisConfigListResponse(BaseModel):
    activeId: str = ""
    configs: list[RedisConfigResponse]


class RedisConfigActivateResponse(BaseModel):
    activeId: str
    config: RedisConfigResponse


class RedisTestResponse(BaseModel):
    ok: bool
    message: str


class RedisStatusResponse(BaseModel):
    available: bool
    mode: str
    host: str
    port: int
    db: int
    message: str


class ModelConfigPayload(BaseModel):
    id: str | None = None
    provider: str = Field(min_length=1)
    baseUrl: str = Field(min_length=1)
    apiKey: str = Field(min_length=1)
    model: str = Field(min_length=1)

    @field_validator("provider", "baseUrl", "apiKey", "model")
    @classmethod
    def strip_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("字段不能为空")
        return normalized


class ModelConfigResponse(ModelConfigPayload):
    id: str
    active: bool = False
    updatedAt: str = ""


class ModelConfigListResponse(BaseModel):
    activeId: str = ""
    models: list[ModelConfigResponse]


class ModelConfigTestResponse(BaseModel):
    ok: bool
    message: str


class ModelConfigActivateResponse(BaseModel):
    activeId: str
    model: ModelConfigResponse
