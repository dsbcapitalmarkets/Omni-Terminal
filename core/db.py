import io
import json
import logging
import os
from pathlib import Path
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from dotenv import load_dotenv
load_dotenv()

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
    """Return the Drive file ID for filename inside folder, or None."""

    escaped_name = filename.replace("\\", "\\\\").replace("'", "\\'")

    query = (
        f"name = '{escaped_name}' "
        f"and '{folder_id}' in parents "
        f"and trashed = false"
    )

    result = service.files().list(
        q=query,
        fields="files(id, name)",
        spaces="drive",
        pageSize=100,
    ).execute()

    files = result.get("files", [])
    return files[0]["id"] if files else None

def _find_subfolder(service, subfolder: str, parent_id: str):
    """Find an existing Google Drive subfolder without creating it."""

    query = (
        f"name = '{subfolder}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents "
        f"and trashed = false"
    )

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=1,
    ).execute()

    folders = results.get("files", [])

    return folders[0]["id"] if folders else None

def _find_or_create_subfolder(service, folder_name: str, parent_id: str) -> str:
    """Find a subfolder under parent_id or create it if it does not exist."""

    escaped_name = folder_name.replace("\\", "\\\\").replace("'", "\\'")

    query = (
        f"name = '{escaped_name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents "
        f"and trashed = false"
    )

    response = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=100,
    ).execute()

    folders = response.get("files", [])

    if folders:
        return folders[0]["id"]

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }

    folder = service.files().create(
        body=folder_metadata,
        fields="id",
    ).execute()

    logging.info("Created Google Drive folder: %s", folder_name)

    return folder["id"]

# =========================
# Public API
# =========================
def save(filename: str, payload, subfolder: str | None = None):
    """
    Save JSON data to Google Drive.

    If subfolder is provided, save inside that subfolder.
    Otherwise, save directly inside the configured root folder.
    """

    try:
        service = _get_drive_service()
        folder_id = _get_folder_id()

        # Resolve destination folder
        if subfolder:
            folder_id = _find_or_create_subfolder(
                service,
                subfolder,
                folder_id,
            )

        json_data = json.dumps(payload, indent=2, default=str)
        media = MediaIoBaseUpload(
            io.BytesIO(json_data.encode("utf-8")),
            mimetype="application/json",
            resumable=True,
        )

        file_id = _find_file_id(service, filename, folder_id)

        if file_id:
            # Update existing file
            service.files().update(
                fileId=file_id,
                media_body=media,
            ).execute()

            logging.info(
                "Updated Google Drive file: %s%s",
                f"{subfolder}/" if subfolder else "",
                filename,
            )

        else:
            # Create new file
            metadata = {
                "name": filename,
                "mimeType": "application/json",
                "parents": [folder_id],
            }

            service.files().create(
                body=metadata,
                media_body=media,
                fields="id",
            ).execute()

            logging.info(
                "Created Google Drive file: %s%s",
                f"{subfolder}/" if subfolder else "",
                filename,
            )

    except Exception:
        logging.exception("Failed to save %s to Google Drive", filename)

        # Preserve existing local fallback for normal saves.
        # For subfolder saves, fail explicitly rather than silently
        # writing the requested Drive files to the local data folder.
        if subfolder:
            raise

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        local_path = DATA_DIR / filename
        with open(local_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, default=str)

        logging.warning("Saved locally instead: %s", local_path)


def load(filename: str, default=None, subfolder: str | None = None):
    """
    Load JSON from Google Drive.

    If subfolder is provided, search inside that Drive subfolder.
    Falls back to the local data/ folder if Drive is unavailable
    or the requested file does not exist.
    """

    try:
        service = _get_drive_service()
        folder_id = _get_folder_id()

        if subfolder:
            folder_id = _find_subfolder(
                service,
                subfolder,
                folder_id,
            )

            if not folder_id:
                logger.warning(
                    "Drive subfolder '%s' not found.",
                    subfolder,
                )
                return default

        file_id = _find_file_id(service, filename, folder_id)

        if file_id:
            request = service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            buffer.seek(0)
            return json.load(buffer)

        logger.warning(
            "Drive: %s not found. Checking local fallback.",
            filename,
        )

    except Exception as e:
        logger.warning(
            "Drive load failed for %s, trying local fallback: %s",
            filename,
            e,
        )

    local_path = DATA_DIR / filename

    if local_path.exists():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)

        except (json.JSONDecodeError, OSError) as e:
            logger.error("Local load failed for %s: %s", filename, e)

    return default


def last_updated(
    filename: str,
    subfolder: str | None = None,
) -> str | None:
    """Return last modified time of a Drive file."""

    try:
        service = _get_drive_service()
        folder_id = _get_folder_id()

        if subfolder:
            folder_id = _find_or_create_subfolder(
                service,
                subfolder,
                folder_id,
            )

        file_id = _find_file_id(service, filename, folder_id)

        if not file_id:
            return None

        meta = service.files().get(
            fileId=file_id,
            fields="modifiedTime",
        ).execute()

        dt = datetime.fromisoformat(
            meta["modifiedTime"].replace("Z", "+00:00")
        )

        from core.utils import IST

        return dt.astimezone(IST).strftime(
            "%d %b %Y, %I:%M %p IST"
        )

    except Exception as e:
        logger.warning(
            "Drive last_updated failed for %s: %s",
            filename,
            e,
        )

    local_path = DATA_DIR / filename

    if local_path.exists():
        ts = os.path.getmtime(local_path)
        return datetime.fromtimestamp(ts).strftime(
            "%d %b %Y, %I:%M %p"
        )

    return None
