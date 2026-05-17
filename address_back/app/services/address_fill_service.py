from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any, Callable

import pandas as pd

from app.core.config import RESULT_DIR, UPLOAD_DIR
from app.schemas.address import ColumnMode, SplitJobDetail
from app.schemas.address_fill import (
    AddressFillInputInspectResponse,
    AddressFillJobDetail,
    AddressFillJobStatus,
    AddressFillRecordResponse,
    AddressFillSplitResultResponse,
    AddressFillWorkflowEvent,
)
from app.services.constants import LEVEL8_FIELDS, LEVEL11_FIELDS
from app.services.db import get_connection, init_db
from app.services.address_fill_agent import build_address_fill_question, run_address_fill_agent_single
from app.services.document_parsers import SUPPORTED_EXTENSIONS, ParsedDocumentChunk, parse_document
from app.services.split_service import get_job as get_split_job
from app.services.split_service import list_jobs as list_split_jobs
from app.services.task_control import is_cancelled, request_cancel, clear_cancel

FILL_LEVEL_FIELDS = [f"new_level_{index}" for index in range(1, 12)]
REQUIRED_BASE_FIELDS = ["new_address"]
OPTIONAL_FIELDS = ["new_validation_status", "new_violated_rule_ids"]
RESULT_EXTRA_FIELDS = ["desc", "new_fill_address"]
MAX_FILL_ROWS = 200
SourceUpload = tuple[str, bytes]
LEGACY_WORKFLOW_EVENT_TITLES = {"模型接口降级", "搜索能力降级"}
FillProgressCallback = Callable[[dict[str, Any]], None]
_LEVEL_NAMES = {
    "new_level_1": "省份",
    "new_level_2": "地市",
    "new_level_3": "区县",
    "new_level_4": "乡镇/街道",
    "new_level_5": "路/巷/街",
    "new_level_6": "门牌号",
    "new_level_7": "建筑物",
}


def should_cancel_fill_job(job_id: str) -> bool:
    return is_cancelled(job_id)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_row_state(
    job_id: str,
    row_id: str,
    address: str,
    status: str = "waiting",
    step1_status: str = "waiting",
    step2_status: str = "waiting",
    step3_status: str = "waiting",
    step4_status: str = "waiting",
) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO address_fill_row_states
               (job_id, row_id, address, status, step1_status, step2_status, step3_status, step4_status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, row_id, address, status, step1_status, step2_status, step3_status, step4_status, _now()),
        )


def get_row_states(job_id: str) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM address_fill_row_states WHERE job_id = ? ORDER BY CAST(row_id AS INTEGER)",
            (job_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_row_state(job_id: str, row_id: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM address_fill_row_states WHERE job_id = ? AND row_id = ?",
            (job_id, row_id),
        ).fetchone()
    return dict(row) if row else None


def cleanup_row_states(job_id: str) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM address_fill_row_states WHERE job_id = ?", (job_id,))


def _emit_step_state_update(
    progress_callback: FillProgressCallback | None,
    job_id: str,
    row_id: str,
    address: str,
    status: str,
    step1_status: str,
    step2_status: str,
    step3_status: str,
    step4_status: str,
) -> None:
    if progress_callback is None:
        return
    progress_callback({
        "event_type": "step_state_update",
        "job_id": job_id,
        "row_id": row_id,
        "address": address,
        "status": status,
        "step1_status": step1_status,
        "step2_status": step2_status,
        "step3_status": step3_status,
        "step4_status": step4_status,
    })


def _normalize_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _read_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path).fillna("")


def _detect_column_mode(columns: list[str]) -> str:
    column_set = set(columns)
    if not set(REQUIRED_BASE_FIELDS).issubset(column_set):
        raise ValueError("上传文件必须包含 new_address 字段")

    level8 = {f"new_{field}" for field in LEVEL8_FIELDS}
    level11 = {f"new_{field}" for field in LEVEL11_FIELDS}
    if level11.issubset(column_set):
        return "level11"
    if level8.issubset(column_set):
        return "level8"
    raise ValueError("仅支持 8 级或 11 级拆分结果字段结构")


