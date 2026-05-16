"""
Intelligent URL Router (Step 2 & 3 Combined)
==============================================
Uses an LLM (via OpenAI compatible API) to classify URLs and assign agents.
Mutates records in-place.
"""

from __future__ import annotations

import os
import re
import logging
import json
from pathlib import Path
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load the project-level .env file once when this module is imported.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GPT_API_KEY = os.getenv("GPT_API_KEY")
GPT_BASE_URL = os.getenv("GPT_BASE_URL", "https://integrate.api.nvidia.com/v1")
GPT_MODEL = os.getenv("GPT_MODEL", "openai/gpt-oss-120b")


def _build_client() -> OpenAI | None:
    """Create the OpenAI-compatible client from environment configuration."""
    if not GPT_API_KEY:
        logger.warning(
            "Missing GPT_API_KEY. LLM routing will fall back to regex-based classification."
        )
        return None

    return OpenAI(
        api_key=GPT_API_KEY,
        base_url=GPT_BASE_URL,
    )


client = _build_client()

class RoutingResult(BaseModel):
    platform: str
    type: str
    agent: str
    tool: str


# ---------------------------------------------------------------------------
# Valid values for validation
# ---------------------------------------------------------------------------
VALID_PLATFORMS = {
    "YouTube_Public", "YouTube_Private", "Google_Drive",
    "Direct_MP4", "Vimeo", "Unknown",
}
VALID_AGENTS = {
    "youtube_agent", "drive_agent", "direct_agent", "fallback_agent",
}
VALID_TOOLS = {"yt-dlp", "gdown", "requests"}


SYSTEM_PROMPT = """
You are an intelligent URL routing assistant for a video asset pipeline.
Your job is to analyze a given URL and determine the standard platform, the content type,
and which agent and tool should be assigned to handle downloading the content.

Platform options mapping:
- "YouTube Public" URL -> platform: "YouTube_Public", agent: "youtube_agent", tool: "yt-dlp", type: "video"
- "YouTube Private" URL (has authentication query params like token, auth, key, si) -> platform: "YouTube_Private", agent: "youtube_agent", tool: "yt-dlp", type: "video"
- "Google Drive" URL (drive.google.com, docs.google.com) -> platform: "Google_Drive", agent: "drive_agent", tool: "gdown", type: "video"
- "Direct MP4" URL (ends with .mp4, .m3u8, .webm, .mkv, .avi, etc) -> platform: "Direct_MP4", agent: "direct_agent", tool: "requests", type: "video"
- "Vimeo" URL (vimeo.com) -> platform: "Vimeo", agent: "fallback_agent", tool: "requests", type: "video"
- Any other URL -> platform: "Unknown", agent: "fallback_agent", tool: "requests", type: "unknown"

You MUST output ONLY a valid JSON object matching the requested schema. No conversational text.
Example output format:
{
  "platform": "YouTube_Public",
  "type": "video",
  "agent": "youtube_agent",
  "tool": "yt-dlp"
}
"""


# ---------------------------------------------------------------------------
# Robust JSON extraction
# ---------------------------------------------------------------------------

