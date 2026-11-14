
"""
DSB Capital - Bhavcopy-Based Universe Generator

Data sources:
    NSE: Daily CM UDiFF Bhavcopy
    BSE: Daily Equity UDiFF Bhavcopy

Generated files:
    data/nse_symbols.json
    data/bse_symbols.json
    data/bse_only_symbols.json
    data/nse_etf.json
    data/bse_etf.json
    data/nse_sme_symbols.json
    data/bse_sme_symbols.json
    data/nse_indices.json
    data/bse_indices.json

Notes:
    - Mainboard and SME securities are kept separate.
    - ETF classification is intentionally conservative.
    - BSE-only securities are identified using ISIN.
    - Index files are empty because STK Bhavcopy does not contain indices.
"""

import argparse
import json
import logging
import re
import time
import zipfile

from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from core.db import save

import os
import tempfile
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

# Use temporary runner storage in GitHub Actions.
# Preserve existing local folders when running on your machine.
if os.getenv("GITHUB_ACTIONS") == "true":
    DATA_DIR = Path(
        os.getenv("RUNNER_TEMP", tempfile.gettempdir())
    ) / "omni_terminal"

else:
    DATA_DIR = Path("data")

DOWNLOAD_DIR = DATA_DIR / "exchange_downloads"

# Ensure directories exist before downloading files.
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILES = {
    "nse": "nse_symbols.json",
    "bse": "bse_symbols.json",
    "bse_only": "bse_only_symbols.json",
    "nse_etf": "nse_etf.json",
    "bse_etf": "bse_etf.json",
    "nse_sme": "nse_sme_symbols.json",
    "bse_sme": "bse_sme_symbols.json",
}

NSE_MAINBOARD_SERIES = {"EQ", "BE", "BZ"}

BSE_MAINBOARD_SERIES = {
    "A", "B", "X", "XT", "T", "Z"
}

# SME series observed in the exchange Bhavcopy data.
NSE_SME_SERIES = {"SM", "ST", "SZ"}
BSE_SME_SERIES = {"M", "MT", "MS"}

# BSE E series contains exchange-traded fund instruments
# in the supplied diagnostic data.
BSE_ETF_SERIES = {"E"}

REQUEST_TIMEOUT = 30
MAX_LOOKBACK_DAYS = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# HTTP SESSION
# ============================================================

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def download_file(url: str) -> bytes:
    """Download a file and return its raw bytes."""

    response = SESSION.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    if not response.content:
        raise ValueError("Downloaded file is empty.")

    return response.content


# ============================================================
# NSE BHAVCOPY
# ============================================================

def download_nse_bhavcopy(trade_date: date) -> pd.DataFrame:
    """
    Download NSE CM UDiFF Bhavcopy.

    Example:
    BhavCopy_NSE_CM_0_0_0_20261112_F_0000.csv.zip
    """

    date_str = trade_date.strftime("%Y%m%d")

    filename = (
        f"BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
    )

    url = (
        "https://nsearchives.nseindia.com/content/cm/"
        f"{filename}"
    )

    logger.info("Downloading NSE Bhavcopy: %s", filename)

    content = download_file(url)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    archive_path = DOWNLOAD_DIR / filename
    archive_path.write_bytes(content)

    with zipfile.ZipFile(BytesIO(content)) as archive:
        csv_files = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            raise ValueError("No CSV found inside NSE ZIP.")

        with archive.open(csv_files[0]) as file:
            df = pd.read_csv(file, low_memory=False)

    logger.info("NSE Bhavcopy rows: %s", len(df))

    return df


# ============================================================
# BSE BHAVCOPY
# ============================================================

def download_bse_bhavcopy(trade_date: date) -> pd.DataFrame:
    """
    Download BSE Equity UDiFF Bhavcopy.

    Example:
    BhavCopy_BSE_CM_0_0_0_20261112_F_0000.CSV
    """

    date_str = trade_date.strftime("%Y%m%d")

    filename = (
        f"BhavCopy_BSE_CM_0_0_0_{date_str}_F_0000.CSV"
    )

    url = (
        "https://www.bseindia.com/download/BhavCopy/Equity/"
        f"{filename}"
    )

    logger.info("Downloading BSE Bhavcopy: %s", filename)

    content = download_file(url)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DOWNLOAD_DIR / filename
    output_path.write_bytes(content)

    df = pd.read_csv(
        BytesIO(content),
        low_memory=False,
    )

    logger.info("BSE Bhavcopy rows: %s", len(df))

    return df