def inspect_address_fill_input(path: Path, filename: str) -> AddressFillInputInspectResponse:
    df = _read_excel(path)
    columns = [str(column) for column in df.columns]
    try:
        column_mode = _detect_column_mode(columns)
    except ValueError as exc:
        return AddressFillInputInspectResponse(
            filename=filename,
            totalRows=len(df),
            columns=columns,
            columnMode="",
            accepted=False,
            message=str(exc),
        )

    return AddressFillInputInspectResponse(
        filename=filename,
        totalRows=len(df),
        columns=columns,
        columnMode=column_mode,
        accepted=True,
        message="字段结构检测通过",
    )


def _output_columns(input_columns: list[str], column_mode: str) -> list[str]:
    base_columns = [*REQUIRED_BASE_FIELDS, *FILL_LEVEL_FIELDS]
    if column_mode == "level8":
        base_columns = [*REQUIRED_BASE_FIELDS, *FILL_LEVEL_FIELDS[:8], *FILL_LEVEL_FIELDS[8:]]

    columns = [column for column in base_columns if column not in OPTIONAL_FIELDS]
    for optional in OPTIONAL_FIELDS:
        if optional in input_columns:
            columns.append(optional)
    columns.extend(RESULT_EXTRA_FIELDS)
    return columns


def _missing_level_desc(row: dict[str, str]) -> str:
    missing = [f"{index}级" for index in range(1, 8) if not row.get(f"new_level_{index}")]
    if not missing:
        return row.get("desc", "")
    return f"无法补全--补全数据来源不足或网上无法搜索到：{'；'.join(missing)}"


def _fill_address(row: dict[str, str]) -> str:
    return "".join(row.get(field, "") for field in FILL_LEVEL_FIELDS if row.get(field))


def _agent_values_by_row(agent_items: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    return agent_items


def _build_result(df: pd.DataFrame, column_mode: str, agent_output: Any | None = None) -> pd.DataFrame:
    input_columns = [str(column) for column in df.columns]
    rows: list[dict[str, str]] = []
    agent_rows = _agent_values_by_row(agent_output)
    for row_index, record in enumerate(df.to_dict(orient="records"), start=1):
        row = {column: _normalize_value(record.get(column, "")) for column in _output_columns(input_columns, column_mode)}
        row["new_address"] = _normalize_value(record.get("new_address", ""))
        for field in FILL_LEVEL_FIELDS:
            row[field] = _normalize_value(record.get(field, ""))
        agent_values = agent_rows.get(str(row_index), {})
        for field in FILL_LEVEL_FIELDS[:7]:
            if not row[field] and agent_values.get(field):
                row[field] = agent_values[field]
        for optional in OPTIONAL_FIELDS:
            if optional in input_columns:
                row[optional] = _normalize_value(record.get(optional, ""))
        row["desc"] = _missing_level_desc(row)
        row["new_fill_address"] = _fill_address(row)
        rows.append(row)

    return pd.DataFrame(rows, columns=_output_columns(input_columns, column_mode))


def _save_job(job: AddressFillJobDetail) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO address_fill_jobs (job_id, client_id, payload, created_at) VALUES (?, ?, ?, ?)",
            (
                job.job_id,
                job.client_id,
                json.dumps(job.model_dump(mode="json"), ensure_ascii=False),
                job.created_at,
            ),
        )


def _update_job_status(job_id: str, status: AddressFillJobStatus, error: str | None = None) -> None:
    job = get_address_fill_job(job_id)
    if job is None:
        return
    job.status = status
    job.updated_at = _now()
    job.error = error
    _save_job(job)


def _save_event(event: AddressFillWorkflowEvent) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO address_fill_events (event_id, job_id, payload, sequence, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.job_id,
                json.dumps(event.model_dump(mode="json"), ensure_ascii=False),
                event.sequence,
                event.created_at,
            ),
        )


def _event(job_id: str, sequence: int, phase: str, title: str, summary: str, status: str = "done", payload: dict[str, Any] | None = None, event_id: str | None = None) -> AddressFillWorkflowEvent:
    return AddressFillWorkflowEvent(
        event_id=event_id or f"{job_id}-{sequence:04d}",
        job_id=job_id,
        phase=phase,
        event_type="stage",
        title=title,
        summary=summary,
        status=status,
        sequence=sequence,
        created_at=_now(),
        payload=payload or {},
    )


