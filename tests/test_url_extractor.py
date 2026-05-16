"""
Test script for the URL Extraction Module.

Creates a sample CSV with mixed columns (some containing URLs, some not),
runs the extractor, and prints the JSON output.
"""

import csv
import json
import sys
from pathlib import Path

# Ensure the pipeline package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.url_extractor import extract_urls

# ---------------------------------------------------------------------------
# 1.  Generate a sample CSV test file
# ---------------------------------------------------------------------------

SAMPLE_CSV = Path("tests/sample_input.csv")
SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)

sample_rows = [
    # Header
    ["Asset ID", "Video Title", "Video URL", "Backup Link", "Campaign"],

    # Normal YouTube
    ["A001", "Brand Promo Q1", "https://www.youtube.com/watch?v=abc123", "", "Q1 Campaign"],
    ["A002", "Reel Cut v2", "https://youtu.be/xyz789", "", "Q1 Campaign"],

    # Google Drive
    ["A003", "Behind the Scenes", "https://drive.google.com/file/d/1aBcDeFgHiJk/view", "", "Q2 Campaign"],

    # Direct MP4 link
    ["A004", "Product Demo", "https://cdn.example.com/videos/demo.mp4", "", "Q2 Campaign"],

    # Duplicate of A001 (should be removed)
    ["A005", "Brand Promo COPY", "https://www.youtube.com/watch?v=abc123", "", "Q1 Campaign"],

    # URL with trailing spaces + extra slashes (tests normalisation)
    ["A006", "Messy Link", "  https://www.youtube.com//watch?v=messy456  ", "", "Q3 Campaign"],

    # URL in backup column too
    ["A007", "Training Video", "https://vimeo.com/112233", "https://cdn.backup.io/training.mp4", "Internal"],

    # Row with no URLs at all
    ["A008", "Missing", "N/A", "N/A", "Q3 Campaign"],

    # YouTube Shorts
    ["A009", "Short Clip", "https://youtube.com/shorts/short999", "", "Q4 Campaign"],

    # Another direct link with query params
    ["A010", "Webinar Recording", "https://media.host.com/rec.mp4?token=abc&expire=123", "", "Q4 Campaign"],
]

with open(SAMPLE_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(sample_rows)

print(f"[OK] Sample CSV created at: {SAMPLE_CSV}  ({len(sample_rows) - 1} data rows)\n")

# ---------------------------------------------------------------------------
# 2.  Run the extractor
# ---------------------------------------------------------------------------

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

results = extract_urls(SAMPLE_CSV)

# ---------------------------------------------------------------------------
# 3.  Display results
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print(f"  EXTRACTED URLs  ({len(results)} unique)")
print("=" * 60)
print(json.dumps(results, indent=2))