# ============================================================
# FETCH LATEST AVAILABLE BHAVCOPY
# ============================================================

def fetch_exchange_data(
    requested_date: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, date]:
    """
    Fetch both exchange Bhavcopies.

    If no date is provided, try today and the preceding
    calendar days until both exchange files are available.

    If a date is explicitly supplied, only that date is tried.
    """

    if requested_date:
        dates_to_try = [requested_date]
    else:
        dates_to_try = [
            date.today() - timedelta(days=i)
            for i in range(MAX_LOOKBACK_DAYS + 1)
        ]

    last_error = None

    for trade_date in dates_to_try:

        logger.info(
            "Trying exchange data for %s",
            trade_date,
        )

        try:
            nse_df = download_nse_bhavcopy(trade_date)

            time.sleep(1)

            bse_df = download_bse_bhavcopy(trade_date)

            return nse_df, bse_df, trade_date

        except Exception as exc:
            last_error = exc

            logger.warning(
                "Bhavcopy unavailable for %s: %s",
                trade_date,
                exc,
            )

            if requested_date:
                break

    raise RuntimeError(
        "Unable to download both NSE and BSE Bhavcopies. "
        f"Last error: {last_error}"
    )


# ============================================================
# DATA NORMALIZATION
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and essential text fields."""

    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
    )

    required = {
        "FinInstrmId",
        "ISIN",
        "TckrSymb",
        "SctySrs",
        "FinInstrmTp",
        "FinInstrmNm",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required Bhavcopy columns: {sorted(missing)}"
        )

    text_columns = [
        "ISIN",
        "TckrSymb",
        "SctySrs",
        "FinInstrmTp",
        "FinInstrmNm",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    df["FinInstrmId"] = (
        df["FinInstrmId"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    return df


def valid_security_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep valid equity instruments with usable identifiers."""

    df = df.copy()

    df = df[
        (df["FinInstrmTp"] == "STK")
        & df["TckrSymb"].ne("")
        & df["ISIN"].ne("")
        & df["FinInstrmId"].ne("")
    ].copy()

    # Exclude exchange test symbols.
    df = df[
        ~df["TckrSymb"].str.endswith("NSETEST")
    ].copy()

    return df


# ============================================================
# ETF CLASSIFICATION
# ============================================================

def has_explicit_etf_marker(row: pd.Series) -> bool:
    """
    Conservative ETF classification.

    Requires an explicit ETF / Exchange Traded Fund / BEES
    marker in the instrument name or symbol.
    """

    symbol = str(row["TckrSymb"]).upper()
    name = str(row["FinInstrmNm"]).upper()

    text = f"{symbol} {name}"

    patterns = [
        r"\bETF\b",
        r"EXCHANGE[\s-]*TRADED[\s-]*FUND",
        r"\bBEES\b",
    ]

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def is_etf(row: pd.Series, exchange: str) -> bool:
    """
    Return True only for securities with an INF ISIN and
    a sufficiently strong ETF indicator.

    BSE E-series instruments are also accepted because
    the supplied exchange diagnostics showed this series
    contains gold/silver ETFs.
    """

    isin = str(row["ISIN"]).upper()

    if not isin.startswith("INF"):
        return False

    if has_explicit_etf_marker(row):
        return True

    if (
        exchange == "BSE"
        and row["SctySrs"] in BSE_ETF_SERIES
    ):
        return True

    return False


# ============================================================
# RECORD CONVERSION
# ============================================================

def get_trade_date(row: pd.Series) -> str | None:
    """Return the available Bhavcopy trade date."""

    for column in ("TradDt", "BizDt"):
        if column in row.index:
            value = row[column]

            if pd.notna(value):
                return str(value)

    return None


def convert_nse_record(row: pd.Series) -> dict:
    """Convert NSE Bhavcopy row into screener-compatible record."""

    symbol = row["TckrSymb"]
    isin = row["ISIN"]

    return {
        "symbol": symbol,
        "identifier": row["FinInstrmId"],
        "series": row["SctySrs"],
        "company": row["FinInstrmNm"],
        "isin": isin,
        "industry": None,
        "exchange": "NSE",
        "yahoo_symbol": f"{symbol}.NS",
        "is_fno": False,
        "is_etf": False,
        "is_suspended": False,
        "trade_date": get_trade_date(row),
    }


