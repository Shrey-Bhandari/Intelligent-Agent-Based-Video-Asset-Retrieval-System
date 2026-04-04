<!-- =========================================
   VIDEO ASSET PROCESSING UI - INTEGRATION GUIDE
   ========================================= -->

# Updated Response Format

The FastAPI backend now returns:

```json
{
  "records": [
    {
      "url": "https://www.youtube.com/watch?v=abc123",
      "source_column": "Video Link",
      "platform": "YouTube_Public",
      "type": "video",
      "agent": "youtube_agent",
      "tool": "yt-dlp",
      "status": "success",
      "message": "Downloaded -> downloads/youtube_ab12.mp4",
      "timestamp": "2026-04-04T12:00:00.000000+00:00",
      "drive_file_id": "1abc2def3ghi4jkl5mno6pqr",
      "drive_link": "https://drive.google.com/file/d/1abc2def3ghi4jkl5mno6pqr/view"
    },
    {
      "url": "https://vimeo.com/987654",
      "source_column": "Backup Link",
      "platform": "Vimeo",
      "type": "video",
      "agent": "fallback_agent",
      "tool": "requests",
      "status": "failure",
      "message": "No dedicated agent for platform 'Vimeo'",
      "timestamp": "2026-04-04T12:00:01.000000+00:00",
      "drive_file_id": null,
      "drive_link": null
    }
  ],
  "summary": {
    "total": 2,
    "success": 1,
    "failure": 1
  }
}
```

# Result Card HTML Structure

Each result card now includes a View/Download button for successful records:

```html
<div class="result-card">
  <!-- Status indicator -->
  <div class="result-status success">✓</div>

  <!-- Content section -->
  <div class="result-content">
    <div class="result-url">https://www.youtube.com/watch?v=abc123</div>
    <div class="result-message">Downloaded -> downloads/youtube_ab12.mp4</div>
    <div class="result-time">Apr 4, 12:00 PM</div>
  </div>

  <!-- Action section -->
  <div class="result-action">
    <!-- Successful record with drive_link -->
    <a
      href="https://drive.google.com/file/d/1abc2def3ghi4jkl5mno6pqr/view"
      target="_blank"
      rel="noopener noreferrer"
      class="view-btn"
    >
      <svg
        class="view-btn-icon"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
        />
      </svg>
      View / Download
    </a>
  </div>
</div>
```

# Failure Cases

## No drive_link (upload pending or failed)

```html
<div class="result-action">
  <span class="view-btn disabled">Upload pending</span>
</div>
```

## Failed download

```html
<div class="result-card">
  <div class="result-status failure">✕</div>
  <div class="result-content">
    <div class="result-url">https://vimeo.com/987654</div>
    <div class="result-message">No dedicated agent for platform 'Vimeo'</div>
    <div class="result-time">Apr 4, 12:00 PM</div>
  </div>
  <div class="result-action">
    <span class="view-btn disabled">Failed</span>
  </div>
</div>
```

# CSS Button Styles

The "View / Download" button features:

- **Green gradient** background (success color)
- **Hover effect**: lifts up with shadow
- **Icon**: play/download SVG
- **Disabled state**: grayed out, no click
- **Smooth transitions**: 0.3s ease

Hover animation:

```css
.view-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(16, 185, 129, 0.3);
}
```

# JavaScript Implementation

The frontend now:

1. Parses the nested `data.records` structure
2. Extracts `drive_link` from each successful record
3. Renders clickable buttons that open Google Drive links
4. Shows status badges (✓ for success, ✕ for failure)
5. Animates cards with stagger effect

# Starting the Backend

## Windows (Command Prompt):

```cmd
set GOOGLE_CREDENTIALS_JSON=C:\path\to\service-account.json
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Or use:

```cmd
start_api.bat
```

## Linux / macOS (Bash):

```bash
export GOOGLE_CREDENTIALS_JSON=/path/to/service-account.json
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Or:

```bash
bash start_api.sh
```

# API Endpoint

```
POST http://localhost:8000/api/process-videos/

Headers:
  Content-Type: multipart/form-data

Body:
  file: <CSV or Excel file>

Response:
  200 OK → { "records": [...], "summary": {...} }
  400 Bad Request → { "detail": "error message" }
  413 Payload Too Large → { "detail": "file size exceeded" }
  500 Internal Server Error → { "detail": "processing failed" }
```

# Features

✅ Video extraction from URLs
✅ Automatic classification (YouTube, Google Drive, Direct MP4, Vimeo)
✅ Parallel execution with retry logic
✅ Google Drive upload with folder hierarchy
✅ Persistent JSONL logging
✅ Real-time download links
✅ Error handling & reporting
✅ Modern, animated UI
✅ Mobile-responsive design
✅ Production-ready code

# Next Steps

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set up Google Drive credentials:
   - Create service account JSON
   - Export as environment variable

3. Start backend:

   ```bash
   python -m uvicorn api:app --host 0.0.0.0 --port 8000
   ```

4. Open frontend:
   - Open `index.html` in a browser
   - Or serve via HTTP server

5. Upload a file and watch the magic happen!
