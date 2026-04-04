"""
Test script for the URL Classification Module.

Feeds a representative set of URL records through the classifier and
validates the output platform assignments.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.url_classifier import classify_urls

# ---------------------------------------------------------------------------
# 1.  Prepare test input (mimics extraction-step output)
# ---------------------------------------------------------------------------

test_records = [
    # YouTube - Public
    {"url": "https://www.youtube.com/watch?v=abc123",           "source_column": "Video URL"},
    {"url": "https://youtu.be/xyz789",                          "source_column": "Video URL"},
    {"url": "https://youtube.com/shorts/short999",              "source_column": "Video URL"},

    # YouTube - Private (has auth token)
    {"url": "https://www.youtube.com/watch?v=priv001&token=secret", "source_column": "Video URL"},

    # Google Drive
    {"url": "https://drive.google.com/file/d/1aBcDeFgHiJk/view",   "source_column": "Video URL"},

    # Direct MP4 / CDN
    {"url": "https://cdn.example.com/videos/demo.mp4",              "source_column": "Video URL"},
    {"url": "https://media.host.com/rec.mp4?token=abc&expire=123",  "source_column": "Video URL"},
    {"url": "https://streaming.site.io/live/stream.m3u8",           "source_column": "Backup Link"},

    # Unknown (not matching any rule)
    {"url": "https://vimeo.com/112233",                             "source_column": "Video URL"},
    {"url": "https://cdn.backup.io/training.mp4",                   "source_column": "Backup Link"},
]

# ---------------------------------------------------------------------------
# 2.  Run classifier
# ---------------------------------------------------------------------------

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

classified = classify_urls(test_records)

# ---------------------------------------------------------------------------
# 3.  Display results
# ---------------------------------------------------------------------------

print("\n" + "=" * 64)
print(f"  CLASSIFIED URLs  ({len(classified)} records)")
print("=" * 64)
print(json.dumps(classified, indent=2))

# ---------------------------------------------------------------------------
# 4.  Quick assertions
# ---------------------------------------------------------------------------

expected = {
    "https://www.youtube.com/watch?v=abc123":             "YouTube_Public",
    "https://youtu.be/xyz789":                            "YouTube_Public",
    "https://youtube.com/shorts/short999":                "YouTube_Public",
    "https://www.youtube.com/watch?v=priv001&token=secret": "YouTube_Private",
    "https://drive.google.com/file/d/1aBcDeFgHiJk/view": "Google_Drive",
    "https://cdn.example.com/videos/demo.mp4":            "Direct_MP4",
    "https://media.host.com/rec.mp4?token=abc&expire=123":"Direct_MP4",
    "https://streaming.site.io/live/stream.m3u8":         "Direct_MP4",
    "https://vimeo.com/112233":                           "Unknown",
    "https://cdn.backup.io/training.mp4":                 "Direct_MP4",
}

print("\n--- Validation ---")
all_pass = True
for rec in classified:
    exp = expected.get(rec["url"])
    got = rec["platform"]
    status = "PASS" if got == exp else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}]  {rec['url'][:55]:<55}  => {got:<20} (expected {exp})")

print()
if all_pass:
    print("[ALL TESTS PASSED]")
else:
    print("[SOME TESTS FAILED]")
    sys.exit(1)
