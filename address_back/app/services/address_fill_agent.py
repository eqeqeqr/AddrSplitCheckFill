from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

from app.core.config import ENV_PATH
from app.schemas.address_fill import AddressFillItem, AddressFillSessionOutput
from app.services.model_config import get_active_model_config

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(ENV_PATH)

AgentEventCallback = Callable[[str, str, str, dict[str, Any]], None]

_MAX_RETRY = 3

_PROVIDER_PREFIXES = (
    "OPENAI",
    "AGENT",
    "LLM",
    "DEEPSEEK",
    "ZHIPU",
    "GLM",
    "DASHSCOPE",
    "QWEN",
    "MOONSHOT",
    "XIAOMI",
    "BAICHUAN",
    "MINIMAX",
    "SILICONFLOW",
    "VOLCENGINE",
    "ARK",
    "DOUBAO",
)

_DEFAULT_COMPAT_BASE_URLS = {
    "DEEPSEEK": "https://api.deepseek.com",
    "ZHIPU": "https://open.bigmodel.cn/api/paas/v4",
    "GLM": "https://open.bigmodel.cn/api/paas/v4",
    "DASHSCOPE": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "QWEN": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "MOONSHOT": "https://api.moonshot.cn/v1",
    "BAICHUAN": "https://api.baichuan-ai.com/v1",
    "MINIMAX": "https://api.minimax.chat/v1",
    "SILICONFLOW": "https://api.siliconflow.cn/v1",
}


@dataclass
class AgentRunResult:
    output: AddressFillSessionOutput | None
    mode: str
    message: str


@dataclass
class AgentRowResult:
    row_id: str
    item: AddressFillItem | None = None
    message: str = ""


@dataclass(frozen=True)
class AgentModelConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None
    temperature: float = 0
    max_tokens: int | None = None


_AGENT_PROMPT_PATH = Path(__file__).resolve().parent / "agent_prompt.md"

_LEVEL_DEFINITIONS = {
    "new_level_1": "省份/直辖市/自治区",
    "new_level_2": "地市",
    "new_level_3": "区县",
    "new_level_4": "乡镇/街道",
    "new_level_5": "路/巷/街",
    "new_level_6": "门牌号码/路号",
    "new_level_7": "建筑物/小区/自然村",
}

_QUESTION_LEVEL_DEFINITIONS = {
    "new_level_1": "归属哪个省份/直辖市/自治区",
    "new_level_2": "归属哪个地市",
    "new_level_3": "归属哪个区县",
    "new_level_4": "归属哪个乡镇/街道",
    "new_level_5": "位于哪条路/巷/街",
    "new_level_6": "门牌号码/路号是多少",
    "new_level_7": "建筑物/小区/自然村是什么",
}


def _load_agent_instructions() -> str:
    if _AGENT_PROMPT_PATH.exists():
        return _AGENT_PROMPT_PATH.read_text(encoding="utf-8")
    return ""


AGENT_INSTRUCTIONS = _load_agent_instructions()


def _env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str) -> int | None:
    value = os.getenv(name)
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _provider_from_env() -> str:
    explicit = _env_first("OPENAI_AGENT_PROVIDER", "LLM_PROVIDER", "MODEL_PROVIDER")
    if explicit:
        return explicit.upper()

    for prefix in _PROVIDER_PREFIXES:
        if prefix == "OPENAI":
            continue
        if _env_first(f"{prefix}_API_KEY", f"{prefix}_MODEL", f"{prefix}_DEFAULT_MODEL"):
            return prefix
    return "OPENAI"


def _resolve_model_config() -> AgentModelConfig:
    active_config = get_active_model_config()
    if active_config is not None:
        return AgentModelConfig(
            provider=active_config.provider,
            model=active_config.model,
            api_key=active_config.apiKey,
            base_url=active_config.baseUrl,
            temperature=_env_float("ADDRESS_FILL_AGENT_TEMPERATURE", 0),
            max_tokens=_env_int("ADDRESS_FILL_AGENT_MAX_TOKENS"),
        )

    provider = _provider_from_env()
    key_names = [f"{provider}_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY", "AGENT_API_KEY"]
    model_names = [
        f"{provider}_DEFAULT_MODEL",
        f"{provider}_MODEL",
        "OPENAI_DEFAULT_MODEL",
        "OPENAI_MODEL",
        "LLM_MODEL",
        "MODEL_NAME",
    ]
    base_url_names = [
        f"{provider}_BASE_URL",
        "OPENAI_BASE_URL",
        "LLM_BASE_URL",
        "AGENT_BASE_URL",
    ]

    api_key = _env_first(*key_names)
    model = _env_first(*model_names)
    base_url = _env_first(*base_url_names) or _DEFAULT_COMPAT_BASE_URLS.get(provider)
    return AgentModelConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url or None,
        temperature=_env_float("ADDRESS_FILL_AGENT_TEMPERATURE", 0),
        max_tokens=_env_int("ADDRESS_FILL_AGENT_MAX_TOKENS"),
    )


