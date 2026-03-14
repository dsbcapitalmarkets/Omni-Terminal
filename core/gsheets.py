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
    """
    Authenticate with Google Sheets using service account credentials
    stored in GOOGLE_SHEETS_CRED environment variable.
    Shared by all modules that need Sheets access.
    """
    creds_json = os.getenv("GOOGLE_SHEETS_CRED")
    if not creds_json:
        raise RuntimeError("Missing GOOGLE_SHEETS_CRED GitHub Secret.")
    creds_dict = json.loads(creds_json)
    creds      = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client     = gspread.authorize(creds)
    logger.info("Google Sheets client initialised.")
    return client

def open_or_create_sheet(
    client: gspread.Client,
    sheet_name: str,
    worksheet_name: str = "Sheet1",
    headers: list[str] | None = None,
) -> gspread.Worksheet:
    """
    Open an existing sheet or create it with optional headers.
    Shared utility so each module doesn't reimplement this logic.
    """
    try:
        worksheet = client.open(sheet_name).worksheet(worksheet_name)
        logger.info(f"Opened existing sheet: {sheet_name}")
        return worksheet
    except gspread.SpreadsheetNotFound:
        logger.info(f"Sheet not found, creating: {sheet_name}")
        worksheet = client.create(sheet_name).get_worksheet(0)
        worksheet.update_title(worksheet_name)
        if headers:
            worksheet.append_row(headers)
        return worksheet