def _extract_json_from_response(raw: str) -> dict | None:
    """
    Try multiple strategies to extract a valid JSON object from LLM output.
    
    Strategy order:
    1. Direct parse (already clean JSON)
    2. Strip markdown fences then parse
    3. Regex extract first {...} block
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown fences
    cleaned = text
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: regex extract first JSON object
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Strategy 4: regex extract nested JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _validate_routing(parsed: dict) -> dict:
    """
    Validate and normalize parsed routing fields.
    Falls back to safe defaults for any invalid/hallucinated values.
    """
    platform = parsed.get("platform", "Unknown")
    content_type = parsed.get("type", "unknown")
    agent = parsed.get("agent", "fallback_agent")
    tool = parsed.get("tool", "requests")

    # Normalize: if platform is not in our known set, mark Unknown
    if platform not in VALID_PLATFORMS:
        logger.warning("LLM returned unknown platform '%s', defaulting to 'Unknown'", platform)
        platform = "Unknown"

    if agent not in VALID_AGENTS:
        logger.warning("LLM returned unknown agent '%s', defaulting to 'fallback_agent'", agent)
        agent = "fallback_agent"

    if tool not in VALID_TOOLS:
        logger.warning("LLM returned unknown tool '%s', defaulting to 'requests'", tool)
        tool = "requests"

    return {
        "platform": platform,
        "type": content_type,
        "agent": agent,
        "tool": tool,
    }


# ---------------------------------------------------------------------------
# Regex-based fallback classifier (no LLM needed)
# ---------------------------------------------------------------------------

def _regex_classify(url: str) -> dict:
    """Classify a URL using regex patterns when LLM is unavailable."""
    url_lower = url.lower()

    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        # Check for private/unlisted indicators
        if any(param in url_lower for param in ["token=", "auth=", "key=", "si="]):
            return {"platform": "YouTube_Private", "type": "video",
                    "agent": "youtube_agent", "tool": "yt-dlp"}
        return {"platform": "YouTube_Public", "type": "video",
                "agent": "youtube_agent", "tool": "yt-dlp"}

    if "drive.google.com" in url_lower or "docs.google.com" in url_lower:
        return {"platform": "Google_Drive", "type": "video",
                "agent": "drive_agent", "tool": "gdown"}

    if "vimeo.com" in url_lower:
        return {"platform": "Vimeo", "type": "video",
                "agent": "fallback_agent", "tool": "requests"}

    video_extensions = (".mp4", ".m3u8", ".webm", ".mkv", ".avi", ".mov", ".flv")
    if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in video_extensions):
        return {"platform": "Direct_MP4", "type": "video",
                "agent": "direct_agent", "tool": "requests"}

    return {"platform": "Unknown", "type": "unknown",
            "agent": "fallback_agent", "tool": "requests"}


def route_urls(records: list[dict]) -> list[dict]:
    """
    Classify each record's URL and set ``platform``, ``type``, ``agent``, and ``tool`` **in-place**.
    Returns the same list for chaining convenience.
    """
    counters: dict[str, int] = {}

    for rec in records:
        url = rec.get("url", "")
        if not url:
            rec.update({
                "platform": "Unknown",
                "type": "unknown",
                "agent": "fallback_agent",
                "tool": "requests"
            })
            continue

        # If LLM client is not available, use regex fallback
        if client is None:
            result = _regex_classify(url)
            rec.update(result)
            counters[result["platform"]] = counters.get(result["platform"], 0) + 1
            logger.info("  [REGEX] %-20s -> %s", url[:50], result["platform"])
            continue

        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this URL and output JSON: {url}"}
                ],
                temperature=0.1,
                max_tokens=256
            )
            raw_content = response.choices[0].message.content.strip()
            logger.info("  [LLM RAW] URL: %s\n    Response: %s", url[:60], raw_content[:200])

            parsed = _extract_json_from_response(raw_content)

            if parsed is None:
                logger.error(
                    "  [LLM FAIL] Could not extract JSON from LLM response for %s. "
                    "Raw: %s. Falling back to regex.",
                    url[:60], raw_content[:200],
                )
                result = _regex_classify(url)
            else:
                result = _validate_routing(parsed)
                logger.info("  [LLM OK] %s -> platform=%s, agent=%s, tool=%s",
                            url[:50], result["platform"], result["agent"], result["tool"])

        except Exception as e:
            logger.error("  [LLM ERROR] URL %s: %s — falling back to regex", url[:60], str(e))
            result = _regex_classify(url)

        rec.update(result)
        counters[result["platform"]] = counters.get(result["platform"], 0) + 1

    logger.info(
        "Intelligent routing complete (%d URLs): %s",
        len(records),
        ", ".join(f"{k}: {v}" for k, v in sorted(counters.items())),
    )
    return records
