@echo off
REM Start the FastAPI backend server on Windows

REM Set the Google Drive credentials path (optional)
REM set GOOGLE_CREDENTIALS_JSON=C:\path\to\service-account.json

python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

pause
