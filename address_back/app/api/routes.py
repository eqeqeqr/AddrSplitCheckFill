from pathlib import Path
import asyncio
import json
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.core.config import DEFAULT_SAMPLE_SIZE, UPLOAD_DIR
from app.schemas.address import (
    AddressSplitRequest,
    ColumnMode,
    ColumnSchemaResponse,
    ExcelInspectResponse,
    RedisConfigPayload,
    RedisConfigResponse,
    RedisStatusResponse,
    RedisTestResponse,
    SplitJobResponse,
    SplitRecordResponse,
    SplitResultDetailResponse,
    ValidationRuleImportResponse,
    ValidationRulePayload,
    ValidationRuleResponse,
)
from app.services.constants import (
    LEVEL8_FIELDS,
    LEVEL11_FIELDS,
    LEVEL_DESCRIPTIONS,
    RAW_FIELDS,
    VALIDATION_LEVEL_OPTIONS,
)
from app.services.environment_config import get_redis_config, save_redis_config
from app.services.redis_store import get_redis_status, reset_redis_connection, test_connection
from app.services.split_service import (
    get_cached_job,
    delete_job,
    get_job,
    inspect_excel_file,
    list_jobs,
    read_result_rows,
    should_cancel_job,
    split_addresses,
    split_excel_file,
)
from app.services.validation_rule_service import (
    delete_validation_rule,
    import_validation_rules,
    list_validation_rules,
    update_validation_rule,
    upsert_validation_rule,
    validation_rules_fingerprint,
)
from app.services.job_store import build_cache_key
from app.services.progress_ws import progress_manager
from app.services.task_control import request_cancel

router = APIRouter(prefix="/api")


def _parse_raw_fields(raw_fields: str | None) -> list[str] | None:
    if not raw_fields:
        return None

    try:
        value = json.loads(raw_fields)
    except json.JSONDecodeError:
        value = [item.strip() for item in raw_fields.split(",") if item.strip()]

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise HTTPException(status_code=400, detail="raw_fields 必须是字符串数组")

    return value


def _split_scheme(column_mode: ColumnMode, raw_fields: list[str] | None = None) -> str:
    if column_mode == ColumnMode.level8:
        return "8级标准列"
    if column_mode == ColumnMode.level11:
        return "11级标准列"
    if raw_fields:
        return f"原始字段自定义({','.join(raw_fields)})"
    return "原始字段自定义"


def _cache_scheme(column_mode: ColumnMode, raw_fields: list[str] | None = None) -> str:
    return f"{_split_scheme(column_mode, raw_fields)}:rules:{validation_rules_fingerprint()}"


def _storage_label(job) -> str:
    if job.storage_backend == "redis":
        return f"Redis {job.storage_host}:{job.storage_port} DB {job.storage_db}"
    return "SQLite"


def _publish_from_worker(loop: asyncio.AbstractEventLoop, job_id: str):
    def publish(payload: dict) -> None:
        asyncio.run_coroutine_threadsafe(progress_manager.publish(job_id, payload), loop)

    return publish


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.websocket("/ws/splits/{job_id}")
async def split_progress_ws(websocket: WebSocket, job_id: str) -> None:
    await progress_manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await progress_manager.disconnect(job_id, websocket)


@router.get("/schemas", response_model=ColumnSchemaResponse)
def get_schemas() -> ColumnSchemaResponse:
    return ColumnSchemaResponse(
        raw_fields=RAW_FIELDS,
        level8_fields=LEVEL8_FIELDS,
        level11_fields=LEVEL11_FIELDS,
        level_descriptions=LEVEL_DESCRIPTIONS,
        validation_level_options=VALIDATION_LEVEL_OPTIONS,
    )


@router.get("/environment/redis", response_model=RedisConfigResponse)
def read_redis_environment() -> RedisConfigResponse:
    return get_redis_config()


@router.get("/environment/redis/status", response_model=RedisStatusResponse)
def read_redis_status() -> RedisStatusResponse:
    return get_redis_status()


@router.put("/environment/redis", response_model=RedisConfigResponse)
def update_redis_environment(payload: RedisConfigPayload) -> RedisConfigResponse:
    result = save_redis_config(payload)
    reset_redis_connection()
    return result


@router.post("/environment/redis/disconnect", response_model=RedisConfigResponse)
def disconnect_redis_environment() -> RedisConfigResponse:
    result = save_redis_config(
        RedisConfigPayload(
            mode="disabled",
            host="127.0.0.1",
            port=6379,
            db=0,
            password="",
        )
    )
    reset_redis_connection()
    return result


