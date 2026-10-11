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

def normalize_ohlc(
    df: pd.DataFrame,
    ticker: str | None = None,
) -> pd.DataFrame:
    """
    Normalize yfinance OHLC data.

    Supports:
    - Flat OHLC columns.
    - MultiIndex columns in either Price/Ticker or Ticker/Price order.
    - Optional ticker selection.
    - Missing OHLC fields without unnecessarily dropping valid Close data.

    Returns a DataFrame with conventional OHLCV column names.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):

        price_fields = {
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
            "Volume",
        }

        selected_level = None

        # Find the column level containing OHLC field names.
        for level in range(df.columns.nlevels):

            values = set(df.columns.get_level_values(level))

            if values.intersection(price_fields):
                selected_level = level
                break

        if selected_level is None:
            raise ValueError(
                "Unable to identify OHLC columns in MultiIndex response: "
                f"{df.columns.tolist()}"
            )

        # If a ticker is specified, select its columns first.
        if ticker is not None:

            ticker_levels = [
                level
                for level in range(df.columns.nlevels)
                if ticker in df.columns.get_level_values(level)
            ]

            if ticker_levels:

                ticker_level = ticker_levels[0]

                df = df.xs(
                    ticker,
                    axis=1,
                    level=ticker_level,
                    drop_level=True,
                )

                if isinstance(df.columns, pd.MultiIndex):

                    remaining_level = next(
                        (
                            level
                            for level in range(df.columns.nlevels)
                            if set(
                                df.columns.get_level_values(level)
                            ).intersection(price_fields)
                        ),
                        None,
                    )

                    if remaining_level is None:
                        raise ValueError(
                            f"OHLC columns missing for ticker {ticker}"
                        )

                    df.columns = df.columns.get_level_values(
                        remaining_level
                    )

                else:
                    df.columns = df.columns.astype(str)

            else:
                raise ValueError(
                    f"Ticker {ticker} not found in columns"
                )

        else:

            df.columns = df.columns.get_level_values(
                selected_level
            )

    df.columns = df.columns.astype(str)

    # Keep the conventional OHLCV fields that are actually available.
    expected_fields = [
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
    ]

    available_fields = [
        field for field in expected_fields
        if field in df.columns
    ]

    df = df.loc[:, available_fields]

    if df.columns.duplicated().any():
        raise ValueError(
            "Duplicate OHLC column names after normalization: "
            f"{df.columns.tolist()}"
        )

    # A valid Close is the essential requirement for price analysis.
    if "Close" in df.columns:
        df = df.dropna(subset=["Close"])

    return df.sort_index()

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
        "Referer":         "https://www.bseindices.com/",
        "Connection":      "keep-alive",
    }

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            session = requests.Session()
            # BSE requires homepage cookie before API calls — same as NSE
            session.get("https://www.bseindices.com", headers=headers, timeout=10)
            time.sleep(2)
            response = session.get(url, headers=headers, timeout=30)
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