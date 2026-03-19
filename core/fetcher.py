# core/fetcher.py

"""
Central data access layer.
All modules must fetch data through here — never call yfinance or NSE directly.
"""
import logging
import pandas as pd
import yfinance as yf
from core.utils import nse_get, normalize_ohlc

logger = logging.getLogger(__name__)

yf.set_tz_cache_location("/tmp/yfinance_cache")

def fetch_ohlc(
    tickers: str | list[str],
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLC for one or multiple tickers.
    Single ticker → pass a string.
    Multiple tickers → pass a list, returns grouped MultiIndex DataFrame.
    Never raises — returns empty DataFrame on failure.
    """
    try:
        is_multi = isinstance(tickers, list)
        df = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by="ticker" if is_multi else None,
            threads=True if is_multi else False,
            progress=False,
            auto_adjust=True,
        )
        return df if is_multi else normalize_ohlc(df)
    except Exception as e:
        logger.error(f"fetch_ohlc failed for {tickers}: {e}")
        return pd.DataFrame()

def fetch_nse(url: str) -> dict | list:
    """
    Fetch from NSE API with session cookie, retry, and backoff.
    Raises RuntimeError after all retries exhausted.
    """
    return nse_get(url, retries=3, backoff=5.0)