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
from pathlib import Path
from typing import Any

from pipeline.url_extractor import extract_urls
from pipeline.url_classifier import classify_urls
from pipeline.agent_assigner import assign_agents
from pipeline.agent_executor import execute_all

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

    # Step 2 — Classification
    classify_urls(records)

    # Step 3 — Agent assignment
    assign_agents(records)

    # Step 4 — Execution
    execute_all(records, max_workers=max_workers)

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
