from __future__ import annotations

import json
import uuid
from datetime import datetime

from app.schemas.address import RedisConfigActivateResponse, RedisConfigListResponse, RedisConfigPayload, RedisConfigResponse
from app.services.db import get_connection, init_db

REDIS_CONFIG_NAME = "redis"
REDIS_CONFIGS_NAME = "redis_configs"


def default_redis_config() -> RedisConfigResponse:
    return RedisConfigResponse(
        id="",
        mode="local",
        host="127.0.0.1",
        port=6379,
        db=0,
        password="",
        active=True,
        updatedAt="",
    )


def _read_environment_payload(name: str) -> tuple[dict, str] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload, updated_at FROM environment_configs WHERE name = ?",
            (name,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row["payload"]), row["updated_at"]


def _write_environment_payload(name: str, payload: dict, updated_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO environment_configs (name, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                name,
                json.dumps(payload, ensure_ascii=False),
                updated_at,
            ),
        )


def _response_from_payload(payload: dict, updated_at: str = "", active: bool = False) -> RedisConfigResponse:
    normalized = {
        "id": payload.get("id", ""),
        "mode": payload.get("mode", "local"),
        "host": payload.get("host", "127.0.0.1"),
        "port": payload.get("port", 6379),
        "db": payload.get("db", 0),
        "password": payload.get("password", ""),
        "active": active,
        "updatedAt": payload.get("updatedAt", updated_at),
    }
    return RedisConfigResponse(**normalized)


def _read_single_redis_config() -> RedisConfigResponse:
    stored = _read_environment_payload(REDIS_CONFIG_NAME)
    if stored is None:
        return default_redis_config()

    payload, updated_at = stored
    return _response_from_payload(payload, updated_at, active=True)


def _read_redis_store() -> tuple[list[dict], str, str]:
    stored = _read_environment_payload(REDIS_CONFIGS_NAME)
    if stored is None:
        single = _read_single_redis_config()
        seed_id = single.id or uuid.uuid4().hex
        seed_payload = single.model_dump(mode="json")
        seed_payload["id"] = seed_id
        seed_payload["active"] = True
        updated_at = single.updatedAt or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        store_payload = {"activeId": seed_id, "configs": [seed_payload]}
        _write_environment_payload(REDIS_CONFIGS_NAME, store_payload, updated_at)
        return [seed_payload], seed_id, updated_at

    payload, updated_at = stored
    configs = payload.get("configs", [])
    active_id = payload.get("activeId", "")
    if not isinstance(configs, list):
        configs = []
    return configs, active_id, updated_at


def _write_redis_store(configs: list[dict], active_id: str, updated_at: str) -> None:
    _write_environment_payload(REDIS_CONFIGS_NAME, {"activeId": active_id, "configs": configs}, updated_at)


def get_redis_config() -> RedisConfigResponse:
    configs, active_id, _ = _read_redis_store()
    active_payload = next((item for item in configs if item.get("id") == active_id), None)
    if active_payload is None and configs:
        active_payload = configs[0]
        active_id = active_payload.get("id", "")

    if active_payload is None:
        return default_redis_config()

    return _response_from_payload(active_payload, active_payload.get("updatedAt", ""), active=True)


def list_redis_configs() -> RedisConfigListResponse:
    configs, active_id, _ = _read_redis_store()
    responses = [
        _response_from_payload(item, item.get("updatedAt", ""), active=item.get("id") == active_id)
        for item in configs
    ]
    return RedisConfigListResponse(activeId=active_id, configs=responses)


def upsert_redis_config(payload: RedisConfigPayload, activate: bool = False) -> RedisConfigResponse:
    init_db()
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    configs, active_id, _ = _read_redis_store()
    config_id = payload.id or uuid.uuid4().hex
    config = payload.model_dump(mode="json")
    config["id"] = config_id
    config["updatedAt"] = updated_at
    config["active"] = False

    replaced = False
    for index, item in enumerate(configs):
        if item.get("id") == config_id:
            configs[index] = config
            replaced = True
            break

    if not replaced:
        configs.append(config)

    if activate or not active_id:
        active_id = config_id

    _write_redis_store(configs, active_id, updated_at)
    if active_id == config_id:
        _write_environment_payload(REDIS_CONFIG_NAME, config, updated_at)

    return _response_from_payload(config, updated_at, active=active_id == config_id)


def save_redis_config(payload: RedisConfigPayload) -> RedisConfigResponse:
    return upsert_redis_config(payload, activate=True)


def activate_redis_config(config_id: str) -> RedisConfigActivateResponse | None:
    configs, active_id, _ = _read_redis_store()
    target = next((item for item in configs if item.get("id") == config_id), None)
    if target is None:
        return None

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_redis_store(configs, config_id, updated_at)
    _write_environment_payload(REDIS_CONFIG_NAME, target, updated_at)
    return RedisConfigActivateResponse(
        activeId=config_id,
        config=_response_from_payload(target, target.get("updatedAt", updated_at), active=True),
    )


def delete_redis_config(config_id: str) -> bool:
    configs, active_id, _ = _read_redis_store()
    next_configs = [item for item in configs if item.get("id") != config_id]
    if len(next_configs) == len(configs):
        return False

    next_active_id = active_id
    if active_id == config_id:
        next_active_id = next_configs[0].get("id", "") if next_configs else ""

    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_redis_store(next_configs, next_active_id, updated_at)
    if next_active_id:
        active_payload = next(item for item in next_configs if item.get("id") == next_active_id)
        _write_environment_payload(REDIS_CONFIG_NAME, active_payload, updated_at)
    return True