@router.post("/environment/redis/test", response_model=RedisTestResponse)
def test_redis_environment(payload: RedisConfigPayload) -> RedisTestResponse:
    ok, message = test_connection(payload.model_dump())
    return RedisTestResponse(ok=ok, message=message)


@router.post("/excels/inspect", response_model=ExcelInspectResponse)
async def inspect_excel(file: UploadFile = File(...)) -> ExcelInspectResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 文件")

    upload_path = UPLOAD_DIR / f"inspect_{Path(file.filename or 'upload.xlsx').stem}_{id(file)}{suffix}"
    upload_path.write_bytes(await file.read())

    try:
        result = inspect_excel_file(upload_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Excel 检测失败：{exc}") from exc
    finally:
        if upload_path.exists():
            upload_path.unlink()

    return ExcelInspectResponse(
        filename=file.filename or upload_path.name,
        total_rows=result["total_rows"],
        address_rows=result["address_rows"],
        address_column=result["address_column"],
        columns=result["columns"],
    )


@router.get("/validation-rules", response_model=list[ValidationRuleResponse])
def get_validation_rules() -> list[ValidationRuleResponse]:
    return list_validation_rules()


@router.post("/validation-rules", response_model=ValidationRuleResponse)
def create_validation_rule(payload: ValidationRulePayload) -> ValidationRuleResponse:
    try:
        return upsert_validation_rule(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/validation-rules/{rule_id}", response_model=ValidationRuleResponse)
def update_rule(rule_id: str, payload: ValidationRulePayload) -> ValidationRuleResponse:
    try:
        rule = update_validation_rule(rule_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if rule is None:
        raise HTTPException(status_code=404, detail="校验规则不存在")
    return rule


@router.delete("/validation-rules/{rule_id}")
def delete_rule(rule_id: str) -> dict[str, bool]:
    deleted = delete_validation_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="校验规则不存在")
    return {"deleted": True}


@router.post("/validation-rules/import", response_model=ValidationRuleImportResponse)
async def import_rules(file: UploadFile = File(...)) -> ValidationRuleImportResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 文件")

    upload_path = UPLOAD_DIR / f"validation_rules_{Path(file.filename or 'rules.xlsx').stem}_{id(file)}{suffix}"
    upload_path.write_bytes(await file.read())
    try:
        rules = import_validation_rules(upload_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"校验规则导入失败：{exc}") from exc
    finally:
        if upload_path.exists():
            upload_path.unlink()

    return ValidationRuleImportResponse(imported=len(rules), rules=rules)


@router.post("/splits", response_model=SplitJobResponse)
async def create_split(
    file: UploadFile = File(...),
    column_mode: ColumnMode = Form(ColumnMode.level11),
    sample_size: int = Form(DEFAULT_SAMPLE_SIZE),
    raw_fields: str | None = Form(None),
    client_job_id: str | None = Form(None),
) -> SplitJobResponse:
    if sample_size <= 0:
        raise HTTPException(status_code=400, detail="sample_size 必须大于 0")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 文件")

    filename = file.filename or "upload.xlsx"
    parsed_raw_fields = _parse_raw_fields(raw_fields)
    job_id = client_job_id or uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    cache_key = build_cache_key(filename, sample_size, _cache_scheme(column_mode, parsed_raw_fields))
    cached_job = get_cached_job(cache_key)
    if cached_job is not None:
        preview_rows, _ = read_result_rows(cached_job, page=1, page_size=20)
        await progress_manager.publish(
            job_id,
            {
                "phase": "done",
                "processed_rows": cached_job.processed_rows,
                "total_rows": max(cached_job.processed_rows, 1),
                "elapsed_seconds": 0,
                "message": "命中缓存，已加载拆分结果",
                "cached_job_id": cached_job.job_id,
            },
        )
        return SplitJobResponse(
            job_id=cached_job.job_id,
            status=cached_job.status,
            column_mode=cached_job.column_mode,
            total_rows=cached_job.total_rows,
            processed_rows=cached_job.processed_rows,
            columns=cached_job.columns,
            preview=preview_rows,
            download_url=f"/api/splits/{cached_job.job_id}/download",
        )

    upload_path = UPLOAD_DIR / f"{Path(file.filename or 'upload.xlsx').stem}_{id(file)}{suffix}"
    upload_path.write_bytes(await file.read())

    try:
        result_job_id, result_df, detail = await asyncio.to_thread(
            split_excel_file,
            upload_path,
            column_mode,
            sample_size,
            parsed_raw_fields,
            filename,
            cache_key,
            job_id,
            _publish_from_worker(loop, job_id),
            lambda: should_cancel_job(job_id),
        )
    except ValueError as exc:
        await progress_manager.publish(job_id, {"phase": "error", "processed_rows": 0, "total_rows": sample_size, "elapsed_seconds": 0, "message": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await progress_manager.publish(job_id, {"phase": "error", "processed_rows": 0, "total_rows": sample_size, "elapsed_seconds": 0, "message": f"地址拆分失败：{exc}"})
        raise HTTPException(status_code=500, detail=f"地址拆分失败：{exc}") from exc

    return SplitJobResponse(
        job_id=result_job_id,
        status=detail.status,
        column_mode=detail.column_mode,
        total_rows=detail.total_rows,
        processed_rows=detail.processed_rows,
        columns=detail.columns,
        preview=result_df.head(20).fillna("").to_dict(orient="records"),
        download_url=f"/api/splits/{job_id}/download",
    )


@router.get("/splits", response_model=list[SplitRecordResponse])
def list_splits() -> list[SplitRecordResponse]:
    records: list[SplitRecordResponse] = []
    for job in list_jobs():
        records.append(
            SplitRecordResponse(
                id=job.job_id,
                taskName=job.task_name or job.job_id,
                source=job.source,
                total=job.total_rows,
                success=job.success_rows,
                failed=job.failed_rows,
                status="success" if job.status.value == "completed" else "partial",
                startedAt=job.created_at,
                columnMode=job.column_mode,
                splitScheme=_split_scheme(job.column_mode, job.raw_fields),
                downloadUrl=f"/api/splits/{job.job_id}/download",
                storageBackend=job.storage_backend,
                storageHost=job.storage_host,
                storagePort=job.storage_port,
                storageDb=job.storage_db,
                storageLabel=_storage_label(job),
            )
        )

    return records


@router.post("/splits/text", response_model=SplitJobResponse)
async def create_text_split(payload: AddressSplitRequest) -> SplitJobResponse:
    job_id = payload.client_job_id or uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    try:
        job_id, result_df, detail = await asyncio.to_thread(
            split_addresses,
            payload.addresses,
            payload.column_mode,
            payload.raw_fields,
            job_id,
            _publish_from_worker(loop, job_id),
            lambda: should_cancel_job(job_id),
        )
    except ValueError as exc:
        await progress_manager.publish(job_id, {"phase": "error", "processed_rows": 0, "total_rows": len(payload.addresses), "elapsed_seconds": 0, "message": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await progress_manager.publish(job_id, {"phase": "error", "processed_rows": 0, "total_rows": len(payload.addresses), "elapsed_seconds": 0, "message": f"地址拆分失败：{exc}"})
        raise HTTPException(status_code=500, detail=f"地址拆分失败：{exc}") from exc

    return SplitJobResponse(
        job_id=job_id,
        status=detail.status,
        column_mode=detail.column_mode,
        total_rows=detail.total_rows,
        processed_rows=detail.processed_rows,
        columns=detail.columns,
        preview=result_df.head(20).fillna("").to_dict(orient="records"),
        download_url=f"/api/splits/{job_id}/download",
    )


@router.get("/splits/{job_id}")
def get_split(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.post("/splits/{job_id}/cancel")
def cancel_split(job_id: str) -> dict[str, bool]:
    request_cancel(job_id)
    return {"cancelled": True}


@router.get("/splits/{job_id}/result", response_model=SplitResultDetailResponse)
def get_split_result(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=1000),
) -> SplitResultDetailResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    rows, row_total = read_result_rows(job, page=page, page_size=page_size)
    total = job.total_rows
    success = job.success_rows
    failed = job.failed_rows
    processed = job.processed_rows
    success_rate = f"{(success / processed * 100):.2f}%" if processed else "0.00%"

    return SplitResultDetailResponse(
        stats={
            "total": f"{total:,}",
            "success": f"{success:,}",
            "failed": f"{failed:,}",
            "successRate": success_rate,
        },
        rows=rows[:200],
        columns=job.columns,
        columnMode=job.column_mode,
        failedRows=[],
        downloadUrl=f"/api/splits/{job.job_id}/download",
        page=page,
        pageSize=page_size,
        totalRows=row_total,
    )


@router.get("/splits/{job_id}/download")
def download_split(job_id: str) -> FileResponse:
    job = get_job(job_id)
    if job is None or not job.result_file:
        raise HTTPException(status_code=404, detail="结果文件不存在")

    result_file = Path(job.result_file)
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        result_file,
        filename=f"address_split_{job_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.delete("/splits/{job_id}")
def delete_split(job_id: str) -> dict[str, bool]:
    deleted = delete_job(job_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"deleted": True}
