from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Awaitable

from fastapi import WebSocket


class ProgressConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._latest: dict[str, dict[str, Any]] = {}
        self._full_state_fetchers: dict[str, Callable[[], Awaitable[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    def register_full_state_fetcher(self, job_id: str, fetcher: Callable[[], Awaitable[dict[str, Any]]]) -> None:
        self._full_state_fetchers[job_id] = fetcher

    def unregister_full_state_fetcher(self, job_id: str) -> None:
        self._full_state_fetchers.pop(job_id, None)

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[job_id].add(websocket)
            latest = self._latest.get(job_id)
            fetcher = self._full_state_fetchers.get(job_id)

        if fetcher:
            try:
                full_state = await fetcher()
                await websocket.send_json(full_state)
            except Exception:
                pass

        if latest:
            await websocket.send_json(latest)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(job_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(job_id, None)

    async def publish(self, job_id: str, payload: dict[str, Any]) -> None:
        message = {"job_id": job_id, **payload}
        async with self._lock:
            self._latest[job_id] = message
            connections = list(self._connections.get(job_id, set()))

        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except RuntimeError:
                stale.append(websocket)

        if stale:
            async with self._lock:
                current = self._connections.get(job_id)
                if current:
                    for websocket in stale:
                        current.discard(websocket)


progress_manager = ProgressConnectionManager()