def _agent_enabled() -> bool:
    config = _resolve_model_config()
    if not config.api_key or not config.model:
        return False
    if config.provider != "OPENAI" and not config.base_url:
        return False
    return True


def _missing_config_message() -> str:
    provider = _provider_from_env()
    return (
        "未配置地址补全模型。请配置 OPENAI_API_KEY/OPENAI_DEFAULT_MODEL，"
        f"或配置 {provider}_API_KEY/{provider}_MODEL；国产 OpenAI 兼容模型还需要配置 {provider}_BASE_URL。"
    )


def _safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_rows = []
    for index, row in enumerate(rows, start=1):
        safe_rows.append(
            {
                "row_id": str(row.get("_row_id") or index),
                "new_address": row.get("new_address", ""),
                **{f"new_level_{level}": row.get(f"new_level_{level}", "") for level in range(1, 12)},
            }
        )
    return safe_rows


def _normalize_address_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def build_address_fill_question(row: dict[str, Any]) -> str:
    safe_row = _safe_rows([row])[0]
    address = _normalize_address_text(safe_row.get("new_address"))
    missing_levels = _missing_levels_for_row(safe_row)
    questions = [
        _QUESTION_LEVEL_DEFINITIONS[level]
        for level in missing_levels
        if level in _QUESTION_LEVEL_DEFINITIONS
    ]
    if not address:
        return "该行 new_address 为空，无法补全地址层级。"
    if not questions:
        return f"{address}，当前 1-7 级地址层级没有缺失。"
    return f"{address}，{'，'.join(questions)}？"


def _missing_levels_for_row(safe_row: dict[str, Any]) -> list[str]:
    return [
        f"new_level_{level}"
        for level in range(1, 8)
        if not _normalize_address_text(safe_row.get(f"new_level_{level}"))
    ]


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1)

    decoder = json.JSONDecoder()
    first_error: json.JSONDecodeError | None = None
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError as exc:
            if first_error is None:
                first_error = exc
            continue
        if isinstance(value, dict):
            return value

    if first_error is not None:
        raise first_error
    raise json.JSONDecodeError("No JSON object found", text, 0)


def _coerce_item(parsed: dict[str, Any], row_id: str, safe_row: dict[str, Any]) -> AddressFillItem:
    parsed["row_id"] = str(parsed.get("row_id") or row_id)
    for level in range(1, 8):
        field_name = f"new_level_{level}"
        value = parsed.get(field_name, "")
        parsed[field_name] = "" if value is None else str(value).strip()
        original_value = safe_row.get(field_name, "")
        if original_value:
            parsed[field_name] = str(original_value)
    for level in range(8, 12):
        parsed.pop(f"new_level_{level}", None)
    item = AddressFillItem.model_validate(parsed)
    item.row_id = row_id
    return item


def _build_client() -> OpenAI:
    config = _resolve_model_config()
    return OpenAI(api_key=config.api_key, base_url=config.base_url)


def _call_llm(system_prompt: str, user_content: str) -> str:
    config = _resolve_model_config()
    client = _build_client()
    kwargs: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": config.temperature,
    }
    if config.max_tokens:
        kwargs["max_tokens"] = config.max_tokens
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def _extract_reasoning_and_json(full_text: str) -> tuple[str, dict[str, Any] | None]:
    clean = re.sub(r"```(?:json)?\s*", "", full_text).strip()
    clean = re.sub(r"\s*```$", "", clean).strip()

    json_obj = None
    reasoning = clean
    for match in re.finditer(r"\{", clean):
        try:
            decoder = json.JSONDecoder()
            value, end = decoder.raw_decode(clean[match.start() :])
            if isinstance(value, dict) and "row_id" in value:
                json_obj = value
                reasoning = clean[: match.start()].strip()
                break
        except json.JSONDecodeError:
            continue

    return reasoning, json_obj