def _source_file_from_split(split_job: SplitJobDetail) -> Path:
    if not split_job.result_file:
        raise ValueError("所选拆分记录没有可用结果文件")
    path = Path(split_job.result_file)
    if not path.exists():
        raise ValueError("所选拆分记录结果文件不存在")
    return path


def _save_and_parse_sources(job_id: str, source_files: list[SourceUpload], start_sequence: int) -> tuple[list[str], int, list[ParsedDocumentChunk]]:
    source_names: list[str] = []
    all_chunks: list[ParsedDocumentChunk] = []
    sequence = start_sequence
    parsed_count = 0
    for index, (filename, content) in enumerate(source_files, start=1):
        safe_name = Path(filename or f"source_{index}").name
        source_names.append(safe_name)
        suffix = Path(safe_name).suffix.lower()
        source_id = f"{job_id}-source-{index}"

        if suffix not in SUPPORTED_EXTENSIONS:
            _save_event(
                _event(
                    job_id,
                    sequence,
                    "sources",
                    "资料解析失败",
                    f"{safe_name} 格式不支持",
                    status="failed",
                    payload={"source_id": source_id, "filename": safe_name},
                )
            )
            sequence += 1
            continue

        source_path = UPLOAD_DIR / f"address_fill_source_{job_id}_{index}{suffix}"
        source_path.write_bytes(content)
        try:
            chunks = parse_document(source_path, source_id)
        except ValueError as exc:
            _save_event(
                _event(
                    job_id,
                    sequence,
                    "sources",
                    "资料解析失败",
                    f"{safe_name}：{exc}",
                    status="failed",
                    payload={"source_id": source_id, "filename": safe_name, "path": str(source_path)},
                )
            )
            sequence += 1
            continue

        parsed_count += 1
        all_chunks.extend(chunks)
        summary = f"{safe_name} 已解析 {len(chunks)} 个文本片段" if chunks else f"{safe_name} 未提取到有效文本"
        _save_event(
            _event(
                job_id,
                sequence,
                "sources",
                "阅读资料",
                summary,
                status="done" if chunks else "failed",
                payload={
                    "source_id": source_id,
                    "filename": safe_name,
                    "path": str(source_path),
                    "chunks": [chunk.__dict__ for chunk in chunks[:5]],
                    "chunk_count": len(chunks),
                },
            )
        )
        sequence += 1

    return source_names, parsed_count, all_chunks


