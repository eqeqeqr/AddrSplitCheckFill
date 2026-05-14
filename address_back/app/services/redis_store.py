from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any

import redis

from app.services.environment_config import get_redis_config
from app.schemas.address import SplitJobDetail

JOB_PREFIX = "address:split:job:"
ROWS_PREFIX = "address:split:rows:"
CACHE_PREFIX = "address:split:cache:"
INDEX_KEY = "address:split:index"


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    config = get_redis_config()
    if config.mode == "disabled":
        raise ConnectionError("Redis 已断开")
    client = redis.Redis(
        host=config.host,
        port=config.port,
        db=config.db,
        password=config.password or None,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    client.ping()
    return client


def reset_redis_connection() -> None:
    get_redis.cache_clear()


def test_connection(config_payload: dict[str, Any] | None = None) -> tuple[bool, str]:
    try:
        if config_payload is None:
            config = get_redis_config()
            if config.mode == "disabled":
                return False, "Redis 已断开，系统正在使用本地模式"
            client = get_redis()
        else:
            if config_payload.get("mode") == "disabled":
                return False, "Redis 已断开，系统正在使用本地模式"
            client = redis.Redis(
                host=config_payload["host"],
                port=int(config_payload["port"]),
                db=int(config_payload.get("db", 0)),
                password=config_payload.get("password") or None,
                decode_responses=True,
                socket_connect_timeout=float(config_payload.get("timeout", 3)),
                socket_timeout=float(config_payload.get("timeout", 3)),
            )
        pong = client.ping()
        return bool(pong), "Redis 连接成功" if pong else "Redis 未返回 PONG"
    except Exception as exc:
        return False, f"Redis 连接失败：{exc}"


def redis_available() -> bool:
    try:
        get_redis().ping()
        return True
    except Exception:
        return False


def get_redis_status() -> dict[str, Any]:
    config = get_redis_config()
    if config.mode == "disabled":
        return {
            "available": False,
            "mode": config.mode,
            "host": config.host,
            "port": config.port,
            "db": config.db,
            "message": "当前未连接 Redis，系统将使用本地模式运行；如需跨任务缓存和高性能记录查询，请安装或配置 Redis。",
        }
    ok, message = test_connection({**config.model_dump(), "timeout": 0.6})
    return {
        "available": ok,
        "mode": config.mode,
        "host": config.host,
        "port": config.port,
        "db": config.db,
        "message": message if ok else "当前未连接 Redis，系统将使用本地模式运行；如需跨任务缓存和高性能记录查询，请安装或配置 Redis。",
    }


def get_storage_config() -> dict[str, Any]:
    config = get_redis_config()
    return {
        "host": config.host,
        "port": config.port,
        "db": config.db,
    }


def build_cache_key(filename: str, sample_size: int, scheme: str = "") -> str:
    safe_name = filename.strip().replace("\\", "_").replace("/", "_") or "upload.xlsx"
    safe_scheme = scheme.strip().replace("\\", "_").replace("/", "_").replace(":", "_") or "default"
    return f"{CACHE_PREFIX}{safe_name}:{sample_size}:{safe_scheme}"


def save_job(job: SplitJobDetail, rows: list[dict[str, Any]] | None = None) -> None:
    if not redis_available():
        return

    client = get_redis()
    job_key = f"{JOB_PREFIX}{job.job_id}"
    rows_key = f"{ROWS_PREFIX}{job.job_id}"
    payload = job.model_dump(mode="json")

    pipe = client.pipeline()
    pipe.set(job_key, json.dumps(payload, ensure_ascii=False))
    pipe.zadd(INDEX_KEY, {job.job_id: time.time()})
    if job.cache_key:
        pipe.set(job.cache_key, job.job_id)
    if rows is not None:
        pipe.delete(rows_key)
        if rows:
            pipe.rpush(rows_key, *[json.dumps(row, ensure_ascii=False) for row in rows])
    pipe.execute()


def get_job(job_id: str) -> SplitJobDetail | None:
    if not redis_available():
        return None

    payload = get_redis().get(f"{JOB_PREFIX}{job_id}")
    return SplitJobDetail(**json.loads(payload)) if payload else None


def get_cached_job(cache_key: str) -> SplitJobDetail | None:
    if not redis_available():
        return None

    job_id = get_redis().get(cache_key)
    return get_job(job_id) if job_id else None


def list_jobs() -> list[SplitJobDetail]:
    if not redis_available():
        return []

    client = get_redis()
    job_ids = client.zrevrange(INDEX_KEY, 0, -1)
    jobs: list[SplitJobDetail] = []
    for job_id in job_ids:
        job = get_job(job_id)
        if job:
            jobs.append(job)
    return jobs


def read_rows(job_id: str, page: int = 1, page_size: int = 200) -> tuple[list[dict[str, Any]], int]:
    if not redis_available():
        return [], 0

    client = get_redis()
    rows_key = f"{ROWS_PREFIX}{job_id}"
    total = client.llen(rows_key)
    start = max(page - 1, 0) * page_size
    end = start + page_size - 1
    raw_rows = client.lrange(rows_key, start, end)
    return [json.loads(row) for row in raw_rows], total


def delete_job(job_id: str) -> SplitJobDetail | None:
    if not redis_available():
        return None

    client = get_redis()
    job = get_job(job_id)
    if job is None:
        return None

    pipe = client.pipeline()
    pipe.delete(f"{JOB_PREFIX}{job_id}")
    pipe.delete(f"{ROWS_PREFIX}{job_id}")
    pipe.zrem(INDEX_KEY, job_id)
    if job.cache_key:
        pipe.delete(job.cache_key)
    pipe.execute()
    return job
