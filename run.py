#!/usr/bin/env python
"""
run.py — CLI entry-point for the Video Asset Retrieval Pipeline
================================================================

Usage:
    python run.py                       # defaults to sample_asset.csv
    python run.py path/to/file.csv
    python run.py path/to/file.xlsx
"""

import json
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so ``pipeline`` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.main import run_pipeline


def main() -> None:
    # Configure console logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-7s | %(message)s",
    )

    # Resolve input file
    input_file = sys.argv[1] if len(sys.argv) > 1 else "sample_asset.csv"
    input_path = Path(input_file)

    if not input_path.exists():
        logging.error("File not found: %s", input_path)
        sys.exit(1)

    # Run the pipeline
    records, summary = run_pipeline(input_path)

    # Print final JSON output
    print("\n" + "=" * 60)
    print("  FINAL RECORDS")
    print("=" * 60)
    print(json.dumps(records, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print()


if __name__ == "__main__":
    main()
