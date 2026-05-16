"""
FastAPI Backend for Video Asset Retrieval System
=================================================

Exposes the pipeline via HTTP API:
- POST /api/process-videos/ — upload file, process, upload to Drive, return results

Required environment:
- GOOGLE_CREDENTIALS_JSON — path to service account JSON

"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline.main import run_pipeline
from report_generator import load_jsonl, generate_report

logger = logging.getLogger(__name__)

# =========================================================================
# CONFIGURATION
# =========================================================================

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
PROCESSING_STATE = {}

# =========================================================================
# MODELS
# =========================================================================

class ProcessResponseItem(BaseModel):
    url: str
    source_column: str | None = None
    platform: str
    type: str
    agent: str
    tool: str
    status: str
    message: str
    timestamp: str
    download_link: str | None = None

class ProcessResponse(BaseModel):
    records: list[ProcessResponseItem]
    summary: dict

class ProgressUpdate(BaseModel):
    session_id: str
    status: str  # "extracting", "processing", "uploading", "complete"
    total_links: int = 0
    current_index: int = 0
    current_url: str | None = None
    success_count: int = 0
    failure_count: int = 0
    message: str = ""

# =========================================================================
# FASTAPI APP
# =========================================================================

app = FastAPI(
    title="Video Asset Processing API",
    description="Process video URLs from spreadsheets and download videos locally",
    version="1.0.0",
)

downloads_dir = Path("downloads").resolve()
app.mount(
    "/downloads",
    StaticFiles(directory=str(downloads_dir), html=False),
    name="downloads",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# ENDPOINTS
# =========================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Get current processing progress for a session."""
    progress = PROCESSING_STATE.get(session_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Session not found")
    return progress

@app.post("/api/process-videos/")
async def process_videos(request: Request, file: UploadFile = File(...)):
    """
    Process a CSV or Excel file containing video URLs.

    Returns:
    {
        "session_id": "uuid",
        "records": [...],
        "summary": {...}
    }

    Query the GOOGLE_CREDENTIALS_JSON environment variable to find the
    service account credentials file.
    """
    session_id = str(uuid.uuid4())
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is required")

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Expected {ALLOWED_EXTENSIONS}, got {file_ext}",
            )

        # Read file into temp location
        file_size = 0
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size {file_size} exceeds maximum {MAX_FILE_SIZE}",
            )

        # Save to temporary file
        with NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            # Update progress: extraction
            PROCESSING_STATE[session_id] = {
                "session_id": session_id,
                "status": "extracting",
                "total_links": 0,
                "current_index": 0,
                "current_url": None,
                "success_count": 0,
                "failure_count": 0,
                "message": "Extracting URLs from file...",
            }

            # Step 1: Run the pipeline (extraction → classification → assignment → execution)
            logger.info("Running pipeline on uploaded file: %s [%s]", file.filename, session_id)
            records, summary = run_pipeline(tmp_path, max_workers=4)

            # Update progress: extracted
            total = len(records)
            PROCESSING_STATE[session_id].update({
                "status": "processing",
                "total_links": total,
                "message": f"Found {total} URLs. Processing now...",
            })

            # Update progress counts as we process
            for idx, record in enumerate(records):
                PROCESSING_STATE[session_id].update({
                    "current_index": idx + 1,
                    "current_url": record.get("url", "")[:100],
                    "success_count": sum(1 for r in records[:idx+1] if r.get("status") == "success"),
                    "failure_count": sum(1 for r in records[:idx+1] if r.get("status") == "failure"),
                    "message": f"Processing {idx + 1}/{total}: {record.get('platform', 'Unknown')}",
                })

            base_url = str(request.base_url).rstrip("/")

            # Step 2: Build HTTP-accessible download links for successful records
            for record in records:
                if record.get("status") == "success":
                    download_link = record.get("download_link")
                    if isinstance(download_link, str) and download_link.startswith("/downloads/"):
                        record["download_link"] = f"{base_url}{download_link}"
                        continue

                    message = record.get("message", "")
                    if "Downloaded ->" in message:
                        local_path = message.split("Downloaded ->")[-1].strip()
                        original_path = Path(local_path)
                        if original_path.exists() and original_path.parent.name == "downloads":
                            record["download_link"] = f"{base_url}/downloads/{original_path.name}"
                        else:
                            record["download_link"] = None
                    else:
                        record["download_link"] = None
                else:
                    record["download_link"] = None

            # Step 3: Complete
            PROCESSING_STATE[session_id].update({
                "status": "complete",
                "message": f"Complete! {summary['success']} passed, {summary['failure']} failed",
            })

            # Return response with session_id
            return {
                "session_id": session_id,
                "records": records,
                "summary": summary
            }

        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during video processing: %s", exc)
        PROCESSING_STATE[session_id] = {
            "session_id": session_id,
            "status": "error",
            "message": str(exc),
            "total_links": 0,
            "current_index": 0,
            "success_count": 0,
            "failure_count": 0,
        }
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(exc)}",
        ) from exc

@app.options("/api/process-videos/")
async def options_process_videos():
    """CORS preflight handler."""
    return {"allowed_methods": ["POST"]}

# =========================================================================
# ERROR HANDLERS
# =========================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# =========================================================================
# LOGGING SETUP
# =========================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# =========================================================================
# MAIN
# =========================================================================

@app.get("/api/download-report")
async def download_report():
    """Generate and return the processing report as plain text."""
    log_path = Path("logs/download_log.jsonl")
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    try:
        records = load_jsonl(str(log_path))
        report = generate_report(records)
        return PlainTextResponse(report, media_type="text/plain")
    except Exception as exc:
        logger.exception("Error generating report: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate report")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
