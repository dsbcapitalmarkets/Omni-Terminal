# core/fetcher.py

"""
Central data access layer.
All modules must fetch data through here — never call yfinance or NSE directly.
"""
import logging
import pandas as pd
import yfinance as yf
from core.utils import nse_get, normalize_ohlc
import time

logger = logging.getLogger(__name__)

yf.set_tz_cache_location("/tmp/yfinance_cache")

def fetch_ohlc(
    tickers: str | list[str],
    period: str = "6mo",
    interval: str = "1d",
    retries: int = 3,
    backoff: float = 15.0,
) -> pd.DataFrame:
    """
    Fetch OHLC for one or multiple tickers.
    Single ticker → pass a string.
    Multiple tickers → pass a list, returns grouped MultiIndex DataFrame.
    Retries on failure (e.g. yfinance rate limits) with exponential backoff.
    Never raises — returns empty DataFrame on failure.
    """
    is_multi = isinstance(tickers, list)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                tickers=tickers,
                period=period,
                interval=interval,
                group_by="ticker" if is_multi else None,
                threads=True if is_multi else False,
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                raise ValueError("yfinance returned empty DataFrame")
            return df if is_multi else normalize_ohlc(df)
        except Exception as e:
            last_error = e
            wait = backoff * attempt
            logger.warning(
                f"fetch_ohlc attempt {attempt}/{retries} failed for {tickers}: {e} "
                f"— retrying in {wait}s"
            )
            if attempt < retries:
                time.sleep(wait)
    logger.error(f"fetch_ohlc failed for {tickers} after {retries} attempts: {last_error}")
    return pd.DataFrame()

def fetch_nse(url: str) -> dict | list:
    """
    Fetch from NSE API with session cookie, retry, and backoff.
    Raises RuntimeError after all retries exhausted.
    """
    return nse_get(url, retries=3, backoff=5.0)