def convert_bse_record(row: pd.Series) -> dict:
    """Convert BSE Bhavcopy row into screener-compatible record."""

    symbol = row["TckrSymb"]
    isin = row["ISIN"]
    scrip_code = row["FinInstrmId"]

    return {
        "symbol": symbol,
        "scrip_code": scrip_code,
        "company": row["FinInstrmNm"],
        "industry": None,
        "trans_date": get_trade_date(row),
        "index_code": None,
        "series": row["SctySrs"],
        "isin": isin,
        "exchange": "BSE",
        "yahoo_symbol": f"{scrip_code}.BO",
        "is_fno": False,
        "is_etf": False,
        "is_suspended": False,
    }


def convert_etf_record(
    row: pd.Series,
    exchange: str,
) -> dict:
    """Convert ETF row into a common ETF record."""

    if exchange == "NSE":
        record = convert_nse_record(row)
    else:
        record = convert_bse_record(row)

    record["is_etf"] = True
    record["category"] = "ETF"

    return record


# ============================================================
# FILTERING AND DEDUPLICATION
# ============================================================

def deduplicate(
    df: pd.DataFrame,
    subset: list[str],
) -> pd.DataFrame:
    """Deduplicate records while retaining the first occurrence."""

    return (
        df.sort_values("TckrSymb")
        .drop_duplicates(subset=subset, keep="first")
        .reset_index(drop=True)
    )


def build_exchange_universes(
    df: pd.DataFrame,
    exchange: str,
) -> dict[str, list[dict]]:
    """Build mainboard, SME and ETF universes for one exchange."""

    df = normalize_columns(df)
    df = valid_security_rows(df)

    # ETF candidates must have an INF ISIN.
    inf_rows = df[
        df["ISIN"].str.startswith("INF")
    ].copy()

    etf_mask = inf_rows.apply(
        lambda row: is_etf(row, exchange),
        axis=1,
    )

    etf_df = inf_rows[etf_mask].copy()

    # INF instruments not positively classified as ETFs
    # remain excluded from ordinary equity universes.
    ambiguous_fund_count = len(inf_rows) - len(etf_df)

    logger.info(
        "%s: INF instruments=%d | ETFs classified=%d "
        "| ambiguous INF instruments excluded=%d",
        exchange,
        len(inf_rows),
        len(etf_df),
        ambiguous_fund_count,
    )

    # Ordinary equity universe excludes all INF instruments.
    equity_df = df[
        ~df["ISIN"].str.startswith("INF")
    ].copy()

    if exchange == "NSE":
        mainboard_series = NSE_MAINBOARD_SERIES
        sme_series = NSE_SME_SERIES
    else:
        mainboard_series = BSE_MAINBOARD_SERIES
        sme_series = BSE_SME_SERIES

    mainboard_df = equity_df[
        equity_df["SctySrs"].isin(mainboard_series)
    ].copy()

    sme_df = equity_df[
        equity_df["SctySrs"].isin(sme_series)
    ].copy()

    # Deduplicate by ISIN. A security should occur once
    # in each exchange universe.
    mainboard_df = deduplicate(
        mainboard_df,
        ["ISIN"],
    )

    sme_df = deduplicate(
        sme_df,
        ["ISIN"],
    )

    etf_df = deduplicate(
        etf_df,
        ["ISIN"],
    )

    if exchange == "NSE":
        mainboard_records = [
            convert_nse_record(row)
            for _, row in mainboard_df.iterrows()
        ]

        sme_records = [
            convert_nse_record(row)
            for _, row in sme_df.iterrows()
        ]

    else:
        mainboard_records = [
            convert_bse_record(row)
            for _, row in mainboard_df.iterrows()
        ]

        sme_records = [
            convert_bse_record(row)
            for _, row in sme_df.iterrows()
        ]

    etf_records = [
        convert_etf_record(row, exchange)
        for _, row in etf_df.iterrows()
    ]

    return {
        "mainboard": mainboard_records,
        "sme": sme_records,
        "etf": etf_records,
        "all_isins": set(df["ISIN"]),
    }


# ============================================================
# BSE-ONLY SECURITIES
# ============================================================

