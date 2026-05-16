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
        f.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


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


def _is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def _build_youtube_filename(url: str) -> str:
    short_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"youtube_{short_hash}"


def youtube_agent(record: dict) -> None:
    """Download a YouTube video using yt-dlp and update the record with the real file path."""
    url = record["url"]
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(parents=True, exist_ok=True)

    base_name = _build_youtube_filename(url)
    yt_dlp_exec = _ensure_yt_dlp_available()
    has_ffmpeg = _is_ffmpeg_available()

    # Build command: prefer merge-output-format (no re-encode) over recode-video
    output_template = str(downloads_dir / f"{base_name}.%(ext)s")
    command = [
        yt_dlp_exec,
        "-o", output_template,
        "--no-warnings",
        "--no-playlist",
    ]

    if has_ffmpeg:
        # Merge to mp4 container without re-encoding (fast)
        command.extend(["--merge-output-format", "mp4"])
    else:
        # Without ffmpeg, request best single mp4 stream
        command.extend(["-f", "best[ext=mp4]/best"])

    command.append(url)

    logger.info("  [yt-dlp] Running: %s", " ".join(command))

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
            timeout=300,  # 5-minute timeout per video
        )
        logger.info("  [yt-dlp] stdout: %s", completed.stdout[-500:] if completed.stdout else "(empty)")
    except subprocess.TimeoutExpired:
        raise RuntimeError("yt-dlp timed out after 300 seconds")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"yt-dlp failed (exit {exc.returncode}): {exc.output.strip()[-500:]}"
        ) from exc

    # Find the downloaded file — yt-dlp may produce .mp4, .webm, .mkv etc.
    downloaded_path = None
    for ext in (".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv"):
        candidate = downloads_dir / f"{base_name}{ext}"
        if candidate.exists():
            downloaded_path = candidate
            break

    if downloaded_path is None:
        # Fallback: check for any file starting with base_name
        matches = list(downloads_dir.glob(f"{base_name}.*"))
        if matches:
            downloaded_path = matches[0]

    if downloaded_path is None:
        raise RuntimeError(
            f"yt-dlp reported success but output file was not found: {downloads_dir / base_name}.*"
        )

    record["message"] = f"Downloaded -> {downloaded_path.as_posix()}"
    record["download_link"] = f"/downloads/{downloaded_path.name}"


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
# Error categorization & analysis
# ---------------------------------------------------------------------------

def _categorize_failure_reason(error_message: str, platform: str) -> str:
    """
    Analyze error message and return a categorized failure reason.
    
    Returns one of:
    - yt_dlp_not_installed
    - video_removed_guidelines
    - video_unavailable
    - video_age_restricted
    - video_deleted
    - video_private
    - access_denied
    - network_error
    - timeout
    - invalid_url
    - unknown_error
    """
    msg_lower = error_message.lower()
    
    # YouTube-specific errors
    if "yt-dlp executable not found" in error_message:
        return "yt_dlp_not_installed"
    
    if "community guidelines" in msg_lower or "violated" in msg_lower:
        return "video_removed_guidelines"
    
    if "not available" in msg_lower or "no longer available" in msg_lower:
        return "video_unavailable"
    
    if "age restricted" in msg_lower or "only users 18+" in msg_lower:
        return "video_age_restricted"
    
    if "video has been removed" in msg_lower or "removed for" in msg_lower:
        return "video_removed_guidelines"
    
    if "deleted" in msg_lower or "no longer exists" in msg_lower:
        return "video_deleted"
    
    if "private" in msg_lower or "not accessible" in msg_lower:
        return "video_private"
    
    if "access denied" in msg_lower or "forbidden" in msg_lower or "403" in msg_lower:
        return "access_denied"
    
    if "connection" in msg_lower or "timeout" in msg_lower or "timed out" in msg_lower:
        return "network_error"
    
    if "404" in msg_lower or "not found" in msg_lower:
        return "invalid_url"
    
    if "gdown" in msg_lower or "google drive" in msg_lower.lower():
        if "access denied" in msg_lower:
            return "access_denied"
        return "drive_download_failed"
    
    if "requests" in msg_lower or "http" in msg_lower:
        return "http_error"
    
    # Platform not supported
    if "no dedicated agent" in msg_lower:
        return "platform_not_supported"
    
    return "unknown_error"


def _build_execution_summary(record: dict) -> dict:
    """Build a structured summary for JSONL logging."""
    status = record.get("status", "failure")
    
    summary = {
        "url": record.get("url", ""),
        "status": status,
        "message": record.get("message", ""),
        "timestamp": record.get("timestamp", ""),
        "platform": record.get("platform", ""),
        "link_status": "active" if status == "success" else "broken",
    }
    
    # Add failure reason if the download failed
    if status == "failure":
        failure_reason = _categorize_failure_reason(
            record.get("message", ""),
            record.get("platform", "")
        )
        summary["failure_reason"] = failure_reason
        summary["failure_details"] = _get_failure_details(failure_reason)
    
    return summary


def _get_failure_details(failure_reason: str) -> str:
    """Return human-readable explanation for the failure reason."""
    details = {
        "yt_dlp_not_installed": "YouTube downloader (yt-dlp) is not installed or not in system PATH. Install it with: pip install yt-dlp",
        "video_removed_guidelines": "Video has been removed by YouTube for violating Community Guidelines. Content is no longer available.",
        "video_unavailable": "Video is no longer available. It may have been deleted or removed by the uploader.",
        "video_age_restricted": "Video is age-restricted. Requires authentication or cannot be downloaded programmatically.",
        "video_deleted": "Video has been deleted by the uploader or is no longer accessible.",
        "video_private": "Video is private or restricted. Not accessible without proper authentication.",
        "access_denied": "Access denied to the resource. May require authentication or permissions.",
        "network_error": "Network connection error or timeout occurred during download.",
        "timeout": "Download request timed out. Server may be slow or unreachable.",
        "invalid_url": "URL is invalid or resource not found (404 error).",
        "drive_download_failed": "Google Drive download failed. File may be restricted or unavailable.",
        "http_error": "HTTP error during download. Check URL validity and network connection.",
        "platform_not_supported": "Platform is not supported by the system. No dedicated agent configured.",
        "unknown_error": "An unknown error occurred during download. Check logs for details.",
    }
    return details.get(failure_reason, "Unknown error details")


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
