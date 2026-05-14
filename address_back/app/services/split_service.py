from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any, Callable

import pandas as pd

from app.core.config import DEFAULT_SAMPLE_SIZE, RESULT_DIR
from app.schemas.address import ColumnMode, SplitJobDetail, SplitJobStatus
from app.services.constants import (
    LEVEL8_FIELDS,
    LEVEL11_FIELDS,
    RAW_FIELDS,
)
from app.services.model_service import get_model_service
from app.services.validation_rule_service import validate_levels
from app.services.job_store import delete_job as delete_stored_job
from app.services.job_store import get_cached_job as get_cached_stored_job
from app.services.job_store import get_job as get_stored_job
from app.services.job_store import list_jobs as list_stored_jobs
from app.services.job_store import read_cached_rows
from app.services.job_store import save_job
from app.services.task_control import clear_cancel, is_cancelled

ProgressCallback = Callable[[dict[str, Any]], None]
CancelCheck = Callable[[], bool]


def _normalize_excel_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _resolve_address_column(df: pd.DataFrame) -> str:
    columns = [str(column) for column in df.columns]
    if "address" in columns:
        return "address"
    if "地址" in columns:
        return "地址"
    raise ValueError("表格不符合规范，需要添加表头 address/地址")


def _read_excel(path: Path, sample_size: int) -> tuple[pd.DataFrame, int, str]:
    df = pd.read_excel(path)
    address_column = _resolve_address_column(df)
    df = df[df[address_column].notna()]
    total_rows = len(df)

    if sample_size > total_rows:
        raise ValueError(f"处理条数不能大于 Excel 地址总量 {total_rows}")

    if total_rows > sample_size:
        df = df.sample(n=sample_size, random_state=20260427).sort_index()

    return df.reset_index(drop=True), total_rows, address_column


def inspect_excel_file(path: Path) -> dict[str, Any]:
    df = pd.read_excel(path)
    address_column = _resolve_address_column(df)

    address_rows = int(df[address_column].notna().sum())
    return {
        "total_rows": len(df),
        "address_rows": address_rows,
        "address_column": address_column,
        "columns": [str(column) for column in df.columns],
    }


def _raw_to_levels(raw: dict[str, str]) -> dict[str, str]:
    return {
        "level_1": raw.get("prov", ""),
        "level_2": raw.get("city", ""),
        "level_3": raw.get("district", ""),
        "level_4": raw.get("town", ""),
        "level_5": raw.get("road", ""),
        "level_6": raw.get("roadno", ""),
        "level_7": raw.get("poi") or raw.get("community") or raw.get("devzone") or raw.get("subpoi", ""),
        "level_8": raw.get("houseno", ""),
        "level_9": raw.get("cellno", ""),
        "level_10": raw.get("floorno", ""),
        "level_11": raw.get("roomno", ""),
    }


def _resolve_raw_fields(column_mode: ColumnMode, raw_fields: list[str] | None) -> list[str]:
    if column_mode != ColumnMode.raw:
        return []

    if not raw_fields:
        return RAW_FIELDS

    invalid_fields = [field for field in raw_fields if field not in RAW_FIELDS]
    if invalid_fields:
        raise ValueError(f"原始字段不支持：{', '.join(invalid_fields)}")

    return raw_fields


def _generated_columns_for_mode(column_mode: ColumnMode, raw_fields: list[str] | None) -> list[str]:
    if column_mode == ColumnMode.level8:
        split_fields = LEVEL8_FIELDS
    elif column_mode == ColumnMode.level11:
        split_fields = LEVEL11_FIELDS
    else:
        split_fields = _resolve_raw_fields(column_mode, raw_fields)

    return ["new_address", *[f"new_{field}" for field in split_fields], "new_validation_status", "new_violated_rule_ids"]


def _result_columns_for_mode(
    original_columns: list[str],
    column_mode: ColumnMode,
    raw_fields: list[str] | None,
) -> list[str]:
    return [*original_columns, *_generated_columns_for_mode(column_mode, raw_fields)]