def create_address_fill_job(
    *,
    client_id: str,
    input_path: Path,
    input_name: str,
    input_source: str,
    source_files: list[SourceUpload],
    job_id: str | None = None,
    progress_callback: FillProgressCallback | None = None,
) -> tuple[AddressFillJobDetail, pd.DataFrame]:
    if not client_id.strip():
        raise ValueError("client_id 不能为空")

    df = _read_excel(input_path)

    columns = [str(column) for column in df.columns]
    column_mode = _detect_column_mode(columns)
    job_id = job_id or uuid.uuid4().hex
    created_at = _now()
    total_rows = len(df)
    initial_job = AddressFillJobDetail(
        job_id=job_id,
        client_id=client_id,
        status=AddressFillJobStatus.running,
        task_name=f"地址补全_{created_at.replace(' ', '_').replace(':', '')}",
        input_source=input_source,
        source_count=len(source_files),
        total_rows=total_rows,
        success_rows=0,
        failed_rows=0,
        columns=[],
        column_mode=column_mode,
        result_file=None,
        created_at=created_at,
        updated_at=created_at,
    )
    _save_job(initial_job)
    clear_cancel(job_id)

    def emit_progress(phase: str, processed_rows: int, message: str = "") -> None:
        if progress_callback is None:
            return
        progress_callback({
            "phase": phase,
            "processed_rows": processed_rows,
            "total_rows": total_rows,
            "elapsed_seconds": int(monotonic() - _start_at),
            "message": message,
        })

    def emit_agent_stream(
        row_id: str,
        stage: str,
        title: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if progress_callback is None:
            return
        try:
            processed_rows = len(agent_items)
        except NameError:
            processed_rows = 0
        progress_callback({
            "event_type": "agent_stream",
            "phase": "agent",
            "stage": stage,
            "row_id": row_id,
            "title": title,
            "content": content,
            "payload": payload or {},
            "processed_rows": processed_rows,
            "total_rows": total_rows,
            "elapsed_seconds": int(monotonic() - _start_at),
        })

    _start_at = monotonic()

    emit_progress("parsing", 0, "开始解析资料")

    source_names, parsed_source_count, source_chunks = _save_and_parse_sources(job_id, source_files, 2)
    events = [
        _event(job_id, 1, "input", "待补全地址文件", f"{input_name} 字段结构检测通过，共 {total_rows} 行"),
        _event(job_id, 100, "sources", "参考资料来源", f"已接收 {len(source_names)} 个资料文件，成功解析 {parsed_source_count} 个", payload={"sources": source_names}),
    ]
    for event in events:
        _save_event(event)

    emit_progress("parsing", 0, "资料解析完成")
    emit_agent_stream(
        "",
        "system",
        "系统上下文已加载",
        f"系统提示词和上传资料已加载。本次任务共 {total_rows} 条地址，成功解析 {parsed_source_count} 个资料文件。",
        {"source_count": parsed_source_count, "source_names": source_names},
    )
    emit_progress("filling", 0, "开始逐条补全地址")

    agent_rows = []
    for index, record in enumerate(df.fillna("").to_dict(orient="records"), start=1):
        record["_row_id"] = str(index)
        agent_rows.append(record)

    agent_items: dict[str, dict[str, str]] = {}
    result_file = RESULT_DIR / f"address_fill_{job_id}.xlsx"
    cancelled = False
    agent_session = None
    try:
        from agents import SQLiteSession

        agent_session = SQLiteSession(f"address-fill-{job_id}")
    except Exception:
        agent_session = None

    for row_index, row in enumerate(agent_rows, start=1):
        if is_cancelled(job_id):
            cancelled = True
            break

        row_id = str(row.get("_row_id", row_index))
        question = build_address_fill_question(row)

        if row_index > 1:
            prev_row_id = str(row_index - 1)
            prev_state = get_row_state(job_id, prev_row_id)
            if prev_state and prev_state.get("status") != "done":
                prev_address = prev_state.get("address", "")
                save_row_state(job_id, prev_row_id, prev_address, "done", "done", "done", "done", "done")
                _emit_step_state_update(progress_callback, job_id, prev_row_id, prev_address, "done", "done", "done", "done", "done")

        _step_seq_base = row_index * 10

        def _emit_and_save_step(step_seq_offset: int, step_stage: str, step_title: str, step_summary: str, step_payload: dict[str, Any]) -> None:
            step_payload["stage"] = step_stage
            step_event_id = step_payload.get("event_id", "")
            emit_agent_stream(row_id, step_stage, step_title, step_summary, step_payload)
            _save_event(
                _event(
                    job_id,
                    _step_seq_base + step_seq_offset,
                    "agent",
                    f"第 {row_id} 行：{step_title}",
                    step_summary,
                    payload=step_payload,
                    event_id=step_event_id or None,
                )
            )

        _emit_and_save_step(
            0,
            "address_start",
            f"地址 {row_id}-开始",
            question,
            {"event_id": f"{job_id}-a{row_id}-start", "row_id": row_id, "row_index": row_index, "question": question},
        )

        address_text = str(row.get("new_address", ""))
        save_row_state(job_id, row_id, address_text, "running", "waiting", "waiting", "waiting", "waiting")
        _emit_step_state_update(progress_callback, job_id, row_id, address_text, "running", "waiting", "waiting", "waiting", "waiting")

        missing_levels = [f"new_level_{i}" for i in range(1, 8) if not str(row.get(f"new_level_{i}", "") or "").strip()]
        missing_names = [_LEVEL_NAMES.get(lv, lv) for lv in missing_levels]
        _emit_and_save_step(
            1,
            "step",
            "层级研判：识别原始地址缺失层级",
            f"缺失层级：{'、'.join(missing_names) if missing_names else '无'}",
            {"event_id": f"{job_id}-s{row_id}-1", "row_id": row_id, "step": 1, "missing_levels": missing_levels},
        )
        save_row_state(job_id, row_id, address_text, "running", "done", "waiting", "waiting", "waiting")
        _emit_step_state_update(progress_callback, job_id, row_id, address_text, "running", "done", "waiting", "waiting", "waiting")

        _emit_and_save_step(
            2,
            "step",
            "任务定标：确定需补全的目标地址层级",
            f"目标补全：{'、'.join(missing_names) if missing_names else '无需补全'}",
            {"event_id": f"{job_id}-s{row_id}-2", "row_id": row_id, "step": 2, "target_levels": missing_levels},
        )
        save_row_state(job_id, row_id, address_text, "running", "done", "done", "waiting", "waiting")
        _emit_step_state_update(progress_callback, job_id, row_id, address_text, "running", "done", "done", "waiting", "waiting")

        agent_event_count = 0
        sub_step_count = 0

        emit_agent_stream(
            row_id,
            "step",
            "智能推理：模型分析与地址补全",
            "正在推理…",
            {"step": 3, "loading": True},
        )
        save_row_state(job_id, row_id, address_text, "running", "done", "done", "doing", "waiting")
        _emit_step_state_update(progress_callback, job_id, row_id, address_text, "running", "done", "done", "doing", "waiting")

        def record_agent_event(_event_type: str, title: str, summary: str, payload: dict[str, Any]) -> None:
            nonlocal agent_event_count, sub_step_count
            agent_event_count += 1
            sub_step_count += 1
            event_id = f"{job_id}-{1000 + row_index * 20 + agent_event_count:04d}"
            sub_type = (payload or {}).get("sub_type", "reasoning")
            emit_agent_stream(
                row_id,
                "sub_step",
                title,
                summary,
                {"event_id": event_id, "row_id": row_id, "step": 3, "sub_step": sub_step_count, "sub_type": sub_type, **(payload or {})},
            )
            _save_event(
                _event(
                    job_id,
                    1000 + row_index * 20 + agent_event_count,
                    "agent",
                    f"第 {row_id} 行：{title}",
                    summary,
                    payload={"event_id": event_id, "row_id": row_id, "step": 3, "sub_step": sub_step_count, "sub_type": sub_type, **(payload or {})},
                )
            )

        row_result = run_address_fill_agent_single(row, source_chunks, record_agent_event, session=agent_session)

        if row_result.item is not None:
            filled_parts = []
            for lv in missing_levels:
                val = _normalize_value(getattr(row_result.item, lv, ""))
                if val:
                    filled_parts.append(f"{_LEVEL_NAMES.get(lv, lv)}：{val}")
            result_summary = "缺失层级补全：" + "、".join(filled_parts) if filled_parts else "无补全结果"
        else:
            result_summary = row_result.message or "补全失败"

        record_agent_event(
            "agent",
            "模型推理完毕",
            result_summary,
            {"sub_type": "result", "has_item": row_result.item is not None},
        )
        save_row_state(job_id, row_id, address_text, "running", "done", "done", "done", "waiting")
        _emit_step_state_update(progress_callback, job_id, row_id, address_text, "running", "done", "done", "done", "waiting")

        if row_result.item is not None:
            item = row_result.item
            agent_items[row_id] = {
                f"new_level_{lvl}": _normalize_value(getattr(item, f"new_level_{lvl}", ""))
                for lvl in range(1, 8)
            }
        else:
            agent_items[row_id] = {}

        result_df = _build_result(df, column_mode, agent_items)
        result_df.to_excel(result_file, index=False)

        processed = row_index
        success_so_far = 0
        fail_so_far = 0
        for rid, vals in agent_items.items():
            filled_any = any(vals.get(f"new_level_{lvl}") for lvl in range(1, 8))
            if filled_any:
                success_so_far += 1
            else:
                fail_so_far += 1

        _update_job_progress(job_id, processed, success_so_far, fail_so_far, str(result_file), list(result_df.columns))

        emit_progress("filling", processed, f"已补全 {processed}/{total_rows} 条")
        filled_levels = []
        if row_result.item is not None:
            filled_levels = [f"new_level_{lvl}" for lvl in range(1, 8) if _normalize_value(getattr(row_result.item, f"new_level_{lvl}", ""))]
        _emit_and_save_step(
            4,
            "step",
            "结果生成：完成层级地址补全",
            f"已补全 {len(filled_levels)} 个层级" if filled_levels else row_result.message,
            {"event_id": f"{job_id}-s{row_id}-4", "row_id": row_id, "step": 4, "filled_levels": filled_levels},
        )
        save_row_state(job_id, row_id, address_text, "done", "done", "done", "done", "done")
        _emit_step_state_update(progress_callback, job_id, row_id, address_text, "done", "done", "done", "done", "done")

        _emit_and_save_step(
            9,
            "address_end",
            f"地址 {row_id}-结束",
            row_result.message,
            {"event_id": f"{job_id}-a{row_id}-end", "row_id": row_id, "row_index": row_index, "preview_refresh": True, "has_item": row_result.item is not None},
        )

    if cancelled:
        result_df = _build_result(df, column_mode, agent_items)
        result_df.to_excel(result_file, index=False)
        processed = len(agent_items)
        success_so_far = sum(1 for vals in agent_items.values() if any(vals.get(f"new_level_{lvl}") for lvl in range(1, 8)))
        fail_so_far = processed - success_so_far
        _update_job_progress(job_id, processed, success_so_far, fail_so_far, str(result_file), list(result_df.columns))

        for r_index in range(processed + 1, total_rows + 1):
            r_id = str(r_index)
            if r_id not in agent_items:
                r_address = str(agent_rows[r_index - 1].get("new_address", ""))
                save_row_state(job_id, r_id, r_address, "interrupted", "waiting", "waiting", "waiting", "waiting")
                _emit_step_state_update(progress_callback, job_id, r_id, r_address, "interrupted", "waiting", "waiting", "waiting", "waiting")

        job = get_address_fill_job(job_id)
        if job:
            job.status = AddressFillJobStatus.cancelled
            job.updated_at = _now()
            _save_job(job)

        emit_progress("cancelled", processed, "补全已中断，已保留结果")
        clear_cancel(job_id)
        return job or initial_job, result_df

    emit_progress("summary", total_rows, "正在汇总结果")

    result_df = _build_result(df, column_mode, agent_items)
    result_df.to_excel(result_file, index=False)

    failed_rows = int((result_df["desc"] != "").sum()) if "desc" in result_df.columns else 0
    job = AddressFillJobDetail(
        job_id=job_id,
        client_id=client_id,
        status=AddressFillJobStatus.completed,
        task_name=initial_job.task_name,
        input_source=input_source,
        source_count=len(source_names),
        total_rows=len(result_df),
        success_rows=max(len(result_df) - failed_rows, 0),
        failed_rows=failed_rows,
        columns=list(result_df.columns),
        column_mode=column_mode,
        result_file=str(result_file),
        created_at=created_at,
        updated_at=_now(),
    )
    _save_job(job)

    emit_progress("done", total_rows, "补全完成")
    return job, result_df


def _update_job_progress(job_id: str, processed: int, success: int, failed: int, result_file: str, columns: list[str]) -> None:
    job = get_address_fill_job(job_id)
    if job is None:
        return
    job.success_rows = success
    job.failed_rows = failed
    job.result_file = result_file
    job.columns = columns
    job.updated_at = _now()
    _save_job(job)


def create_address_fill_job_from_upload(
    *,
    client_id: str,
    filename: str,
    content: bytes,
    source_files: list[SourceUpload],
    job_id: str | None = None,
    progress_callback: FillProgressCallback | None = None,
) -> tuple[AddressFillJobDetail, pd.DataFrame]:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise ValueError("补全输入仅支持 .xlsx 或 .xls 文件")

    upload_path = UPLOAD_DIR / f"address_fill_{Path(filename).stem}_{uuid.uuid4().hex}{suffix}"
    upload_path.write_bytes(content)
    return create_address_fill_job(
        client_id=client_id,
        input_path=upload_path,
        input_name=filename,
        input_source="Excel上传",
        source_files=source_files,
        job_id=job_id,
        progress_callback=progress_callback,
    )


def create_address_fill_job_from_split(
    *,
    client_id: str,
    split_job_id: str,
    source_files: list[SourceUpload],
    job_id: str | None = None,
    progress_callback: FillProgressCallback | None = None,
) -> tuple[AddressFillJobDetail, pd.DataFrame]:
    split_job = get_split_job(split_job_id)
    if split_job is None:
        raise ValueError("拆分记录不存在")
    input_path = _source_file_from_split(split_job)
    return create_address_fill_job(
        client_id=client_id,
        input_path=input_path,
        input_name=split_job.task_name or input_path.name,
        input_source="拆分结果",
        source_files=source_files,
        job_id=job_id,
        progress_callback=progress_callback,
    )


def get_address_fill_job(job_id: str) -> AddressFillJobDetail | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT payload FROM address_fill_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return AddressFillJobDetail(**json.loads(row["payload"])) if row else None


def delete_address_fill_job(job_id: str) -> bool:
    job = get_address_fill_job(job_id)
    if job is None:
        return False
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM address_fill_jobs WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM address_fill_events WHERE job_id = ?", (job_id,))
    if job.result_file:
        path = Path(job.result_file)
        if path.exists():
            path.unlink()
    return True


def list_address_fill_jobs() -> list[AddressFillJobDetail]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT payload FROM address_fill_jobs ORDER BY created_at DESC").fetchall()
    return [AddressFillJobDetail(**json.loads(row["payload"])) for row in rows]


def list_address_fill_records() -> list[AddressFillRecordResponse]:
    records = []
    for job in list_address_fill_jobs():
        records.append(
            AddressFillRecordResponse(
                id=job.job_id,
                taskName=job.task_name,
                inputSource=job.input_source,
                sourceCount=job.source_count,
                total=job.total_rows,
                success=job.success_rows,
                failed=job.failed_rows,
                status="success" if job.status == AddressFillJobStatus.completed else "partial",
                startedAt=job.created_at,
                columnMode=job.column_mode,
                downloadUrl=f"/api/address-fill/jobs/{job.job_id}/download",
            )
        )
    return records


def list_address_fill_events(job_id: str, after_event_id: str | None = None) -> list[AddressFillWorkflowEvent]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT payload FROM address_fill_events WHERE job_id = ? ORDER BY sequence ASC",
            (job_id,),
        ).fetchall()
    events = [
        event
        for event in (AddressFillWorkflowEvent(**json.loads(row["payload"])) for row in rows)
        if event.title not in LEGACY_WORKFLOW_EVENT_TITLES
    ]
    if not after_event_id:
        return events
    seen = False
    result: list[AddressFillWorkflowEvent] = []
    for event in events:
        if seen:
            result.append(event)
        elif event.event_id == after_event_id:
            seen = True
    return result


