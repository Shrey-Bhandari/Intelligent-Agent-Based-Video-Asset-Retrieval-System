"""
Unified Pipeline  (``pipeline.main``)
======================================
Single entry point that chains all four processing stages.

Usage::

    from pipeline.main import run_pipeline
    records, summary = run_pipeline("sample_assets.xlsx")
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pipeline.url_extractor import extract_urls
from pipeline.intelligent_router import route_urls
from pipeline.agent_executor import execute_all
from pipeline.storage import upload_records_to_drive

logger = logging.getLogger(__name__)


def run_pipeline(csv_path: str | Path, *,
                 max_workers: int = 4) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Run the full video-asset retrieval pipeline.

    Parameters
    ----------
    csv_path : str | Path
        Path to a ``.csv`` or ``.xlsx`` spreadsheet containing asset URLs.
    max_workers : int
        Thread-pool size for parallel execution.

    Returns
    -------
    (records, summary)
        *records* — list of unified dicts with all stages populated.
        *summary* — ``{"total": X, "success": Y, "failure": Z}``.
    """
    csv_path = Path(csv_path)
    logger.info("=" * 60)
    logger.info("  PIPELINE START  |  %s", csv_path.name)
    logger.info("=" * 60)

    # Step 1 — Extraction
    records = extract_urls(csv_path)
    if not records:
        logger.warning("No URLs found. Pipeline finished with 0 records.")
        return [], {"total": 0, "success": 0, "failure": 0}

    # Step 2 & 3 — Intelligent Routing (Classification & Agent Assignment)
    route_urls(records)

    # Step 4 — Execution
    execute_all(records, max_workers=max_workers)

    # Step 5 — Google Drive Sync
    creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_path and Path(creds_path).exists():
        logger.info("Uploading assets and logs to Google Drive using credentials at %s...", creds_path)
        records = upload_records_to_drive(records, creds_path)
    else:
        logger.warning(
            "GOOGLE_CREDENTIALS_JSON is not set or the file does not exist. Skipping upload."
        )

    # Summary
    success = sum(1 for r in records if r["status"] == "success")
    failure = sum(1 for r in records if r["status"] == "failure")
    summary = {"total": len(records), "success": success, "failure": failure}

    logger.info("=" * 60)
    logger.info("  PIPELINE COMPLETE")
    logger.info("  Total: %d  |  Success: %d  |  Failure: %d",
                summary["total"], summary["success"], summary["failure"])
    logger.info("=" * 60)

    return records, summary
