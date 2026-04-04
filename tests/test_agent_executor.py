"""
Test script for the Agent Execution Layer.

Runs a set of agent-assigned records (including a deliberate broken URL)
through the executor and validates statuses.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.agent_executor import execute_all

# ---------------------------------------------------------------------------
# 1.  Prepare test input (mimics agent-assignment output)
# ---------------------------------------------------------------------------

assigned_records = [
    # YouTube – should succeed
    {"url": "https://www.youtube.com/watch?v=abc123",                "platform": "YouTube_Public",  "agent": "youtube_agent",  "tool": "yt-dlp"},
    {"url": "https://youtu.be/xyz789",                               "platform": "YouTube_Public",  "agent": "youtube_agent",  "tool": "yt-dlp"},
    {"url": "https://www.youtube.com/watch?v=priv001&token=secret",  "platform": "YouTube_Private", "agent": "youtube_agent",  "tool": "yt-dlp"},

    # Google Drive – should succeed
    {"url": "https://drive.google.com/file/d/1aBcDeFgHiJk/view",    "platform": "Google_Drive",    "agent": "drive_agent",    "tool": "gdown"},

    # Direct – should succeed
    {"url": "https://cdn.example.com/videos/demo.mp4",               "platform": "Direct_MP4",      "agent": "direct_agent",   "tool": "requests"},

    # Unknown platform – fallback agent, always fails
    {"url": "https://vimeo.com/112233",                               "platform": "Unknown",         "agent": "fallback_agent", "tool": "requests"},

    # Broken link (contains "broken") – youtube_agent should simulate failure
    {"url": "https://www.youtube.com/watch?v=broken_link",           "platform": "YouTube_Public",  "agent": "youtube_agent",  "tool": "yt-dlp"},
]

# ---------------------------------------------------------------------------
# 2.  Execute
# ---------------------------------------------------------------------------

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

results = execute_all(assigned_records)

# ---------------------------------------------------------------------------
# 3.  Display
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print(f"  EXECUTION RESULTS  ({len(results)} tasks)")
print("=" * 70)
print(json.dumps(results, indent=2))

# ---------------------------------------------------------------------------
# 4.  Assertions
# ---------------------------------------------------------------------------

expected_status = {
    "https://www.youtube.com/watch?v=abc123":               "success",
    "https://youtu.be/xyz789":                              "success",
    "https://www.youtube.com/watch?v=priv001&token=secret": "success",
    "https://drive.google.com/file/d/1aBcDeFgHiJk/view":   "success",
    "https://cdn.example.com/videos/demo.mp4":              "success",
    "https://vimeo.com/112233":                             "failure",   # fallback
    "https://www.youtube.com/watch?v=broken_link":          "failure",   # "broken" keyword
}

print("\n--- Validation ---")
all_pass = True
for rec in results:
    exp = expected_status[rec["url"]]
    got = rec["status"]
    status = "PASS" if got == exp else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}]  {rec['agent']:<16} {rec['url'][:45]:<45}  => {got}")

print()
print("[ALL TESTS PASSED]" if all_pass else "[SOME TESTS FAILED]")
if not all_pass:
    sys.exit(1)
