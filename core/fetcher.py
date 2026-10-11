"""
Central data access layer.
All modules must fetch data through here — never call yfinance or NSE directly.
"""

import logging
import time

import pandas as pd
import yfinance as yf

from core.utils import nse_get, normalize_ohlc

logger = logging.getLogger(__name__)

yf.set_tz_cache_location("/tmp/yfinance_cache")


def _download_single(
    ticker: str,
    period: str,
    interval: str,
) -> pd.DataFrame:
    """
    Download one ticker independently.
    Return normalized OHLC data.
    """

    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        group_by="column",
        threads=False,
        progress=False,
        auto_adjust=True,
    )

    
    # Diagnostic logs: inspect raw Yahoo Finance response
    logger.info(
        "RAW DOWNLOAD %s: shape=%s, columns=%s",
        ticker,
        df.shape,
        df.columns.tolist(),
    )

    logger.info(
        "RAW DOWNLOAD %s: date range=%s to %s",
        ticker,
        df.index.min() if not df.empty else None,
        df.index.max() if not df.empty else None,
    )

    logger.info(
        "RAW DOWNLOAD %s: last 5 rows:\n%s",
        ticker,
        df.tail(5).to_string(),
    )

    if df.empty:
        raise ValueError(
            f"yfinance returned empty data for {ticker}"
        )

    df = normalize_ohlc(df, ticker=ticker)

    if "Close" not in df.columns:
        raise ValueError(
            f"Close column missing for {ticker}"
        )

    df = df.dropna(subset=["Close"])
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()

    if df.empty:
        raise ValueError(
            f"No valid closing prices for {ticker}"
        )

    return df


def fetch_ohlc(
    tickers: str | list[str],
    period: str = "6mo",
    interval: str = "1d",
    retries: int = 3,
    backoff: float = 15.0,
) -> pd.DataFrame:
    """
    Fetch OHLC for one or multiple tickers.

    Single ticker:
        Returns a normal OHLC DataFrame.

    Multiple tickers:
        Returns a ticker-first MultiIndex DataFrame compatible
        with raw[ticker] access.

    Tickers with insufficient bulk history are retried individually.
    """

    is_multi = isinstance(tickers, list)

    # ---------------------------------------------------------
    # SINGLE TICKER
    # ---------------------------------------------------------
    if not is_multi:

        for attempt in range(1, retries + 1):
            try:
                df = _download_single(
                    tickers,
                    period,
                    interval,
                )

                logger.info(
                    "%s: %s historical observations",
                    tickers,
                    len(df),
                )

                return df

            except Exception as exc:

                logger.warning(
                    "Download attempt %s/%s failed for %s: %s",
                    attempt,
                    retries,
                    tickers,
                    exc,
                )

                if attempt < retries:
                    time.sleep(backoff * attempt)

        logger.error(
            "Unable to download historical data for %s",
            tickers,
        )

        return pd.DataFrame()

    # ---------------------------------------------------------
    # MULTIPLE TICKERS
    # ---------------------------------------------------------
    if not tickers:
        return pd.DataFrame()

    # Bulk download first.
    bulk_df = pd.DataFrame()

    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "Downloading %s tickers in bulk",
                len(tickers),
            )

            bulk_df = yf.download(
                tickers=tickers,
                period=period,
                interval=interval,
                group_by="ticker",
                threads=True,
                progress=False,
                auto_adjust=True,
            )

            if bulk_df.empty:
                raise ValueError(
                    "Bulk download returned no data"
                )

            break

        except Exception as exc:

            logger.warning(
                "Bulk download attempt %s/%s failed: %s",
                attempt,
                retries,
                exc,
            )

            if attempt < retries:
                time.sleep(backoff * attempt)

    # Ten rows is a basic recovery threshold, not a guarantee
    # that the history is sufficient for every downstream calculation.
    min_expected_rows = 10

    valid_data = {}
    failed_tickers = []

    # ---------------------------------------------------------
    # EXTRACT AND VALIDATE EACH TICKER
    # ---------------------------------------------------------
    for ticker in tickers:
        try:

            if isinstance(bulk_df.columns, pd.MultiIndex):

                ticker_level = next(
                    (
                        level
                        for level in range(bulk_df.columns.nlevels)
                        if ticker in bulk_df.columns.get_level_values(level)
                    ),
                    None,
                )

                if ticker_level is None:
                    raise ValueError(
                        "Ticker missing from bulk response"
                    )

                ticker_df = bulk_df.xs(
                    ticker,
                    axis=1,
                    level=ticker_level,
                    drop_level=True,
                )

            else:
                # A single ticker may produce flat columns.
                if len(tickers) != 1:
                    raise ValueError(
                        "Expected MultiIndex columns for multiple tickers"
                    )

                ticker_df = bulk_df.copy()

            ticker_df = normalize_ohlc(ticker_df)
            ticker_df = ticker_df[
                ~ticker_df.index.duplicated(keep="last")
            ]

            if "Close" not in ticker_df.columns:
                raise ValueError(
                    "Close column missing from bulk response"
                )

            ticker_df = ticker_df.dropna(subset=["Close"])

            logger.info(
                "%s: bulk download returned %s observations",
                ticker,
                len(ticker_df),
            )

            if len(ticker_df) < min_expected_rows:
                failed_tickers.append(ticker)
            else:
                valid_data[ticker] = ticker_df

        except Exception as exc:

            logger.warning(
                "%s: bulk extraction failed: %s",
                ticker,
                exc,
            )

            failed_tickers.append(ticker)

    
    # ---------------------------------------------------------
    # INDIVIDUAL RECOVERY — ONE ATTEMPT PER FAILED TICKER
    # ---------------------------------------------------------
    for ticker in failed_tickers:
        try:
            logger.info(
                "Attempting individual recovery for %s (1 attempt only)",
                ticker,
            )

            ticker_df = _download_single(
                ticker,
                period,
                interval,
            )

            logger.info(
                "%s: individual download returned %s observations",
                ticker,
                len(ticker_df),
            )

            if len(ticker_df) < min_expected_rows:
                raise ValueError(
                    f"Only {len(ticker_df)} observations returned"
                )

            valid_data[ticker] = ticker_df

        except Exception as exc:
            logger.warning(
                "%s: individual recovery failed (no further retries): %s",
                ticker,
                exc,
            )

            logger.error(
                "%s: historical data recovery failed",
                ticker,
            )

    # ---------------------------------------------------------
    # COMBINE RESULTS
    # ---------------------------------------------------------
    if not valid_data:
        logger.error(
            "No tickers returned usable historical data"
        )
        return pd.DataFrame()

    combined = pd.concat(
        valid_data,
        axis=1,
    )

    logger.info(
        "Historical data fetch completed: %s/%s tickers usable",
        len(valid_data),
        len(tickers),
    )

    missing = [
        ticker
        for ticker in tickers
        if ticker not in valid_data
    ]

    if missing:
        logger.warning(
            "Tickers without usable history: %s",
            missing,
        )

    return combined


def fetch_nse(url: str) -> dict | list:
    """
    Fetch from NSE API with session cookie, retry, and backoff.
    Raises RuntimeError after all retries exhausted.
    """

    return nse_get(
        url,
        retries=3,
        backoff=5.0,
    )