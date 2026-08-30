import io
import json
import logging
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_secret(key: str):
    """Read a secret from environment variables."""
    value = os.getenv(key)

    if value:
        return value

    raise RuntimeError(f"'{key}' environment variable not found.")


def _get_drive_service():
    """Create authenticated Google Drive client."""
    creds_raw = _get_secret("GOOGLE_DRIVE_CRED")

    creds_dict = (
        json.loads(creds_raw)
        if isinstance(creds_raw, str)
        else creds_raw
    )

    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=DRIVE_SCOPES,
    )

    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def _get_folder_id() -> str:
    """Get Google Drive folder ID."""
    return _get_secret("GOOGLE_DRIVE_FOLDER_ID")


def _find_file_id(
    service,
    filename: str,
    folder_id: str,
) -> str | None:
    """Find a file inside the configured Google Drive folder."""

    query = (
        f"name='{filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed=false"
    )

    result = service.files().list(
        q=query,
        fields="files(id,name)",
        spaces="drive",
    ).execute()

    files = result.get("files", [])

    if not files:
        return None

    return files[0]["id"]


def load_json(filename: str):
    """
    Load the latest JSON file from Google Drive.

    This function always reads the current file.
    Nothing is hard-coded or cached here.
    """

    service = _get_drive_service()
    folder_id = _get_folder_id()

    file_id = _find_file_id(
        service,
        filename,
        folder_id,
    )

    if not file_id:
        raise FileNotFoundError(
            f"'{filename}' was not found in Google Drive."
        )

    request = service.files().get_media(
        fileId=file_id
    )

    buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(
        buffer,
        request,
    )

    done = False

    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)

    return json.load(buffer)