import io
import json
import logging
import os
from pathlib import Path
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

logger = logging.getLogger(__name__)

DATA_DIR     = Path(__file__).resolve().parent.parent / "data"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

def _get_secret(key: str) -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        secret = st.secrets[key]
        return secret if isinstance(secret, str) else dict(secret)
    except Exception:
        raise RuntimeError(f"'{key}' not found in environment or Streamlit secrets.")

# =========================
# Drive client
# =========================
def _get_drive_service():
    creds_raw = _get_secret("GOOGLE_DRIVE_CRED")
    creds_dict = json.loads(creds_raw) if isinstance(creds_raw, str) else creds_raw
    creds = Credentials.from_service_account_info(creds_dict, scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def _get_folder_id() -> str:
    return _get_secret("GOOGLE_DRIVE_FOLDER_ID")

def _find_file_id(service, filename: str, folder_id: str) -> str | None:
    """Return the Drive file ID for filename inside folder, or None if not found."""
    query = (
        f"name='{filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed=false"
    )
    result = service.files().list(
        q=query, fields="files(id, name)", spaces="drive"
    ).execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None

# =========================
# Public API
# =========================
def save(filename: str, payload: dict | list) -> None:
    """
    Update an existing JSON file in Google Drive.
    File MUST already exist in the Drive folder — create it manually first.
    Falls back to local data/ folder if Drive unavailable.
    """
    content = json.dumps(payload, indent=2, default=str).encode("utf-8")

    try:
        service   = _get_drive_service()
        folder_id = _get_folder_id()
        file_id   = _find_file_id(service, filename, folder_id)

        if not file_id:
            # File doesn't exist — can't create (service account has no quota)
            # Log clearly so user knows to manually create the file in Drive
            raise FileNotFoundError(
                f"'{filename}' not found in Drive folder. "
                f"Please create it manually in quant-dashboard-data/ "
                f"with content {{\"status\": \"pending\"}} then re-run."
            )

        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype="application/json",
            resumable=False,
        )
        service.files().update(
            fileId=file_id,
            media_body=media,
        ).execute()
        logger.info(f"Drive updated: {filename}")
        return

    except FileNotFoundError as e:
        # Re-raise with clear message — this needs user action
        logger.error(str(e))
        raise

    except Exception as e:
        logger.warning(
            f"Drive save failed for {filename}, falling back to local: {e}"
        )

    # Local fallback (used during local dev without Drive credentials)
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / filename, "w") as f:
        f.write(json.dumps(payload, indent=2, default=str))
    logger.info(f"Local save: {filename}")


def load(filename: str, default=None):
    """
    Read JSON from Google Drive. Falls back to local data/ folder.
    Use this in GitHub Actions modules — never cached.
    """
    try:
        service   = _get_drive_service()
        folder_id = _get_folder_id()
        file_id   = _find_file_id(service, filename, folder_id)

        if not file_id:
            logger.warning(f"Drive: {filename} not found.")
            return default

        request    = service.files().get_media(fileId=file_id)
        buffer     = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return json.load(buffer)

    except Exception as e:
        logger.warning(f"Drive load failed for {filename}, trying local: {e}")

    local_path = DATA_DIR / filename
    if local_path.exists():
        try:
            with open(local_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default

def last_updated(filename: str) -> str | None:
    """Return last modified time of the file from Drive."""
    try:
        service   = _get_drive_service()
        folder_id = _get_folder_id()
        file_id   = _find_file_id(service, filename, folder_id)

        if not file_id:
            return None

        meta = service.files().get(
            fileId=file_id, fields="modifiedTime"
        ).execute()
        dt = datetime.fromisoformat(
            meta["modifiedTime"].replace("Z", "+00:00")
        )
        from core.utils import IST
        return dt.astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")

    except Exception as e:
        logger.warning(f"Drive last_updated failed for {filename}: {e}")

    local_path = DATA_DIR / filename
    if local_path.exists():
        ts = os.path.getmtime(local_path)
        return datetime.fromtimestamp(ts).strftime("%d %b %Y, %I:%M %p")
    return None