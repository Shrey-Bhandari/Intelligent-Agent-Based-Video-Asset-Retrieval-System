"""
URL Classification Module (Step 2 — Refactored)
=================================================
Classifies URLs in-place using deterministic rule-based matching.

Supported platforms:  YouTube_Public, YouTube_Private, Google_Drive,
Direct_MP4, Vimeo, Unknown.

Each record's ``platform`` and ``type`` fields are **mutated in-place**.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform constants
# ---------------------------------------------------------------------------

YOUTUBE_PUBLIC  = "YouTube_Public"
YOUTUBE_PRIVATE = "YouTube_Private"
GOOGLE_DRIVE    = "Google_Drive"
DIRECT_MP4      = "Direct_MP4"
VIMEO           = "Vimeo"
UNKNOWN         = "Unknown"

# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

_YOUTUBE_DOMAINS: set[str] = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "www.youtu.be",
}

_GDRIVE_DOMAINS: set[str] = {
    "drive.google.com", "docs.google.com",
}

_VIMEO_DOMAINS: set[str] = {
    "vimeo.com", "www.vimeo.com", "player.vimeo.com",
}

_DIRECT_MEDIA_EXTENSIONS: set[str] = {
    ".mp4", ".m3u8", ".webm", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".ts",
}

_YOUTUBE_AUTH_PARAMS: set[str] = {"token", "auth", "key", "si"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_youtube_private(query_params: dict[str, list[str]]) -> bool:
    return bool(_YOUTUBE_AUTH_PARAMS & set(query_params.keys()))


def _has_media_extension(path: str) -> bool:
    lower = path.lower().split("?")[0].split("#")[0]
    return any(lower.endswith(ext) for ext in _DIRECT_MEDIA_EXTENSIONS)


# ---------------------------------------------------------------------------
# Single-URL classifier
# ---------------------------------------------------------------------------

def _classify_single(url: str) -> tuple[str, str]:
    """Return ``(platform, type)`` for a URL string."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return UNKNOWN, "unknown"

    domain = parsed.netloc.lower().split(":")[0]
    path = parsed.path or ""
    query = parse_qs(parsed.query)

    if domain in _YOUTUBE_DOMAINS:
        platform = YOUTUBE_PRIVATE if _is_youtube_private(query) else YOUTUBE_PUBLIC
        return platform, "video"

    if domain in _GDRIVE_DOMAINS:
        return GOOGLE_DRIVE, "video"

    if domain in _VIMEO_DOMAINS:
        return VIMEO, "video"

    if _has_media_extension(path):
        return DIRECT_MP4, "video"

    return UNKNOWN, "unknown"


# ---------------------------------------------------------------------------
# Public API  (mutates records in-place)
# ---------------------------------------------------------------------------

def classify_urls(records: list[dict]) -> list[dict]:
    """
    Classify each record's URL and set ``platform`` / ``type`` **in-place**.

    Returns the same list for chaining convenience.
    """
    counters: dict[str, int] = {}

    for rec in records:
        platform, content_type = _classify_single(rec.get("url", ""))
        rec["platform"] = platform
        rec["type"] = content_type
        counters[platform] = counters.get(platform, 0) + 1

    logger.info(
        "Classification complete (%d URLs): %s",
        len(records),
        ", ".join(f"{k}: {v}" for k, v in sorted(counters.items())),
    )
    return records
