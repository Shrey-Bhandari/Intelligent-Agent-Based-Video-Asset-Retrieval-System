"""
Agent Assignment Module (Step 3 — Refactored)
===============================================
Maps each classified record to a download agent + tool **in-place**.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform → (agent, tool) registry
# ---------------------------------------------------------------------------

_AGENT_REGISTRY: dict[str, tuple[str, str]] = {
    "YouTube_Public":  ("youtube_agent",  "yt-dlp"),
    "YouTube_Private": ("youtube_agent",  "yt-dlp"),
    "Google_Drive":    ("drive_agent",    "gdown"),
    "Direct_MP4":      ("direct_agent",   "requests"),
    "Vimeo":           ("fallback_agent", "requests"),
}

_DEFAULT_AGENT = ("fallback_agent", "requests")


# ---------------------------------------------------------------------------
# Public API  (mutates records in-place)
# ---------------------------------------------------------------------------

def assign_agents(records: list[dict]) -> list[dict]:
    """
    Set ``agent`` and ``tool`` on every record **in-place**.

    Returns the same list for chaining convenience.
    """
    counters: dict[str, int] = {}

    for rec in records:
        agent, tool = _AGENT_REGISTRY.get(rec.get("platform", ""), _DEFAULT_AGENT)
        rec["agent"] = agent
        rec["tool"] = tool
        counters[agent] = counters.get(agent, 0) + 1

    logger.info(
        "Agent assignment complete (%d URLs): %s",
        len(records),
        ", ".join(f"{k}: {v}" for k, v in sorted(counters.items())),
    )
    return records
