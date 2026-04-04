#!/bin/bash
# Start the FastAPI backend server

# Set the Google Drive credentials path (optional)
# export GOOGLE_CREDENTIALS_JSON=/path/to/service-account.json

# For Windows Command Prompt:
# set GOOGLE_CREDENTIALS_JSON=C:\path\to\service-account.json
# python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