def build_bse_only_universe(
    bse_records: list[dict],
    nse_isins: set[str],
) -> list[dict]:
    """
    Identify BSE-only securities using ISIN.

    A BSE listing is considered BSE-only when its ISIN
    is absent from the NSE mainboard universe.
    """

    return [
        record
        for record in bse_records
        if record.get("isin")
        and record["isin"] not in nse_isins
    ]


# ============================================================
# JSON OUTPUT
# ============================================================

def save_json(data: list[dict], path: Path) -> None:
    """Save records to a formatted JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
            default=str,
        )

    logger.info(
        "Saved %s records -> %s",
        len(data),
        path,
    )


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_universes(
    requested_date: date | None = None,
) -> None:

    logger.info("=" * 65)
    logger.info("DSB CAPITAL - BHAVCOPY UNIVERSE GENERATOR")
    logger.info("=" * 65)

    # --------------------------------------------------------
    # 1. Download exchange data
    # --------------------------------------------------------

    nse_raw, bse_raw, trade_date = fetch_exchange_data(
        requested_date
    )

    logger.info("Using trade date: %s", trade_date)

    # --------------------------------------------------------
    # 2. Build exchange universes
    # --------------------------------------------------------

    nse = build_exchange_universes(
        nse_raw,
        "NSE",
    )

    bse = build_exchange_universes(
        bse_raw,
        "BSE",
    )

    nse_symbols = nse["mainboard"]
    bse_symbols = bse["mainboard"]

    nse_sme = nse["sme"]
    bse_sme = bse["sme"]

    nse_etf = nse["etf"]
    bse_etf = bse["etf"]

    # --------------------------------------------------------
    # 3. Identify BSE-only securities using ISIN
    # --------------------------------------------------------

    # Identify BSE-only securities using ISIN.
    # A BSE mainboard listing is considered BSE-only when its ISIN
    # is absent from all valid securities in the NSE Bhavcopy,
    # including mainboard, SME and ETF/fund segments.

    bse_only = build_bse_only_universe(
        bse_symbols,
        nse["all_isins"],
    )

    # --------------------------------------------------------
    # 4. Index files
    # --------------------------------------------------------
    # Equity STK Bhavcopy does not contain index instruments.
    # Keep these files available for existing application code.
    # Populate them later from a dedicated index master source.

    # nse_indices = []
    # bse_indices = []

    # --------------------------------------------------------
    # 5. Save all output files
    # --------------------------------------------------------
    save("nse_symbols.json", nse_symbols, subfolder="symbols")
    save("bse_symbols.json", bse_symbols, subfolder="symbols")
    save("bse_only_symbols.json", bse_only, subfolder="symbols")

    save("nse_etf.json", nse_etf, subfolder="symbols")
    save("bse_etf.json", bse_etf, subfolder="symbols")

    save("nse_sme_symbols.json", nse_sme, subfolder="symbols")
    save("bse_sme_symbols.json", bse_sme, subfolder="symbols")



    # --------------------------------------------------------
    # 6. Summary
    # --------------------------------------------------------

    logger.info("")
    logger.info("=" * 65)
    logger.info("UNIVERSE GENERATION SUMMARY")
    logger.info("=" * 65)

    logger.info("Trade date       : %s", trade_date)

    logger.info("NSE mainboard    : %d", len(nse_symbols))
    logger.info("BSE mainboard    : %d", len(bse_symbols))

    logger.info("BSE-only         : %d", len(bse_only))

    logger.info("NSE ETFs         : %d", len(nse_etf))
    logger.info("BSE ETFs         : %d", len(bse_etf))

    logger.info("NSE SME          : %d", len(nse_sme))
    logger.info("BSE SME          : %d", len(bse_sme))

    # logger.info("NSE indices      : %d", len(nse_indices))
    # logger.info("BSE indices      : %d", len(bse_indices))

    logger.info("=" * 65)

    logger.info("Universe generation completed successfully.")


# ============================================================
# COMMAND LINE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Generate NSE/BSE universes from daily Bhavcopy."
    )

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Trade date in YYYY-MM-DD format. Defaults to latest available.",
    )

    args = parser.parse_args()

    requested_date = None

    if args.date:
        requested_date = datetime.strptime(
            args.date,
            "%Y-%m-%d",
        ).date()

    generate_universes(requested_date)


if __name__ == "__main__":
    main()