def get_latest_workflow(client_id: str) -> tuple[AddressFillJobDetail | None, list[AddressFillWorkflowEvent]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload FROM address_fill_jobs WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
            (client_id,),
        ).fetchone()
    if row is None:
        return None, []
    job = AddressFillJobDetail(**json.loads(row["payload"]))
    return job, list_address_fill_events(job.job_id)


def read_address_fill_rows(job: AddressFillJobDetail, page: int = 1, page_size: int = 200) -> tuple[list[dict[str, Any]], int]:
    if not job.result_file:
        return [], 0
    path = Path(job.result_file)
    if not path.exists():
        return [], 0
    df = pd.read_excel(path).fillna("")
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return df.iloc[start:end].to_dict(orient="records"), len(df)


def list_fillable_split_results() -> list[AddressFillSplitResultResponse]:
    results: list[AddressFillSplitResultResponse] = []
    for job in list_split_jobs():
        if job.column_mode not in {ColumnMode.level8, ColumnMode.level11}:
            continue
        if not job.result_file or not Path(job.result_file).exists():
            continue
        if job.status.value != "completed":
            continue
        scheme = "11级标准列" if job.column_mode == ColumnMode.level11 else "8级标准列" if job.column_mode == ColumnMode.level8 else "原始字段自定义"
        results.append(
            AddressFillSplitResultResponse(
                id=job.job_id,
                taskName=job.task_name or job.job_id,
                total=job.total_rows,
                columnMode=job.column_mode.value,
                splitScheme=scheme,
                startedAt=job.created_at,
            )
        )
    return results
