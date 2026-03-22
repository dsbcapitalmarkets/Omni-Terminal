import math
import time
import logging
import pandas as pd
import requests
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

def now_ist() -> datetime:
    return datetime.now(IST)

def today_str() -> str:
    return now_ist().strftime("%d %b %Y")

def timestamp_str() -> str:
    return now_ist().strftime("%d %b %Y, %I:%M %p IST")

def safe_scalar(x) -> float:
    """Extract plain Python float from pandas Series, DataFrame, or numpy scalar."""
    try:
        if isinstance(x, (pd.Series, pd.DataFrame)):
            arr = x.to_numpy().ravel()
            return float(arr[-1])
        return float(x)
    except Exception:
        return float("nan")

def fmt_pct(x, plus: bool = False) -> str:
    """Format float as percentage string. Returns 'N/A' for nan/None."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/A"
    return f"{x:+.2f}%" if plus else f"{x:.2f}%"

def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance MultiIndex columns if present."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def nse_get(url: str, retries: int = 3, backoff: float = 5.0) -> dict:
    """
    Hardened NSE API fetch with session cookie + retry/backoff.
    Used by: stock_screener, market_breadth, earnings_tracker, universe_updater.

    Raises RuntimeError after all retries exhausted.
    """
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.nseindia.com/",
        "Connection":      "keep-alive",
    }

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            session = requests.Session()
            # NSE requires homepage cookie before API calls
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(1)
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e
            wait = backoff * attempt
            logger.warning(
                f"NSE request failed (attempt {attempt}/{retries}): {e} "
                f"— retrying in {wait}s"
            )
            if attempt < retries:
                time.sleep(wait)

    raise RuntimeError(
        f"NSE API unreachable after {retries} attempts: {last_error}"
    )


def bse_get(url: str, retries: int = 3, backoff: float = 5.0) -> dict:
    """
    Hardened BSE API fetch with session cookie + retry/backoff.
    Mirrors nse_get() exactly — same Chrome/JSON headers, same session
    cookie pattern, same retry logic.
    Used by: universe_updater.

    Raises RuntimeError after all retries exhausted.
    """
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.bseindia.com/",
        "Connection":      "keep-alive",
    }

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            session = requests.Session()
            # BSE requires homepage cookie before API calls — same as NSE
            session.get("https://www.bseindices.com", headers=headers, timeout=10)
            time.sleep(1)
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e
            wait = backoff * attempt
            logger.warning(
                f"BSE request failed (attempt {attempt}/{retries}): {e} "
                f"— retrying in {wait}s"
            )
            if attempt < retries:
                time.sleep(wait)

    raise RuntimeError(
        f"BSE API unreachable after {retries} attempts: {last_error}"
    )