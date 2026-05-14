from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.schemas.address import ColumnMode, VALIDATION_LEVELS, ValidationRulePayload, ValidationRuleResponse
from app.services.constants import LEVEL8_FIELDS, LEVEL11_FIELDS
from app.services.db import get_connection, init_db

RULE_IMPORT_COLUMNS = ["规则ID", "正则表达式", "校验层级"]
VALIDATION_STATUS_PASS = "通过"
VALIDATION_STATUS_FAIL = "未通过"
VALIDATION_STATUS_UNCHECKED = "未校验"


def _serialize_levels(levels: list[str]) -> str:
    return json.dumps(levels, ensure_ascii=False)


def _deserialize_levels(value: str) -> list[str]:
    try:
        levels = json.loads(value)
    except json.JSONDecodeError:
        levels = [item.strip() for item in value.split(";") if item.strip()]
    return [str(item).strip() for item in levels if str(item).strip()]


def _normalize_levels(raw_value: Any) -> list[str]:
    if pd.isna(raw_value):
        raise ValueError("校验层级不能为空")
    parts = [
        item.strip()
        for item in re.split(r"[;；,，\s]+", str(raw_value))
        if item.strip()
    ]
    if not parts:
        raise ValueError("校验层级不能为空")
    normalized: list[str] = []
    for level in parts:
        if level not in VALIDATION_LEVELS:
            raise ValueError("校验层级仅支持 level_1 到 level_11")
        if level not in normalized:
            normalized.append(level)
    return normalized


def _validate_pattern(pattern: str) -> str:
    normalized = pattern.strip()
    if not normalized:
        raise ValueError("正则表达式不能为空")
    try:
        re.compile(normalized)
    except re.error as exc:
        raise ValueError(f"正则表达式无效：{exc}") from exc
    return normalized


def _row_to_rule(row) -> ValidationRuleResponse:
    return ValidationRuleResponse(
        ruleId=row["rule_id"],
        pattern=row["pattern"],
        levels=_deserialize_levels(row["levels"]),
    )


def list_validation_rules() -> list[ValidationRuleResponse]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT rule_id, pattern, levels
            FROM validation_rules
            ORDER BY rule_id ASC
            """
        ).fetchall()
    return [_row_to_rule(row) for row in rows]


def upsert_validation_rule(payload: ValidationRulePayload) -> ValidationRuleResponse:
    rule_id = payload.ruleId.strip()
    if not rule_id:
        raise ValueError("规则ID不能为空")

    rule = ValidationRuleResponse(
        ruleId=rule_id,
        pattern=_validate_pattern(payload.pattern),
        levels=payload.levels,
    )
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO validation_rules (rule_id, pattern, levels, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                rule.ruleId,
                rule.pattern,
                _serialize_levels(rule.levels),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    return rule


def update_validation_rule(rule_id: str, payload: ValidationRulePayload) -> ValidationRuleResponse | None:
    init_db()
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM validation_rules WHERE rule_id = ?", (rule_id,)).fetchone()
    if exists is None:
        return None

    if rule_id != payload.ruleId:
        delete_validation_rule(rule_id)
    return upsert_validation_rule(payload)


def delete_validation_rule(rule_id: str) -> bool:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM validation_rules WHERE rule_id = ?", (rule_id,)).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM validation_rules WHERE rule_id = ?", (rule_id,))
    return True


def import_validation_rules(path: Path) -> list[ValidationRuleResponse]:
    df = pd.read_excel(path)
    columns = [str(column).strip() for column in df.columns]
    if columns[:3] != RULE_IMPORT_COLUMNS:
        raise ValueError("导入模板不符合规范，需要前三列表头依次为：规则ID、正则表达式、校验层级")

    rules: list[ValidationRuleResponse] = []
    for index, row in df.iterrows():
        rule_id = "" if pd.isna(row["规则ID"]) else str(row["规则ID"]).strip()
        pattern = "" if pd.isna(row["正则表达式"]) else str(row["正则表达式"]).strip()
        if not rule_id and not pattern and pd.isna(row["校验层级"]):
            continue
        try:
            payload = ValidationRulePayload(
                ruleId=rule_id,
                pattern=pattern,
                levels=_normalize_levels(row["校验层级"]),
            )
            rules.append(upsert_validation_rule(payload))
        except ValueError as exc:
            raise ValueError(f"第 {index + 2} 行规则无效：{exc}") from exc
    return rules


def group_validation_rules_by_level(rules: list[ValidationRuleResponse] | None = None) -> dict[str, list[ValidationRuleResponse]]:
    grouped = {level: [] for level in LEVEL11_FIELDS}
    for rule in rules if rules is not None else list_validation_rules():
        for level in rule.levels:
            if level in grouped:
                grouped[level].append(rule)
    return grouped


def validate_levels(column_mode: ColumnMode, levels: dict[str, str]) -> tuple[str, str]:
    if column_mode == ColumnMode.raw:
        return VALIDATION_STATUS_UNCHECKED, ""

    active_levels = LEVEL8_FIELDS if column_mode == ColumnMode.level8 else LEVEL11_FIELDS
    grouped_rules = group_validation_rules_by_level()
    has_rule = any(grouped_rules[level] for level in active_levels)
    if not has_rule:
        return VALIDATION_STATUS_UNCHECKED, ""

    violated_rule_ids: list[str] = []
    for level in active_levels:
        value = str(levels.get(level, "") or "")
        for rule in grouped_rules[level]:
            try:
                matched = re.search(rule.pattern, value) is not None
            except re.error:
                matched = False
            if matched and rule.ruleId not in violated_rule_ids:
                violated_rule_ids.append(rule.ruleId)

    if violated_rule_ids:
        return VALIDATION_STATUS_FAIL, f"违反规则ID：{';'.join(violated_rule_ids)}"
    return VALIDATION_STATUS_PASS, ""


def validation_rules_fingerprint() -> str:
    payload = [
        rule.model_dump(mode="json")
        for rule in list_validation_rules()
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
