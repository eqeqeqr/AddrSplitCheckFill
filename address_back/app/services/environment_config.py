from __future__ import annotations

import json
from datetime import datetime

from app.schemas.address import RedisConfigPayload, RedisConfigResponse
from app.services.db import get_connection, init_db

REDIS_CONFIG_NAME = "redis"


def default_redis_config() -> RedisConfigResponse:
    return RedisConfigResponse(
        mode="local",
        host="127.0.0.1",
        port=6379,
        db=0,
        password="",
        updatedAt="",
    )


def get_redis_config() -> RedisConfigResponse:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload, updated_at FROM environment_configs WHERE name = ?",
            (REDIS_CONFIG_NAME,),
        ).fetchone()

    if row is None:
        return default_redis_config()

    payload = json.loads(row["payload"])
    return RedisConfigResponse(**payload, updatedAt=row["updated_at"])


def save_redis_config(payload: RedisConfigPayload) -> RedisConfigResponse:
    init_db()
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = RedisConfigResponse(**payload.model_dump(), updatedAt=updated_at)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO environment_configs (name, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                REDIS_CONFIG_NAME,
                json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                updated_at,
            ),
        )

    return response
