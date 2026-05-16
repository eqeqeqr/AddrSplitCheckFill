"""Bing web search module with Tavily-compatible response format.

Drop-in replacement for Tavily search API, using Bing HTML scraping.
Includes anti-blocking measures: UA rotation, request jitter, CAPTCHA detection, retry.
"""

from __future__ import annotations

import asyncio
import random
import re
import uuid
from html import unescape
from time import monotonic
from typing import Any

import httpx

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

_REQUEST_TIMEOUT = 20
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0
_MAX_RESULTS = 10

_search_semaphore = asyncio.Semaphore(2)
_last_request_time: float = 0.0


def _random_headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


def _is_blocked(html: str) -> bool:
    indicators = [
        "captcha",
        "unusual traffic",
        "blocked",
        "robot",
        "verify you are human",
        "To continue, please",
        "访问频率",
        "验证码",
    ]
    lower = html.lower()
    return any(indicator.lower() in lower for indicator in indicators)


async def _rate_limit_delay() -> None:
    global _last_request_time
    now = monotonic()
    elapsed = now - _last_request_time
    min_interval = random.uniform(1.0, 2.5)
    if elapsed < min_interval:
        await asyncio.sleep(min_interval - elapsed)
    _last_request_time = monotonic()


def _parse_bing_results(html: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for block in re.findall(r'<li\s+class="b_algo"[^>]*>.*?</li>', html, flags=re.S):
        title_match = re.search(
            r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>\s*</h2>',
            block,
            flags=re.S,
        )
        if not title_match:
            continue

        url = unescape(title_match.group(1)).strip()
        title = unescape(re.sub(r"<[^>]+>", "", title_match.group(2))).strip()

        if not url.startswith("http"):
            continue

        content = ""
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.S)
        if snippet_match:
            content = unescape(re.sub(r"<[^>]+>", "", snippet_match.group(1))).strip()

        if not content:
            div_match = re.search(r'<div\s+class="b_caption"[^>]*>(.*?)</div>', block, flags=re.S)
            if div_match:
                content = unescape(re.sub(r"<[^>]+>", "", div_match.group(1))).strip()

        if not title and not content:
            continue

        position = len(results) + 1
        score = round(max(0.1, 1.0 - (position - 1) * 0.08), 6)

        results.append({
            "title": title,
            "url": url,
            "content": content,
            "score": score,
            "raw_content": None,
        })

        if len(results) >= limit:
            break

    return results


async def bing_search(
    query: str,
    *,
    max_results: int = _MAX_RESULTS,
    include_raw_content: bool = False,
) -> dict[str, Any]:
    """Search Bing and return results in Tavily-compatible format.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (1-10).
        include_raw_content: If True, fetch full page content for each result.

    Returns:
        dict with Tavily-compatible schema:
        {
            "query": str,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [{"url", "title", "content", "score", "raw_content"}],
            "response_time": float,
            "request_id": str,
        }
    """
    if not query or not query.strip():
        return _empty_response(query, "查询不能为空")

    query = query.strip()
    max_results = max(1, min(max_results, _MAX_RESULTS))
    request_id = uuid.uuid4().hex[:12]
    started = monotonic()

    for attempt in range(_MAX_RETRIES):
        try:
            async with _search_semaphore:
                await _rate_limit_delay()

                async with httpx.AsyncClient(
                    timeout=_REQUEST_TIMEOUT,
                    follow_redirects=True,
                    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                ) as client:
                    resp = await client.get(
                        "https://www.bing.com/search",
                        params={"q": query, "mkt": "zh-CN", "count": str(max_results * 2)},
                        headers=_random_headers(),
                    )

                if resp.status_code == 429:
                    wait = _RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0.5, 1.5)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code != 200:
                    if attempt < _MAX_RETRIES - 1:
                        await asyncio.sleep(_RETRY_BASE_DELAY * (attempt + 1))
                        continue
                    return _empty_response(query, f"Bing 返回 HTTP {resp.status_code}", request_id, started)

                html = resp.text

                if _is_blocked(html):
                    if attempt < _MAX_RETRIES - 1:
                        wait = _RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                        await asyncio.sleep(wait)
                        continue
                    return _empty_response(query, "Bing 返回了验证码或拦截页面", request_id, started)

                results = _parse_bing_results(html, max_results)

                if include_raw_content and results:
                    results = await _enrich_raw_content(client, results)

                return {
                    "query": query,
                    "follow_up_questions": None,
                    "answer": None,
                    "images": [],
                    "results": results,
                    "response_time": round(monotonic() - started, 2),
                    "request_id": request_id,
                }

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_BASE_DELAY * (attempt + 1))
                continue
            return _empty_response(query, f"网络错误：{exc}", request_id, started)
        except Exception as exc:
            return _empty_response(query, f"搜索异常：{exc}", request_id, started)

    return _empty_response(query, "搜索重试耗尽", request_id, started)


async def _enrich_raw_content(
    client: httpx.AsyncClient,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    async def fetch_one(result: dict[str, Any]) -> None:
        url = result.get("url", "")
        if not url:
            return
        try:
            await asyncio.sleep(random.uniform(0.3, 0.8))
            resp = await client.get(url, headers=_random_headers(), timeout=10)
            if resp.status_code == 200:
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()
                result["raw_content"] = text[:20000]
        except Exception:
            pass

    tasks = [fetch_one(r) for r in results[:5]]
    await asyncio.gather(*tasks)
    return results


def _empty_response(
    query: str,
    error: str = "",
    request_id: str = "",
    started: float | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "query": query,
        "follow_up_questions": None,
        "answer": None,
        "images": [],
        "results": [],
        "response_time": round(monotonic() - started, 2) if started else 0.0,
        "request_id": request_id or uuid.uuid4().hex[:12],
    }
    if error:
        response["error"] = error
    return response
