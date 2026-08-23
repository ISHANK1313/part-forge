"""Thin Gemini LLM wrapper: JSON outputs, temp 0, retry+repair once, SQLite cache.

Uses the REST API directly to avoid SDK version drift. Cache keyed
sha256(stage|model|prompt) so re-runs are free (architecture.md §3).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "llm_cache.sqlite"


class LLMUnavailable(Exception):
    """No API key configured or provider unreachable after retries."""


_conn: sqlite3.Connection | None = None
# RLock: call_json holds this while calling _db(), which acquires it again.
_db_lock = threading.RLock()

# Measured 2026-08-23: provider latency ~42 s/call regardless of model/size
# (upstream throttling). Pipeline MUST parallelise (see main.py --workers).
READ_TIMEOUT_S = 150.0


def load_env(env_path: str | Path | None = None) -> None:
    """Populate os.environ from a .env file (no external dependency)."""
    path = Path(env_path) if env_path else Path(__file__).resolve().parents[2] / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _db() -> sqlite3.Connection:
    # check_same_thread=False + explicit lock: safe under ThreadPoolExecutor.
    global _conn
    with _db_lock:
        if _conn is None:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(CACHE_PATH, check_same_thread=False)
            _conn.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
            _conn.commit()
    return _conn


def _key(stage: str, model: str, prompt: str) -> str:
    return hashlib.sha256(f"{stage}|{model}|{prompt}".encode()).hexdigest()


def api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or None


def model_name() -> str:
    return os.environ.get("PARTFORGE_MODEL", "gemini-3.1-flash-lite")


def available() -> bool:
    return api_key() is not None


def _post(prompt: str) -> dict:
    url = API_URL.format(model=model_name())
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": api_key()},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 2048,
                # disable hidden reasoning burn (measured: JSON replies in ~3s)
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
        timeout=(10, READ_TIMEOUT_S),
    )
    if resp.status_code == 429:
        raise LLMUnavailable("rate limited")
    resp.raise_for_status()
    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return _loads_json(text)


def _loads_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        t = t[start:end + 1]
    return json.loads(t)


def call_json(stage: str, prompt: str, *, retries: int = 2) -> dict | None:
    """Return parsed JSON dict for a stage prompt, or None on failure.

    Cached by content hash; network errors degrade gracefully so callers fall
    back to deterministic-only fields.
    """
    key = _key(stage, model_name(), prompt)
    with _db_lock:
        row = _db().execute("SELECT v FROM cache WHERE k=?", (key,)).fetchone()
    if row:
        return json.loads(row[0])

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = _post(prompt)
            if not isinstance(result, dict):
                result = {"_raw": result}
            with _db_lock:
                _db().execute("INSERT OR REPLACE INTO cache VALUES (?, ?)",
                              (key, json.dumps(result)))
                _db().commit()
            return result
        except LLMUnavailable as exc:
            last_err = exc
            time.sleep(2 * (attempt + 1))
        except (requests.RequestException, ValueError, KeyError) as exc:
            last_err = exc
            # one repair-style retry: append hint and try once more (I-05 fix)
            if attempt == 0 and retries > 0:
                prompt = (f"{prompt}\n\nYour previous response was invalid JSON or "
                          f"violated the schema: {exc}\nRespond with corrected JSON only.")
            time.sleep(1)
    print(f"[llm] stage={stage} failed after retries: {last_err}")
    return None


def repair_json(stage: str, prompt: str, bad_output_hint: str) -> dict | None:
    """One repair retry with the failure reason appended."""
    return call_json(
        f"{stage}:repair",
        f"{prompt}\n\nYour previous response was invalid JSON or violated the "
        f"schema: {bad_output_hint}\nRespond again with corrected JSON only.",
        retries=0,
    )
