"""kie.ai unified-gateway HTTP client (single gateway).

Async jobs flow, confirmed against docs.kie.ai (2026-06):
  submit  -> POST /api/v1/jobs/createTask  body {"model": <slash-id>, "input": {...}}  -> data.taskId
  poll    -> GET  /api/v1/jobs/recordInfo?taskId=...  -> data.state + data.resultJson
  result  -> data.resultJson is a STRINGIFIED json -> double-parse -> resultUrls[]
  credit  -> GET  /api/v1/chat/credit  -> data (balance)

CRITICAL invariants:
- Completion is decided by data.state (waiting|queuing|generating|success|fail),
  NOT the envelope `code` (docs show an inconsistent code in one example).
- resultJson must be json.loads()'d a second time to reach resultUrls.
- Auth: Authorization: Bearer <KIE_API_KEY> (one key reaches all kie models).

This module is pure gateway plumbing — no model knowledge. The model slash-id
and per-model input shape come from lib/providers/model_map.py.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

BASE_URL = "https://api.kie.ai"
CREATE_TASK_PATH = "/api/v1/jobs/createTask"
RECORD_INFO_PATH = "/api/v1/jobs/recordInfo"
CREDIT_PATH = "/api/v1/chat/credit"

_STATE_SUCCESS = "success"
_STATE_FAIL = "fail"
_STATE_PENDING = {"waiting", "queuing", "generating"}


class KieError(RuntimeError):
    """kie gateway error (auth, submit, poll, or generation failure)."""


def api_key() -> Optional[str]:
    """Return a real KIE_API_KEY, or None (treats empty/comment-only as unset)."""
    from lib.env_loader import env_present

    if not env_present("KIE_API_KEY"):
        return None
    return (os.environ.get("KIE_API_KEY") or "").strip()


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _resolve_key(key: Optional[str]) -> str:
    key = key or api_key()
    if not key:
        raise KieError("KIE_API_KEY not set (empty or comment-only in .env)")
    return key


def get_credit(*, key: Optional[str] = None, timeout: int = 30) -> Any:
    """Return the account credit balance (also proves auth + connectivity)."""
    import requests

    key = _resolve_key(key)
    r = requests.get(f"{BASE_URL}{CREDIT_PATH}", headers=_headers(key), timeout=timeout)
    r.raise_for_status()
    return r.json().get("data")


def create_task(
    model: str,
    inputs: dict[str, Any],
    *,
    key: Optional[str] = None,
    callback_url: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Submit a generation job; return its taskId."""
    import requests

    key = _resolve_key(key)
    payload: dict[str, Any] = {"model": model, "input": inputs}
    if callback_url:
        payload["callBackUrl"] = callback_url
    r = requests.post(
        f"{BASE_URL}{CREATE_TASK_PATH}", headers=_headers(key), json=payload, timeout=timeout
    )
    r.raise_for_status()
    body = r.json()
    task_id = (body.get("data") or {}).get("taskId")
    if not task_id:
        raise KieError(f"createTask returned no taskId: {body}")
    return task_id


def parse_result_urls(record: dict[str, Any]) -> list[str]:
    """Extract output URLs from a success record.

    data.resultJson is a STRINGIFIED json blob -> parse it, then read resultUrls.
    """
    rj = record.get("resultJson")
    if not rj:
        return []
    parsed = json.loads(rj) if isinstance(rj, str) else rj
    urls = parsed.get("resultUrls") or []
    if isinstance(urls, str):
        urls = [urls]
    return list(urls)


def poll_task(
    task_id: str,
    *,
    key: Optional[str] = None,
    timeout: int = 600,
    interval: float = 5.0,
) -> dict[str, Any]:
    """Poll recordInfo until a terminal state. Returns the `data` record on success.

    Source of truth is data.state. Raises KieError on fail/timeout. Backoff
    mirrors the existing poll_heygen helper (interval x1.2, capped at 30s).
    """
    import requests

    key = _resolve_key(key)
    deadline = time.time() + timeout
    cur = interval
    while time.time() < deadline:
        r = requests.get(
            f"{BASE_URL}{RECORD_INFO_PATH}",
            headers=_headers(key),
            params={"taskId": task_id},
            timeout=30,
        )
        r.raise_for_status()
        record = r.json().get("data") or {}
        state = (record.get("state") or "").lower()
        if state == _STATE_SUCCESS:
            return record
        if state == _STATE_FAIL:
            raise KieError(
                f"kie task {task_id} failed: "
                f"{record.get('failCode')} {record.get('failMsg')}".strip()
            )
        # pending (waiting/queuing/generating/unknown) -> wait and retry
        time.sleep(min(cur, max(0.0, deadline - time.time())))
        cur = min(cur * 1.2, 30.0)
    raise KieError(f"kie task {task_id} timed out after {timeout}s")


def _detect_extension(url: str, content: bytes) -> str:
    """Pick the correct file extension. Content magic bytes WIN (kie sometimes
    serves a JPEG from a .png URL); fall back to the URL's path extension."""
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if content[4:8] == b"ftyp":
        return ".mp4"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    if content[:4] == b"OggS":
        return ".ogg"
    from urllib.parse import urlparse
    import os as _os

    ext = _os.path.splitext(urlparse(url).path)[1].lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".gif", ".mp3", ".wav"} else ""


def download(url: str, out_path: str | Path, *, timeout: int = 180) -> str:
    """Download a result URL; name the file from the REAL content type
    (e.g. JPEG -> .jpg), correcting the path extension. Returns the actual path."""
    import requests

    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    content = r.content
    p = Path(out_path)
    ext = _detect_extension(url, content)
    if ext and p.suffix.lower() != ext:
        p = p.with_suffix(ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return str(p)


def run_job(
    model: str,
    inputs: dict[str, Any],
    out_path: str | Path,
    *,
    key: Optional[str] = None,
    callback_url: Optional[str] = None,
    poll_timeout: int = 600,
) -> tuple[str, dict[str, Any], list[str]]:
    """submit -> poll -> download first result URL. Returns (path, record, urls)."""
    key = _resolve_key(key)
    task_id = create_task(model, inputs, key=key, callback_url=callback_url)
    record = poll_task(task_id, key=key, timeout=poll_timeout)
    record.setdefault("taskId", task_id)
    urls = parse_result_urls(record)
    if not urls:
        raise KieError(f"kie task {task_id} succeeded but returned no resultUrls: {record}")
    path = download(urls[0], out_path)
    return path, record, urls
