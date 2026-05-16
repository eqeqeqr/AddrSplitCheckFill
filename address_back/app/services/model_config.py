from __future__ import annotations

import json
import uuid
from datetime import datetime

from openai import OpenAI

from app.schemas.address import (
    ModelConfigActivateResponse,
    ModelConfigListResponse,
    ModelConfigPayload,
    ModelConfigResponse,
    ModelConfigTestResponse,
)
from app.services.db import get_connection, init_db

MODEL_CONFIG_NAME = "models"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_store() -> dict:
    return {"activeId": "", "models": []}


def _read_store() -> dict:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload FROM environment_configs WHERE name = ?",
            (MODEL_CONFIG_NAME,),
        ).fetchone()
    if row is None:
        return _empty_store()
    try:
        payload = json.loads(row["payload"])
    except json.JSONDecodeError:
        return _empty_store()
    if not isinstance(payload, dict):
        return _empty_store()
    payload.setdefault("activeId", "")
    payload.setdefault("models", [])
    return payload


def _write_store(payload: dict) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO environment_configs (name, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (MODEL_CONFIG_NAME, json.dumps(payload, ensure_ascii=False), _now()),
        )


def _response(item: dict, active_id: str) -> ModelConfigResponse:
    return ModelConfigResponse(
        id=item["id"],
        provider=item["provider"],
        baseUrl=item["baseUrl"],
        apiKey=item["apiKey"],
        model=item["model"],
        active=item["id"] == active_id,
        updatedAt=item.get("updatedAt", ""),
    )


def list_model_configs() -> ModelConfigListResponse:
    store = _read_store()
    active_id = str(store.get("activeId") or "")
    models = [_response(item, active_id) for item in store.get("models", [])]
    return ModelConfigListResponse(activeId=active_id, models=models)


def upsert_model_config(payload: ModelConfigPayload) -> ModelConfigResponse:
    store = _read_store()
    active_id = str(store.get("activeId") or "")
    models = list(store.get("models", []))
    config_id = payload.id or uuid.uuid4().hex
    updated_at = _now()
    item = {
        "id": config_id,
        "provider": payload.provider,
        "baseUrl": payload.baseUrl.rstrip("/"),
        "apiKey": payload.apiKey,
        "model": payload.model,
        "updatedAt": updated_at,
    }

    replaced = False
    for index, existing in enumerate(models):
        if existing.get("id") == config_id:
            models[index] = item
            replaced = True
            break
    if not replaced:
        models.append(item)

    store["models"] = models
    store["activeId"] = active_id
    _write_store(store)
    return _response(item, active_id)


def delete_model_config(config_id: str) -> bool:
    store = _read_store()
    models = [item for item in store.get("models", []) if item.get("id") != config_id]
    if len(models) == len(store.get("models", [])):
        return False
    if store.get("activeId") == config_id:
        store["activeId"] = ""
    store["models"] = models
    _write_store(store)
    return True


def get_active_model_config() -> ModelConfigResponse | None:
    configs = list_model_configs()
    if not configs.activeId:
        return None
    return next((item for item in configs.models if item.id == configs.activeId), None)


def activate_model_config(config_id: str) -> ModelConfigActivateResponse | None:
    store = _read_store()
    active_item = next((item for item in store.get("models", []) if item.get("id") == config_id), None)
    if active_item is None:
        return None
    store["activeId"] = config_id
    _write_store(store)
    return ModelConfigActivateResponse(activeId=config_id, model=_response(active_item, config_id))


def test_model_config(payload: ModelConfigPayload) -> ModelConfigTestResponse:
    try:
        client = OpenAI(api_key=payload.apiKey, base_url=payload.baseUrl.rstrip("/"))
        response = client.chat.completions.create(
            model=payload.model,
            messages=[
                {"role": "system", "content": "You are a connection test. Reply with OK only."},
                {"role": "user", "content": "OK"},
            ],
            temperature=0,
            max_tokens=8,
        )
        content = response.choices[0].message.content or ""
        message = f"模型连接成功，返回：{content.strip() or '空响应'}"
        return ModelConfigTestResponse(ok=True, message=message)
    except Exception as exc:
        return ModelConfigTestResponse(ok=False, message=f"模型连接失败：{exc}")
