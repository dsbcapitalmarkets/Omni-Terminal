import json
import logging
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def get_gspread_client() -> gspread.Client:
    """Authenticate with Google Sheets using service account credentials."""
    creds_json = os.getenv("GOOGLE_DRIVE_CRED")
    if not creds_json:
        raise RuntimeError("Missing GOOGLE_DRIVE_CRED environment variable.")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(creds_json), SCOPE
    )
    return gspread.authorize(creds)


def get_worksheet(
    client: gspread.Client,
    spreadsheet_id: str,
    worksheet_name: str = "Sheet1",
) -> gspread.Worksheet:
    """Open a worksheet by spreadsheet ID."""
    return client.open_by_key(spreadsheet_id).worksheet(worksheet_name)