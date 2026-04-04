"""
Agent Execution Layer (Step 4 — Refactored)
=============================================
Executes download tasks via platform-specific agent functions.

Key upgrades:
  - **Retry logic** — each task retried up to ``MAX_RETRIES`` times.
  - **Parallel execution** — ``ThreadPoolExecutor`` for concurrency.
  - **JSONL logging** — every result appended to ``logs/download_log.jsonl``.
  - **In-place mutation** — records updated, not replaced.
"""

from __future__ import annotations

import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_RETRIES: int = 2
MAX_WORKERS: int = 4
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "download_log.jsonl"


# ---------------------------------------------------------------------------
# JSONL logger
# ---------------------------------------------------------------------------

def _append_jsonl(record: dict) -> None:
    """Append a single JSON line to the persistent log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Individual agent functions (simulated)
# ---------------------------------------------------------------------------

def youtube_agent(record: dict) -> None:
    """Simulate yt-dlp download."""
    url = record["url"]
    time.sleep(random.uniform(0.05, 0.15))
    if "broken" in url.lower():
        raise RuntimeError("yt-dlp returned non-zero exit code (simulated)")
    record["message"] = f"Downloaded via yt-dlp -> youtube_{hash(url) & 0xFFFF:04x}.mp4"


def drive_agent(record: dict) -> None:
    """Simulate gdown download (placeholder)."""
    url = record["url"]
    time.sleep(random.uniform(0.05, 0.15))
    if "broken" in url.lower():
        raise RuntimeError("gdown: access denied (simulated)")
    record["message"] = f"Downloaded via gdown -> gdrive_{hash(url) & 0xFFFF:04x}.mp4"


def direct_agent(record: dict) -> None:
    """Simulate HTTP stream download."""
    url = record["url"]
    time.sleep(random.uniform(0.05, 0.15))
    if "broken" in url.lower():
        raise RuntimeError("HTTP 404 (simulated)")
    record["message"] = f"Streamed via requests -> direct_{hash(url) & 0xFFFF:04x}.mp4"


def fallback_agent(record: dict) -> None:
    """Always fails — platform has no dedicated handler."""
    raise RuntimeError(f"No dedicated agent for platform '{record.get('platform')}'")


# ---------------------------------------------------------------------------
# Agent dispatcher
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, Callable[[dict], None]] = {
    "youtube_agent":  youtube_agent,
    "drive_agent":    drive_agent,
    "direct_agent":   direct_agent,
    "fallback_agent": fallback_agent,
}


# ---------------------------------------------------------------------------
# Single-record execution with retries
# ---------------------------------------------------------------------------

def _execute_one(record: dict) -> dict:
    """
    Execute a single download task with up to ``MAX_RETRIES`` retries.
    Mutates the record **in-place** and returns it.
    """
    agent_name = record.get("agent", "fallback_agent")
    handler = _DISPATCH.get(agent_name, fallback_agent)

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 2):          # 1 try + MAX_RETRIES
        try:
            handler(record)
            record["status"] = "success"
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
            logger.info(
                "  [OK]  %-16s %s  (attempt %d)",
                agent_name, record["url"][:60], attempt,
            )
            _append_jsonl(record)
            return record
        except Exception as exc:
            last_error = str(exc)
            if attempt <= MAX_RETRIES:
                logger.warning(
                    "  [RETRY %d/%d]  %-16s %s — %s",
                    attempt, MAX_RETRIES, agent_name,
                    record["url"][:60], last_error,
                )
                time.sleep(0.1 * attempt)               # brief back-off

    # All attempts exhausted
    record["status"] = "failure"
    record["message"] = last_error
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    logger.error(
        "  [FAIL] %-16s %s — %s",
        agent_name, record["url"][:60], last_error,
    )
    _append_jsonl(record)
    return record


# ---------------------------------------------------------------------------
# Batch execution (parallel)
# ---------------------------------------------------------------------------

def execute_all(records: list[dict], *,
                max_workers: int = MAX_WORKERS) -> list[dict]:
    """
    Execute all assigned records using a thread pool.

    Mutates records **in-place** and returns the same list.
    """
    logger.info("=== Execution started (%d tasks, %d workers) ===",
                len(records), max_workers)

    # ThreadPoolExecutor to run downloads concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_execute_one, rec): idx
                   for idx, rec in enumerate(records)}
        for future in as_completed(futures):
            future.result()                              # propagate unexpected errors

    success = sum(1 for r in records if r["status"] == "success")
    failure = len(records) - success
    logger.info(
        "=== Execution finished | total: %d | success: %d | failure: %d ===",
        len(records), success, failure,
    )
    return records
