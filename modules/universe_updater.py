"""
Module Name: Universe Updater
Purpose: Fetch the full NSE (NIFTY Total Market) and BSE AllCap symbol lists
         from their respective APIs and persist them to Google Drive as JSON.
         Runs weekly on Saturday via GitHub Actions.
Inputs:  NSE NIFTY Total Market API, BSE AllCap API
Outputs: nse_symbols.json, bse_symbols.json updated on Google Drive

Secrets required (already present in repo — shared with all modules):
    GOOGLE_DRIVE_CRED      — service account JSON (handles auth)
    GOOGLE_DRIVE_FOLDER_ID — Drive folder ID (tells save() where to write)
"""

import logging
import time
from core.db import save
from core.utils import timestamp_str, nse_get, bse_get

logger = logging.getLogger(__name__)

# ── API Endpoints ─────────────────────────────────────────────────────────────

NSE_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"

# Replace with your actual BSE AllCap API endpoint
BSE_URL = "https://www.bseindices.com/AsiaIndexAPI/api/Codewise_Indices/w?code=87"


# ── NSE ───────────────────────────────────────────────────────────────────────

def fetch_nse_symbols() -> tuple[list[dict], dict]:
    """
    Fetch NIFTY Total Market constituents from NSE API.

    Uses core/utils.nse_get() which handles:
        - Correct NSE request headers
        - Homepage cookie fetch before API call
        - Retry + backoff (3 attempts, 5s backoff)

    Filters out priority=1 (the index entry itself — not a stock).

    Each saved entry contains:
        symbol       : NSE ticker e.g. "HDFCBANK"
        identifier   : e.g. "HDFCBANKEQN"
        series       : e.g. "EQ"
        company      : from meta.companyName
        industry     : from meta.industry
        isin         : from meta.isin
        listing_date : from meta.listingDate
        is_fno       : from meta.isFNOSec
        is_etf       : from meta.isETFSec
        is_suspended : from meta.isSuspended

    Returns:
        symbols  : list of stock dicts
        metadata : index-level advance/decline summary
    """
    response = nse_get(NSE_URL)

    metadata = {
        "index_name": response.get("name", "NIFTY TOTAL MARKET"),
        "timestamp":  response.get("timestamp", ""),
        "advances":   response.get("advance", {}).get("advances", 0),
        "declines":   response.get("advance", {}).get("declines", 0),
        "unchanged":  response.get("advance", {}).get("unchanged", 0),
    }

    symbols = []
    for item in response.get("data", []):
        # priority=1 is the index row itself — skip it
        if item.get("priority", 0) == 1:
            continue

        meta = item.get("meta", {})
        symbols.append({
            "symbol":       item.get("symbol",     ""),
            "identifier":   item.get("identifier", ""),
            "series":       item.get("series",     "EQ"),
            "company":      meta.get("companyName", ""),
            "industry":     meta.get("industry",    ""),
            "isin":         meta.get("isin",        ""),
            "listing_date": meta.get("listingDate", ""),
            "is_fno":       meta.get("isFNOSec",    False),
            "is_etf":       meta.get("isETFSec",    False),
            "is_suspended": meta.get("isSuspended", False),
        })

    logger.info(f"NSE: {len(symbols)} stocks fetched (priority=1 index entry excluded)")
    return symbols, metadata


# ── BSE ───────────────────────────────────────────────────────────────────────