def split_dataframe(
    df: pd.DataFrame,
    total_rows: int,
    column_mode: ColumnMode,
    raw_fields: list[str] | None = None,
    task_name: str = "",
    source: str = "",
    cache_key: str | None = None,
    address_column: str = "address",
    job_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> tuple[str, pd.DataFrame, SplitJobDetail]:
    job_id = job_id or uuid.uuid4().hex
    resolved_raw_fields = _resolve_raw_fields(column_mode, raw_fields)
    model = get_model_service()

    rows: list[dict[str, Any]] = []
    original_columns = list(df.columns)
    process_total = len(df)
    started_at = monotonic()

    def emit_progress(phase: str, processed_rows: int, message: str = "") -> None:
        if progress_callback is None:
            return
        progress_callback(
            {
                "phase": phase,
                "processed_rows": processed_rows,
                "total_rows": process_total,
                "elapsed_seconds": int(monotonic() - started_at),
                "message": message,
            }
        )

    cancelled = False
    emit_progress("splitting", 0, "开始地址识别与拆分")
    for index, record in enumerate(df.itertuples(index=False), start=1):
        if should_cancel and should_cancel():
            cancelled = True
            break

        record_data = dict(zip(original_columns, record, strict=False))
        address = _normalize_excel_value(record_data[address_column])
        raw = model.parse(address)
        levels = _raw_to_levels(raw)
        validation_status, violated_rule_ids = validate_levels(column_mode, levels)

        row: dict[str, Any] = {column: _normalize_excel_value(record_data[column]) for column in original_columns}
        row["new_address"] = address
        if column_mode == ColumnMode.level8:
            row.update({f"new_{field}": levels.get(field, "") for field in LEVEL8_FIELDS})
        elif column_mode == ColumnMode.level11:
            row.update({f"new_{field}": levels.get(field, "") for field in LEVEL11_FIELDS})
        else:
            row.update({f"new_{field}": raw.get(field, "") for field in resolved_raw_fields})

        row["new_validation_status"] = validation_status
        row["new_violated_rule_ids"] = violated_rule_ids
        rows.append(row)
        emit_progress("splitting", index, "地址识别与拆分中")

    emit_progress("summary", len(rows), "正在汇总当前结果" if cancelled else "正在汇总结果")
    result_df = pd.DataFrame(rows, columns=_result_columns_for_mode(original_columns, column_mode, resolved_raw_fields))
    result_file = RESULT_DIR / f"{job_id}.xlsx"
    result_df.to_excel(result_file, index=False)

    detail = SplitJobDetail(
        job_id=job_id,
        status=SplitJobStatus.cancelled if cancelled else SplitJobStatus.completed,
        column_mode=column_mode,
        total_rows=total_rows,
        processed_rows=len(result_df),
        columns=list(result_df.columns),
        task_name=task_name or f"地址拆分_{job_id[:8]}",
        source=source or "手动输入",
        success_rows=len(result_df),
        failed_rows=0,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        raw_fields=resolved_raw_fields if column_mode == ColumnMode.raw else None,
        result_file=str(result_file),
        cache_key=cache_key,
    )
    save_job(detail, result_df.fillna("").to_dict(orient="records"))
    emit_progress("cancelled" if cancelled else "done", len(result_df), "已结束拆分，已保留当前结果" if cancelled else "拆分完成")
    clear_cancel(job_id)
    return job_id, result_df, detail


def split_excel_file(
    path: Path,
    column_mode: ColumnMode,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    raw_fields: list[str] | None = None,
    task_name: str = "",
    cache_key: str | None = None,
    job_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> tuple[str, pd.DataFrame, SplitJobDetail]:
    if progress_callback is not None:
        progress_callback(
            {
                "phase": "parsing",
                "processed_rows": 0,
                "total_rows": sample_size,
                "elapsed_seconds": 0,
                "message": "正在解析 Excel 文件",
            }
        )
    df, total_rows, address_column = _read_excel(path, sample_size)
    return split_dataframe(
        df,
        total_rows,
        column_mode,
        raw_fields,
        task_name=task_name or path.name,
        source="Excel上传",
        cache_key=cache_key,
        address_column=address_column,
        job_id=job_id,
        progress_callback=progress_callback,
        should_cancel=should_cancel,
    )


def split_addresses(
    addresses: list[str],
    column_mode: ColumnMode,
    raw_fields: list[str] | None = None,
    job_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> tuple[str, pd.DataFrame, SplitJobDetail]:
    df = pd.DataFrame({"address": addresses})
    return split_dataframe(
        df,
        len(df),
        column_mode,
        raw_fields,
        task_name=f"手动输入_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        source="手动输入",
        job_id=job_id,
        progress_callback=progress_callback,
        should_cancel=should_cancel,
    )


def should_cancel_job(job_id: str) -> bool:
    return is_cancelled(job_id)


def get_job(job_id: str) -> SplitJobDetail | None:
    return get_stored_job(job_id)


def get_cached_job(cache_key: str) -> SplitJobDetail | None:
    return get_cached_stored_job(cache_key)


def list_jobs() -> list[SplitJobDetail]:
    return list_stored_jobs()


def delete_job(job_id: str) -> SplitJobDetail | None:
    job = delete_stored_job(job_id)
    if job and job.result_file:
        path = Path(job.result_file)
        if path.exists():
            path.unlink()
    return job


def read_result_rows(job: SplitJobDetail, page: int = 1, page_size: int = 200) -> tuple[list[dict[str, Any]], int]:
    cached_rows, cached_total = read_cached_rows(job.job_id, page, page_size)
    if cached_total:
        return cached_rows, cached_total

    if not job.result_file:
        return [], 0

    path = Path(job.result_file)
    if not path.exists():
        return [], 0

    df = pd.read_excel(path).fillna("")
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return df.iloc[start:end].to_dict(orient="records"), len(df)