def run_address_fill_agent_single(
    row: dict[str, Any],
    chunks: list[Any],
    on_event: AgentEventCallback | None = None,
    session: Any | None = None,
) -> AgentRowResult:
    if not _agent_enabled():
        return AgentRowResult(row_id=str(row.get("_row_id", "")), message=_missing_config_message())

    safe_row = _safe_rows([row])[0]
    row_id = safe_row["row_id"]
    missing_levels = [
        f"new_level_{level}"
        for level in range(1, 8)
        if not safe_row.get(f"new_level_{level}", "")
    ]
    question = build_address_fill_question(row)

    if not safe_row.get("new_address", "").strip():
        return AgentRowResult(
            row_id=row_id,
            item=AddressFillItem(row_id=row_id, unresolved_levels=missing_levels),
            message="new_address 为空，跳过补全",
        )

    if not missing_levels:
        return AgentRowResult(
            row_id=row_id,
            item=AddressFillItem(
                row_id=row_id,
                **{f"new_level_{level}": safe_row.get(f"new_level_{level}", "") for level in range(1, 8)},
            ),
            message="无缺失层级，跳过补全",
        )

    system_prompt = AGENT_INSTRUCTIONS
    user_content = json.dumps(
        {
            "address": safe_row,
            "program_question": question,
            "missing_levels": missing_levels,
        },
        ensure_ascii=False,
    )

    model_config = _resolve_model_config()
    if on_event:
        on_event(
            "agent",
            "模型推理",
            question,
            {
                "provider": model_config.provider,
                "model": model_config.model,
                "base_url": model_config.base_url,
                "missing_levels": missing_levels,
            },
        )

    last_error = ""
    for attempt in range(1, _MAX_RETRY + 1):
        try:
            full_text = _call_llm(system_prompt, user_content)
        except Exception as exc:
            last_error = f"模型调用失败：{exc}"
            if on_event:
                on_event(
                    "agent",
                    "调用异常",
                    f"第 {attempt}/{_MAX_RETRY} 次调用失败：{exc}",
                    {"sub_type": "retry", "attempt": attempt, "max_retry": _MAX_RETRY, "error": str(exc)},
                )
            continue

        reasoning, json_obj = _extract_reasoning_and_json(full_text)

        if reasoning and on_event:
            on_event(
                "agent",
                "模型分析",
                reasoning[:3000],
                {"sub_type": "reasoning", "full_text": reasoning},
            )

        if json_obj is None:
            last_error = "模型返回内容中未找到有效 JSON"
            if on_event:
                on_event(
                    "agent",
                    "解析失败",
                    f"JSON 解析失败，重试 {attempt}/{_MAX_RETRY}",
                    {"sub_type": "retry", "attempt": attempt, "max_retry": _MAX_RETRY},
                )
            continue

        try:
            item = _coerce_item(json_obj, row_id, safe_row)
        except Exception as exc:
            last_error = f"JSON 格式校验失败：{exc}"
            if on_event:
                on_event(
                    "agent",
                    "校验失败",
                    f"格式校验失败，重试 {attempt}/{_MAX_RETRY}：{exc}",
                    {"sub_type": "retry", "attempt": attempt, "max_retry": _MAX_RETRY, "error": str(exc)},
                )
            continue

        return AgentRowResult(row_id=row_id, item=item, message="模型补全完成")

    return AgentRowResult(row_id=row_id, message=f"补全失败（{_MAX_RETRY} 次重试均失败）：{last_error}")


def run_address_fill_agent(
    rows: list[dict[str, Any]],
    chunks: list[Any],
    on_event: AgentEventCallback | None = None,
    session: Any | None = None,
) -> AgentRunResult:
    if not _agent_enabled():
        return AgentRunResult(output=None, mode="disabled", message=_missing_config_message())

    items: list[AddressFillItem] = []
    for row in rows:
        row_result = run_address_fill_agent_single(row, chunks, on_event, session=session)
        if row_result.item is not None:
            items.append(row_result.item)

    output = AddressFillSessionOutput(items=items)
    return AgentRunResult(output=output, mode="chat_completion", message="补全完成")
