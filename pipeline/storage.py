"""
Google Drive Storage Layer
==========================

Uploads downloaded assets and the execution log to Google Drive using a
service account. This module is intentionally separate from the core
pipeline so that it can be invoked after execution completes.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except ImportError as exc:
    raise ImportError(
        "Missing Google Drive dependencies. Install 'google-api-python-client' and "
        "'google-auth' before using pipeline.storage.'"
    ) from exc

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT_FOLDER_NAME = "Root"
LOGS_FOLDER_NAME = "Logs"
UNKNOWN_FOLDER_NAME = "Unknown"
DRIVE_FOLDER_PATHS = [
    [ROOT_FOLDER_NAME, "YouTube", "Public"],
    [ROOT_FOLDER_NAME, "YouTube", "Private_Unlisted"],
    [ROOT_FOLDER_NAME, "GoogleDrive"],
    [ROOT_FOLDER_NAME, "DirectMP4"],
    [ROOT_FOLDER_NAME, "Vimeo"],
    [ROOT_FOLDER_NAME, LOGS_FOLDER_NAME],
]
PLATFORM_FOLDER_MAP: dict[str, list[str]] = {
    "YouTube_Public": [ROOT_FOLDER_NAME, "YouTube", "Public"],
    "YouTube_Private": [ROOT_FOLDER_NAME, "YouTube", "Private_Unlisted"],
    "Google_Drive": [ROOT_FOLDER_NAME, "GoogleDrive"],
    "Direct_MP4": [ROOT_FOLDER_NAME, "DirectMP4"],
    "Vimeo": [ROOT_FOLDER_NAME, "Vimeo"],
    "Unknown": [ROOT_FOLDER_NAME, LOGS_FOLDER_NAME, UNKNOWN_FOLDER_NAME],
}


def build_drive_service(credentials_json: str | Path) -> Any:
    """Create a reusable Google Drive service client from a service account."""
    credentials_path = Path(credentials_json)
    if not credentials_path.exists():
        raise FileNotFoundError(f"Service account credentials not found: {credentials_path}")

    credentials = Credentials.from_service_account_file(
        str(credentials_path), scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _escape_query_value(value: str) -> str:
    return value.replace("'", "\\'")


def find_folder(service: Any, folder_name: str, parent_id: str | None = None) -> str | None:
    """Return the folder id if a folder with the given name exists under the parent."""
    query = [
        "mimeType='application/vnd.google-apps.folder'",
        f"name='{_escape_query_value(folder_name)}'",
        "trashed=false",
    ]
    if parent_id:
        query.append(f"'{parent_id}' in parents")
    else:
        query.append("'root' in parents")

    response = service.files().list(
        q=" and ".join(query),
        fields="files(id, name)",
        spaces="drive",
        pageSize=10,
    ).execute()
    files = response.get("files", [])
    return files[0]["id"] if files else None


def create_folder(service: Any, folder_name: str, parent_id: str | None = None) -> str:
    """Create a Google Drive folder and return its file ID."""
    metadata: dict[str, Any] = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def get_or_create_folder(service: Any, folder_name: str, parent_id: str | None = None) -> str:
    """Return an existing folder ID or create a new folder if needed."""
    folder_id = find_folder(service, folder_name, parent_id=parent_id)
    if folder_id:
        return folder_id
    return create_folder(service, folder_name, parent_id=parent_id)


def get_or_create_folder_by_path(service: Any, folder_path: list[str]) -> str:
    """Create or resolve a folder path under Google Drive root."""
    parent_id = "root"
    for folder_name in folder_path:
        parent_id = get_or_create_folder(service, folder_name, parent_id=parent_id)
    return parent_id


def get_upload_folder_path(platform: str) -> list[str]:
    """Return the Drive folder path for a given platform."""
    return PLATFORM_FOLDER_MAP.get(platform, PLATFORM_FOLDER_MAP["Unknown"])


def build_drive_filename(platform: str, source_path: Path) -> str:
    """Rename the local file before upload using a stable short hash."""
    normalized = platform.split("_")[0].lower() if platform else "asset"
    short_hash = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:8]
    return f"{normalized}_{short_hash}.mp4"


def _extract_local_path(message: str) -> Path | None:
    if not message:
        return None

    candidate = message.strip()
    if "->" in candidate:
        candidate = candidate.split("->")[-1].strip()
    if candidate.startswith(('"', "'")) and candidate.endswith(('"', "'")):
        candidate = candidate[1:-1]

    local_path = Path(candidate)
    if local_path.is_absolute() and local_path.exists():
        return local_path

    relative_path = Path.cwd() / local_path
    if relative_path.exists():
        return relative_path

    return None


def upload_file(service: Any, local_path: Path, parent_folder_id: str, upload_name: str) -> dict[str, str]:
    """Upload a file to Drive using resumable upload and return file metadata."""
    media = MediaFileUpload(str(local_path), mimetype="application/octet-stream", resumable=True)
    metadata = {"name": upload_name, "parents": [parent_folder_id]}
    request = service.files().create(body=metadata, media_body=media, fields="id, webViewLink")
    file_info = request.execute()
    return {
        "file_id": file_info["id"],
        "drive_link": file_info.get("webViewLink", f"https://drive.google.com/file/d/{file_info['id']}/view"),
    }


def upload_log_file(service: Any, log_path: Path, root_folder_id: str) -> None:
    """Upload the download log file into Root/Logs/ if it exists."""
    if not log_path.exists():
        logger.warning("Log file not found, skipping upload: %s", log_path)
        return

    logs_folder_id = get_or_create_folder_by_path(service, [ROOT_FOLDER_NAME, LOGS_FOLDER_NAME])
    upload_file(service, log_path, logs_folder_id, log_path.name)
    logger.info("Uploaded execution log to Drive folder: %s", logs_folder_id)


def upload_records_to_drive(
    records: list[dict[str, Any]],
    credentials_json: str | Path,
    *,
    log_file_path: str | Path = Path("logs/download_log.jsonl"),
    root_folder_name: str = ROOT_FOLDER_NAME,
) -> list[dict[str, Any]]:
    """Upload successful records to Drive and update each record with Drive metadata."""
    service = build_drive_service(credentials_json)

    # Ensure the required folder hierarchy exists.
    for path in DRIVE_FOLDER_PATHS:
        get_or_create_folder_by_path(service, path)

    root_folder_id = get_or_create_folder(service, root_folder_name, parent_id="root")
    upload_log_file(service, Path(log_file_path), root_folder_id)

    updated_records: list[dict[str, Any]] = []
    for record in records:
        record.setdefault("drive_file_id", "")
        record.setdefault("drive_link", "")

        if record.get("status") != "success":
            updated_records.append(record)
            continue

        local_path = _extract_local_path(str(record.get("message", "")))
        if not local_path:
            record["status"] = "failure"
            record["message"] = "Upload failed: unable to resolve local file path from record message"
            updated_records.append(record)
            continue

        if not local_path.exists():
            record["status"] = "failure"
            record["message"] = f"Upload failed: local file not found: {local_path}"
            updated_records.append(record)
            continue

        folder_path = get_upload_folder_path(record.get("platform", "Unknown"))
        try:
            parent_folder_id = get_or_create_folder_by_path(service, folder_path)
            upload_name = build_drive_filename(record.get("platform", "Unknown"), local_path)
            metadata = upload_file(service, local_path, parent_folder_id, upload_name)
            record["drive_file_id"] = metadata["file_id"]
            record["drive_link"] = metadata["drive_link"]
            updated_records.append(record)
        except HttpError as exc:
            record["status"] = "failure"
            record["message"] = f"Upload failed: {exc._get_reason() if hasattr(exc, '_get_reason') else exc}"
            updated_records.append(record)
        except Exception as exc:
            record["status"] = "failure"
            record["message"] = f"Upload failed: {exc}"
            updated_records.append(record)

    return updated_records
