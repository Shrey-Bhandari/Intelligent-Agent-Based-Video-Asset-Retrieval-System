"""
URL Extraction Module (Step 1 — Refactored)
=============================================
Extracts, deduplicates, and normalises URLs from Excel/CSV spreadsheets.

Returns **unified record dicts** with all pipeline fields pre-initialised
so that downstream stages can mutate the same objects in place.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse, quote, unquote

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r"https?://"
    r"[^\s\"'<>\\,\]\)]+",
    re.IGNORECASE,
)

CHUNK_SIZE: int = 50_000
SUPPORTED_EXTENSIONS = {".xlsx", ".csv"}


# ---------------------------------------------------------------------------
# Unified record factory
# ---------------------------------------------------------------------------

def _make_record(url: str, source_column: str) -> dict[str, Any]:
    """Create a pipeline record with every field pre-initialised."""
    return {
        "url": url,
        "source_column": source_column,
        "platform": "",
        "type": "",
        "agent": "",
        "tool": "",
        "status": "pending",
        "message": "",
        "timestamp": "",
    }


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------

def normalize_url(raw: str) -> str | None:
    """
    Normalise a URL: lowercase scheme/netloc, strip default ports,
    collapse slashes, re-encode path.  Returns *None* on invalid input.
    """
    url = raw.strip().strip("<>").strip()
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    if not parsed.scheme or not parsed.netloc:
        return None

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = re.sub(r"/+", "/", parsed.path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    path = quote(unquote(path), safe="/:@!$&'()*+,;=-._~")

    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def _sample_has_urls(series: pd.Series, sample_size: int = 50,
                     threshold: float = 0.3) -> bool:
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return False
    sample = non_null.head(sample_size)
    matches = sample.apply(lambda v: bool(URL_PATTERN.search(v)))
    return matches.mean() >= threshold


def detect_url_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that likely contain URLs."""
    return [str(col) for col in df.columns if _sample_has_urls(df[col])]


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def _read_file(filepath: Path, chunk_size: int = CHUNK_SIZE) -> pd.DataFrame:
    ext = filepath.suffix.lower()
    if ext == ".xlsx":
        logger.info("Reading Excel file: %s", filepath.name)
        return pd.read_excel(filepath, engine="openpyxl")
    if ext == ".csv":
        logger.info("Reading CSV file (chunk_size=%d): %s", chunk_size, filepath.name)
        chunks = list(pd.read_csv(filepath, chunksize=chunk_size, low_memory=False))
        return pd.concat(chunks, ignore_index=True)
    raise ValueError(f"Unsupported file type '{ext}'. Expected {SUPPORTED_EXTENSIONS}.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_urls(filepath: str | Path, *,
                 chunk_size: int = CHUNK_SIZE) -> list[dict[str, Any]]:
    """
    Extract, normalise, and deduplicate URLs from a spreadsheet.

    Returns a list of **unified pipeline records** (dicts) with status
    ``"pending"`` — ready for classification.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")
    if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{filepath.suffix}'. "
            f"Expected one of {SUPPORTED_EXTENSIONS}."
        )

    df = _read_file(filepath, chunk_size=chunk_size)
    logger.info("Loaded %d rows x %d columns", len(df), len(df.columns))

    url_columns = detect_url_columns(df)
    if not url_columns:
        logger.warning("No URL-bearing columns detected.")
        return []
    logger.info("Detected URL columns: %s", url_columns)

    seen: set[str] = set()
    records: list[dict[str, Any]] = []

    for col in url_columns:
        for value in df[col].dropna().astype(str):
            for match in URL_PATTERN.findall(value):
                normalised = normalize_url(match)
                if normalised and normalised not in seen:
                    seen.add(normalised)
                    records.append(_make_record(normalised, col))

    logger.info("Extraction complete: %d unique URLs", len(records))
    return records
