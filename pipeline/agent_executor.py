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

import hashlib
import json
import logging
import random
import shutil
import subprocess
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
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "download_log.jsonl"


# ---------------------------------------------------------------------------
# JSONL logger
# ---------------------------------------------------------------------------

def _append_jsonl(result: dict) -> None:
    """Append a single JSON line to the persistent log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Individual agent functions
# ---------------------------------------------------------------------------

def _ensure_yt_dlp_available() -> str:
    binary = shutil.which("yt-dlp")
    if binary:
        return binary

    binary = shutil.which("yt_dlp")
    if binary:
        return binary

    raise RuntimeError(
        "yt-dlp executable not found. Install yt-dlp and ensure it is on PATH."
    )


def _build_youtube_filename(url: str) -> str:
    short_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"youtube_{short_hash}.mp4"


def youtube_agent(record: dict) -> None:
    """Download a YouTube video using yt-dlp and update the record with the real file path."""
    url = record["url"]
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)

    output_name = _build_youtube_filename(url)
    output_template = str(downloads_dir / output_name)
    yt_dlp_exec = _ensure_yt_dlp_available()

    command = [
        yt_dlp_exec,
        "-o",
        output_template,
        "--recode-video",
        "mp4",
        "--no-warnings",
        url,
    ]

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"yt-dlp failed: {exc.returncode} - {exc.output.strip()}"
        ) from exc

    downloaded_path = downloads_dir / output_name
    if not downloaded_path.exists():
        raise RuntimeError(
            f"yt-dlp reported success but output file was not found: {downloaded_path}"
        )

    record["message"] = f"Downloaded -> {downloaded_path.as_posix()}"


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
# ---------------------------------------------------------------------------

def _build_execution_summary(record: dict) -> dict:
    return {
        "url": record.get("url", ""),
        "status": record.get("status", "failure"),
        "message": record.get("message", ""),
        "timestamp": record.get("timestamp", ""),
    }


def _execute_one(record: dict) -> dict:
    """
    Execute a single download task with up to ``MAX_RETRIES`` retries.
    Mutates the record **in-place** and returns a structured execution summary.
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
            result = _build_execution_summary(record)
            _append_jsonl(result)
            return result
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
    result = _build_execution_summary(record)
    _append_jsonl(result)
    return result


# ---------------------------------------------------------------------------
# Batch execution (parallel)
# ---------------------------------------------------------------------------
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
        future_to_record = {pool.submit(_execute_one, rec): rec
                            for rec in records}
        for future in as_completed(future_to_record):
            rec = future_to_record[future]
            try:
                future.result()
            except Exception as exc:
                rec["status"] = "failure"
                rec["message"] = str(exc)
                rec["timestamp"] = datetime.now(timezone.utc).isoformat()
                logger.error(
                    "  [ERROR] %-16s %s — %s",
                    rec.get("agent", "fallback_agent"), rec["url"][:60], exc,
                )
                _append_jsonl(_build_execution_summary(rec))

    success = sum(1 for r in records if r["status"] == "success")
    failure = len(records) - success
    logger.info(
        "=== Execution finished | total: %d | success: %d | failure: %d ===",
        len(records), success, failure,
    )
    return records