def fetch_bse_symbols() -> list[dict]:
    """
    Fetch BSE AllCap constituents from BSE API.

    Uses core/utils.bse_get() which handles:
        - Correct BSE request headers
        - Homepage cookie fetch before API call
        - Retry + backoff (3 attempts, 5s backoff)

    Each saved entry contains:
        scrip_code  : BSE numeric scrip code e.g. "542772"
        company     : company name e.g. "360 ONE WAM LIMITED"
        industry    : sector e.g. "Financial Services"
        trans_date  : constituent snapshot date e.g. "2026-02-27T00:00:00"
        index_code  : BSE index code (17 = BSE 500, 87 = AllCap)

    Note: BSE API does not return ISIN in this endpoint.
    """
    data = bse_get(BSE_URL)

    rows = data.get("Table", [])
    if not rows:
        raise ValueError(
            f"BSE API returned empty Table. "
            f"Response keys: {list(data.keys())}"
        )

    symbols = []
    for item in rows:
        scrip_code = str(item.get("SCRIP_CODE",    "")).strip()
        company    = str(item.get("SCRIPNAME",     "")).strip()
        industry   = str(item.get("Industry_name", "")).strip()
        trans_date = str(item.get("TransDate",     "")).strip()
        index_code = item.get("index_Code", "")

        if not scrip_code:
            continue

        symbols.append({
            "scrip_code": scrip_code,
            "company":    company,
            "industry":   industry,
            "trans_date": trans_date,
            "index_code": index_code,
        })

    logger.info(f"BSE: {len(symbols)} stocks fetched")
    return symbols


# ── run() ─────────────────────────────────────────────────────────────────────

def run() -> dict:
    """
    Fetch NSE + BSE symbol lists and save to Google Drive.

    Drive auth is handled entirely by core/db.save() using:
        GOOGLE_DRIVE_CRED      — service account credentials (env/secret)
        GOOGLE_DRIVE_FOLDER_ID — target Drive folder (env/secret)
    """
    ts     = timestamp_str()
    errors = []

    # ── NSE ──────────────────────────────────────────────────────────────────
    nse_count = 0
    try:
        nse_symbols, nse_meta = fetch_nse_symbols()
        nse_count = len(nse_symbols)

        save("nse_symbols.json", {
            "status":     "ok",
            "timestamp":  ts,
            "source":     NSE_URL,
            "count":      nse_count,
            "index_name": nse_meta["index_name"],
            "as_of":      nse_meta["timestamp"],
            "advances":   nse_meta["advances"],
            "declines":   nse_meta["declines"],
            "unchanged":  nse_meta["unchanged"],
            "symbols":    nse_symbols,
        })
        logger.info(f"nse_symbols.json saved to Drive — {nse_count} symbols")

    except Exception as e:
        logger.error(f"NSE fetch/save failed: {e}")
        errors.append(f"NSE: {e}")
        save("nse_symbols.json", {
            "status":    "error",
            "timestamp": ts,
            "error":     str(e),
            "count":     0,
            "symbols":   [],
        })

    # Pause between NSE and BSE calls
    time.sleep(3)

    # ── BSE ──────────────────────────────────────────────────────────────────
    bse_count = 0
    try:
        bse_symbols = fetch_bse_symbols()
        bse_count   = len(bse_symbols)

        save("bse_symbols.json", {
            "status":    "ok",
            "timestamp": ts,
            "source":    BSE_URL,
            "count":     bse_count,
            "symbols":   bse_symbols,
        })
        logger.info(f"bse_symbols.json saved to Drive — {bse_count} symbols")

    except Exception as e:
        logger.error(f"BSE fetch/save failed: {e}")
        errors.append(f"BSE: {e}")
        save("bse_symbols.json", {
            "status":    "error",
            "timestamp": ts,
            "error":     str(e),
            "count":     0,
            "symbols":   [],
        })

    # ── Summary ───────────────────────────────────────────────────────────────
    result = {
        "timestamp":  ts,
        "nse_count":  nse_count,
        "bse_count":  bse_count,
        "nse_status": "ok"  if not any("NSE" in e for e in errors) else "error",
        "bse_status": "ok"  if not any("BSE" in e for e in errors) else "error",
        "errors":     errors,
    }

    if errors:
        logger.error(f"Universe updater completed with errors: {errors}")
    else:
        logger.info(f"Universe updater done — NSE: {nse_count}, BSE: {bse_count}")

    print(
        f"Universe updater done — "
        f"NSE: {nse_count} symbols, BSE: {bse_count} symbols, "
        f"errors: {len(errors)}"
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()