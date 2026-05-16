"""
Test script for the Agent Assignment Module.

Feeds classified records through the assigner and validates that each
platform maps to the correct agent / tool pairing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.agent_assigner import assign_agents

# ---------------------------------------------------------------------------
# 1.  Prepare test input (mimics classification-step output)
# ---------------------------------------------------------------------------

classified_records = [
    {"url": "https://www.youtube.com/watch?v=abc123",                "platform": "YouTube_Public",  "type": "video"},
    {"url": "https://youtu.be/xyz789",                               "platform": "YouTube_Public",  "type": "video"},
    {"url": "https://www.youtube.com/watch?v=priv001&token=secret",  "platform": "YouTube_Private", "type": "video"},
    {"url": "https://drive.google.com/file/d/1aBcDeFgHiJk/view",    "platform": "Google_Drive",    "type": "video"},
    {"url": "https://cdn.example.com/videos/demo.mp4",               "platform": "Direct_MP4",     "type": "video"},
    {"url": "https://streaming.site.io/live/stream.m3u8",            "platform": "Direct_MP4",     "type": "video"},
    {"url": "https://vimeo.com/112233",                               "platform": "Unknown",        "type": "unknown"},
]

# ---------------------------------------------------------------------------
# 2.  Run assigner
# ---------------------------------------------------------------------------

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

assigned = assign_agents(classified_records)

# ---------------------------------------------------------------------------
# 3.  Display
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print(f"  AGENT-ASSIGNED URLs  ({len(assigned)} records)")
print("=" * 70)
print(json.dumps(assigned, indent=2))

# ---------------------------------------------------------------------------
# 4.  Assertions
# ---------------------------------------------------------------------------

expected = {
    "https://www.youtube.com/watch?v=abc123":                ("youtube_agent", "yt-dlp"),
    "https://youtu.be/xyz789":                               ("youtube_agent", "yt-dlp"),
    "https://www.youtube.com/watch?v=priv001&token=secret":  ("youtube_agent", "yt-dlp"),
    "https://drive.google.com/file/d/1aBcDeFgHiJk/view":    ("drive_agent",   "gdown"),
    "https://cdn.example.com/videos/demo.mp4":               ("direct_agent",  "requests"),
    "https://streaming.site.io/live/stream.m3u8":            ("direct_agent",  "requests"),
    "https://vimeo.com/112233":                              ("fallback_agent","requests"),
}

print("\n--- Validation ---")
all_pass = True
for rec in assigned:
    exp_agent, exp_tool = expected[rec["url"]]
    a_ok = rec["agent"] == exp_agent
    t_ok = rec["tool"]  == exp_tool
    status = "PASS" if (a_ok and t_ok) else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}]  {rec['url'][:50]:<50}  => {rec['agent']:<16} / {rec['tool']}")

print()
print("[ALL TESTS PASSED]" if all_pass else "[SOME TESTS FAILED]")
if not all_pass:
    sys.exit(1)
