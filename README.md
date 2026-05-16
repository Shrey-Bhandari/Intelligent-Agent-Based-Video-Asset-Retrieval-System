# Intelligent Agent-Based Video Asset Retrieval System (IAVARS)

**A production-ready pipeline framework for bulk YouTube video downloads with intelligent error handling, parallel execution, and comprehensive audit logging.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-darkgreen?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-required-red)](https://github.com/yt-dlp/yt-dlp)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Feature Status](#feature-status)
3. [Key Features](#key-features)
4. [System Architecture](#system-architecture)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Project Structure](#project-structure)
9. [API Reference](#api-reference)
10. [Pipeline Stages](#pipeline-stages)
11. [Error Handling](#error-handling)
12. [Troubleshooting](#troubleshooting)
13. [Contributing](#contributing)

---

## Overview

IAVARS is a production-grade video retrieval system that automates bulk downloading of videos from multiple platforms. The system employs a four-stage pipeline architecture: URL extraction and normalization, rule-based platform classification, intelligent agent assignment, and parallel execution with fault tolerance.

**Primary Use Cases:**

- Content archivists requiring bulk video curation
- Marketing teams managing video asset libraries
- Media professionals archiving online content
- Research teams collecting video datasets

---

## Feature Status

### Fully Implemented

- **YouTube Video Downloads** – Full support via `yt-dlp` (public videos)
- **Parallel Execution** – Thread pool with configurable workers (default: 4)
- **Retry Logic** – Automatic exponential backoff (up to 2 retries)
- **JSONL Audit Logging** – Structured logs with detailed error categorization
- **FastAPI Backend** – REST API with OpenAPI documentation
- **Web UI** – Responsive HTML/CSS/JavaScript interface with real-time progress
- **Rule-Based Classification** – Deterministic URL parsing (no ML/LLM required)
- **Error Analysis** – 13+ categorized error types with human-readable explanations
- **File Upload** – Drag-and-drop Excel/CSV file processing via web interface

### Partially Implemented

- **Google Drive Downloads** – Agent exists but only simulates downloads
- **Direct MP4/CDN Downloads** – Agent exists but only simulates downloads
- **Vimeo Downloads** – Platform detection works, agent not implemented

### Not Yet Implemented

- **Cloud Storage (Google Drive Upload)** – Storage module exists but not integrated
- **LLM-Based Classification** – Uses rule-based matching only (not ML/AI)
- **Hierarchical Cloud Organization** – No automatic folder creation/syncing
- **Report Generation** – No HTML/XLSX report generation yet

---

## Key Features

### 1. **YouTube Video Downloads (Production Ready)**

- Download public YouTube videos using `yt-dlp`
- Handles rate limiting and retries gracefully
- Semantic filename generation (consistent hashing)
- Parallel downloads with worker pools

### 2. **Rule-Based URL Classification**

- Fast, deterministic platform detection
- Supports: YouTube (public/private), Google Drive, Vimeo, Direct MP4/CDN
- No external API calls required
- Pattern matching with URL parsing

### 3. **High-Performance Processing**

- Parallel execution via `ThreadPoolExecutor`
- Configurable retry behavior with exponential backoff
- Memory-efficient streaming
- Automatic duplicate detection and removal

### 4. **Comprehensive Error Handling**

- 13+ categorized failure reasons
- Machine-readable error codes in JSONL logs
- Human-readable explanations for each error
- Examples:
  - `yt_dlp_not_installed` – Missing YouTube downloader
  - `video_removed_guidelines` – Community guideline violation
  - `video_unavailable` – Deleted or restricted video
  - `platform_not_supported` – Unsupported platform (Vimeo)

### 5. **Structured Logging**

- JSONL format (one JSON object per line)
- Tracks: URL, platform, status, timestamp, failure reason, error details
- Human and machine-readable
- Easy integration with analytics/dashboards

### 6. **Web-Based Interface**

- FastAPI REST backend with Swagger/ReDoc docs
- Responsive HTML/CSS/JavaScript frontend
- File upload with validation
- Real-time processing status updates

---

## System Architecture

### Pipeline Stages (4 Stages)

```
┌─────────────────────┐
│  1. URL Extraction  │  Parse spreadsheet, detect URLs, deduplicate
└────────────┬────────┘
             │
             ▼
┌─────────────────────┐
│  2. Classification  │  Classify platform (YouTube, GDrive, Vimeo, MP4)
└────────────┬────────┘
             │
             ▼
┌─────────────────────┐
│  3. Agent Assignment│  Assign appropriate agent (youtube_agent, drive_agent, etc.)
└────────────┬────────┘
             │
             ▼
┌─────────────────────┐
│ 4. Parallel Exec    │  Download with retries, log results to JSONL
└─────────────────────┘
```

### Module Breakdown

| Module              | Purpose                          | Status            | Key File                     |
| ------------------- | -------------------------------- | ----------------- | ---------------------------- |
| **URL Extractor**   | Parse Excel/CSV, extract URLs    | ✅ Working        | `pipeline/url_extractor.py`  |
| **URL Classifier**  | Classify platform by URL pattern | ✅ Working        | `pipeline/url_classifier.py` |
| **Agent Assigner**  | Map URLs to agents               | ✅ Working        | `pipeline/agent_assigner.py` |
| **Agent Executor**  | Download via agents, retry, log  | ✅ Working        | `pipeline/agent_executor.py` |
| **Storage Layer**   | Google Drive upload              | ❌ Not integrated | `pipeline/storage.py`        |
| **FastAPI Backend** | REST API & web server            | ✅ Working        | `api.py`                     |
| **Frontend UI**     | Web interface                    | ✅ Working        | `index.html`, `script.js`    |

---

## Installation

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **pip** or **conda**
- **yt-dlp** (for YouTube downloads)

### Step 1: Clone & Navigate

```bash
git clone <repository-url>
cd IAVARS
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Contents of requirements.txt:**

```
pandas>=2.0
openpyxl>=3.1
requests>=2.31
google-api-python-client>=2.0
google-auth>=2.0
fastapi>=0.95
uvicorn>=0.21
python-multipart>=0.0.5
yt-dlp>=2023.0.0
```

### Step 4: Install yt-dlp System Binary

**Windows (via pip):**

```bash
pip install yt-dlp --upgrade
```

**macOS:**

```bash
brew install yt-dlp
```

**Linux (Debian/Ubuntu):**

```bash
sudo apt-get install yt-dlp
```

**Linux (RedHat/CentOS):**

```bash
sudo yum install yt-dlp
```

Verify:

```bash
yt-dlp --version
```

---

## Configuration

### Environment Variables (Optional)

```bash
# Not required for basic YouTube downloads, but useful for future cloud features
export GOOGLE_CREDENTIALS_JSON="/path/to/service_account.json"
export GOOGLE_DRIVE_FOLDER_ID="your_folder_id"
```

### Application Settings

Edit `pipeline/agent_executor.py`:

```python
MAX_RETRIES = 2              # Number of retries per download
MAX_WORKERS = 4              # Thread pool workers
TIMEOUT_SECONDS = 300        # Download timeout in seconds
```

Edit `pipeline/url_extractor.py`:

```python
CHUNK_SIZE = 50_000          # Excel parsing chunk size
SUPPORTED_EXTENSIONS = {".xlsx", ".csv"}  # Allowed file types
```

---

## Usage

### Option 1: Web Interface (Recommended)

1. **Start the server:**

   ```bash
   python api.py
   ```

2. **Open browser:**
   Navigate to `http://localhost:8000`

3. **Upload spreadsheet:**
   - Drag & drop Excel/CSV file
   - View real-time progress
   - Download videos to `/downloads/` folder

4. **Check logs:**
   Open `logs/download_log.jsonl` for detailed results

### Option 2: Python API (Programmatic)

```python
from pipeline.main import run_pipeline

# Process a spreadsheet
records, summary = run_pipeline("path/to/videos.xlsx")

# Results
print(f"Total: {summary['total']}")
print(f"Success: {summary['success']}")
print(f"Failure: {summary['failure']}")

# Access individual records
for record in records:
    if record["status"] == "success":
        print(f"✅ {record['url']} -> {record['message']}")
    else:
        print(f"❌ {record['url']} ({record['failure_reason']})")
```

### Option 3: Command Line

```bash
python run.py tests/sample_input.csv
```

### Option 4: Start API Server with Custom Port

```bash
python api.py --host 0.0.0.0 --port 8080
```

---

## Project Structure

```
IAVARS/
├── api.py                          # FastAPI backend
├── index.html                      # Web UI
├── styles.css                      # Styling
├── script.js                       # Frontend logic
├── run.py                          # CLI entry point
├── report_generator.py             # Report utilities
├── requirements.txt                # Dependencies
│
├── pipeline/                       # Core modules
│   ├── __init__.py
│   ├── main.py                     # Main pipeline orchestrator
│   ├── url_extractor.py            # Excel/CSV parsing
│   ├── url_classifier.py           # Platform classification
│   ├── agent_assigner.py           # Agent mapping
│   ├── agent_executor.py           # Download execution & logging
│   └── storage.py                  # Google Drive integration (not in use)
│
├── tests/                          # Test data
│   ├── sample_input.csv
│   ├── test_*.py
│
├── downloads/                      # Downloaded videos (local storage)
├── logs/
│   └── download_log.jsonl          # Audit logs
│
├── .gitignore
├── README.md                       # This file
└── system_architecture.md          # Detailed architecture docs
```

---

## API Reference

### GET /health

Health check endpoint.

**Response:**

```json
{ "status": "ok" }
```

### POST /api/process-videos/

Processes a spreadsheet containing video URLs.

**Parameters:**

- `file` (multipart/form-data) - Excel or CSV file containing video URLs

Response:

```json
{
  "records": [
    {
      "url": "https://www.youtube.com/watch?v=abc123",
      "platform": "YouTube_Public",
      "status": "success",
      "message": "Downloaded -> downloads/youtube_abc.mp4",
      "timestamp": "2026-04-06T12:00:00Z",
      "download_link": "http://localhost:8000/downloads/youtube_abc.mp4",
      "failure_reason": null
    }
  ],
  "summary": {
    "total": 10,
    "success": 8,
    "failure": 2
  }
}
```

### GET /downloads/{filename}

Retrieves a downloaded video file.

### Interactive Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Pipeline Stages

### Stage 1: URL Extraction

**Input:** Excel/CSV file  
**Process:**

- Read spreadsheet with pandas
- Detect URL columns via regex
- Validate and sanitize URLs
- Remove duplicates
- Extract metadata (title, category, source column)

**Output:** List of records with URLs and metadata

### Stage 2: URL Classification

**Input:** List of URLs  
**Process:**

- Parse each URL's domain and path
- Match against platform patterns (YouTube, GDrive, Vimeo, MP4)
- Classify type (video, document, etc.)

**Output:** Classified records with platform and type fields

**Platform Detection Rules:**

- `youtube.com`, `youtu.be`, `youtube.com/shorts` → `YouTube_Public`
- YouTube + auth params → `YouTube_Private`
- `drive.google.com` → `Google_Drive`
- `vimeo.com` → `Vimeo`
- `.mp4`, `.m3u8`, `.webm` extension → `Direct_MP4`
- Unknown → `Unknown`

### Stage 3: Agent Assignment

**Input:** Classified records  
**Process:**

- Map platform to agent (youtube_agent, drive_agent, direct_agent, fallback_agent)
- Map agent to tool (yt-dlp, gdown, requests)

**Output:** Records with agent and tool assignments

### Stage 4: Parallel Execution

**Input:** Agent-assigned records  
**Process:**

- Spawn thread pool (default: 4 workers)
- Each worker executes assigned agent
- Agent downloads video to `/downloads/`
- Retry on failure (up to 2 retries)
- Log result to JSONL with error categorization

**Output:** Downloaded files + JSONL logs

---

## Error Handling

All failures are categorized in JSONL logs with machine-readable codes and human-friendly descriptions:

| Failure Reason             | Cause                    | Solution                               |
| -------------------------- | ------------------------ | -------------------------------------- |
| `yt_dlp_not_installed`     | yt-dlp not in PATH       | `pip install yt-dlp`                   |
| `video_removed_guidelines` | YouTube policy violation | Video permanently unavailable          |
| `video_unavailable`        | Deleted or restricted    | Contact uploader                       |
| `video_age_restricted`     | Age-restricted content   | Requires authentication                |
| `video_deleted`            | Uploader deleted video   | Check URL                              |
| `video_private`            | Private/restricted       | Request access                         |
| `access_denied`            | Permission denied (403)  | Check credentials                      |
| `network_error`            | Connection timeout       | Check internet                         |
| `invalid_url`              | URL not found (404)      | Verify URL                             |
| `drive_download_failed`    | Google Drive error       | File may be restricted                 |
| `platform_not_supported`   | No agent available       | Platform not implemented (e.g., Vimeo) |
| `unknown_error`            | Unexpected error         | Check logs                             |

**Example JSONL Log Entry:**

```json
{
  "url": "https://www.youtube.com/watch?v=abc123",
  "status": "failure",
  "message": "yt-dlp executable not found. Install yt-dlp and ensure it is on PATH.",
  "platform": "YouTube_Public",
  "timestamp": "2026-04-06T07:04:25.818381+00:00",
  "link_status": "broken",
  "failure_reason": "yt_dlp_not_installed",
  "failure_details": "YouTube downloader (yt-dlp) is not installed or not in system PATH. Install it with: pip install yt-dlp"
}
```

---

## Troubleshooting

### Issue: `yt-dlp executable not found`

**Solution:**

```bash
pip install yt-dlp --upgrade
yt-dlp --version  # Verify
```

### Issue: YouTube video not downloading despite being available

**Solution:** Check logs for specific error:

```bash
cat logs/download_log.jsonl | grep "failure_reason"
```

### Issue: API fails to start on port 8000

**Solution:** Use different port:

```bash
python api.py --port 8001
```

### Issue: Uploads fail due to file size

**Solution:** Default max is 50MB. Increase in `api.py`:

```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
```

### Issue: Performance slow with many videos

**Solution:** Increase workers in `pipeline/agent_executor.py`:

```python
MAX_WORKERS = 8  # Increase from 4
```

### Issue: `ModuleNotFoundError: No module named 'google.oauth2'`

**Solution:** Install Google dependencies:

```bash
pip install google-auth google-api-python-client
```

---

## 📊 Sample Input Format

### CSV Example

```csv
Video Link,Title,Category,Campaign
https://www.youtube.com/watch?v=abc123,Brand Promo,Commercial,Q1_2026
https://www.youtube.com/watch?v=xyz789,Tutorial,Educational,Q2_2026
https://cdn.example.com/video.mp4,Archived,Archive,Backup
```

### Excel Format

- Columns: Video Link, Title, Category, Campaign (flexible)
- Multiple sheets supported
- Up to 1,000,000+ rows with chunked processing

---

## Security

- **Credentials Management:** Store `.env` and service account credentials outside version control
- **File Upload Restrictions:** Maximum 50MB file size; only `.csv` and `.xlsx` formats accepted
- **Cross-Origin Resource Sharing:** Configure `allow_origins` in `api.py` for production deployments
- **Audit Logging:** JSONL logs contain URLs; implement appropriate access controls

---

## Testing

### Run Unit Tests

```bash
pytest tests/
pytest tests/test_url_classifier.py -v
```

### Test with Sample Data

```bash
python run.py tests/sample_input.csv
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## Known Limitations

1. **Rule-Based Classification Only** – No LLM/AI integration; deterministic and transparent
2. **Local Storage Only** – Videos are stored locally; cloud synchronization not yet implemented
3. **Limited Platform Support** – Google Drive, Vimeo, and Direct MP4 agents are placeholder implementations
4. **No Report Generation** – HTML and XLSX report functionality not yet implemented
5. **No User Authentication** – API endpoints are unauthenticated; intended for internal use only

---

## Roadmap

Planned enhancements for future releases:

- [ ] Google Drive upload integration and hierarchical folder organization
- [ ] Vimeo platform download support
- [ ] Real-time direct MP4/CDN download capability
- [ ] Automated HTML and XLSX report generation
- [ ] Database backend for asset tracking and metadata management
- [ ] API authentication, authorization, and rate limiting
- [ ] Web-based dashboard for job monitoring and analytics

---

## Support

For technical support and troubleshooting:

- **Review Logs:** Examine `logs/download_log.jsonl` for detailed execution records
- **Consult Error Reference:** See the Error Handling section for categorized failure types
- **Report Issues:** Submit GitHub issues with detailed reproduction steps and logs

---

## 📝 License

MIT License – See LICENSE file

---

**Last Updated:** April 6, 2026  
**Status:** ✅ Core features production-ready | ⚙️ Cloud features in development
