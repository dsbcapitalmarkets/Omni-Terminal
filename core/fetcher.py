# core/fetcher.py

"""
Central data access layer.
All modules must fetch data through here — never call yfinance or NSE directly.
"""

import logging
import pandas as pd
import yfinance as yf
import time

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

    Returns a normalized OHLC dataframe.
    Raises on failure.
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

    if df.empty:
        raise ValueError(
            f"yfinance returned empty data for {ticker}"
        )

    return normalize_ohlc(df)



def fetch_ohlc(
    tickers: str | list[str],
    period: str = "6mo",
    interval: str = "1d",
    retries: int = 3,
    backoff: float = 15.0,
) -> pd.DataFrame:
    """
    Fetch OHLC data for one or multiple tickers.

    Single ticker:
        Returns a normal OHLC dataframe.
        Retains the existing retry behaviour.

    Multiple tickers:
        1. Attempt one bulk yfinance download.
        2. Validate each ticker independently.
        3. Skip individual fallback for failed .BO tickers.
        4. Attempt one individual download for other failed tickers.
        5. Combine all successfully recovered tickers.

    Multi-ticker requests return a grouped MultiIndex dataframe.

    Never raises — returns an empty DataFrame on total failure.
    """

    is_multi = isinstance(tickers, list)

    # ---------------------------------------------------------
    # SINGLE TICKER — EXISTING RETRY BEHAVIOUR
    # ---------------------------------------------------------

    if not is_multi:

        last_error = None

        for attempt in range(1, retries + 1):

            try:

                df = _download_single(
                    tickers,
                    period,
                    interval,
                )

                logger.info(
                    f"{tickers}: {len(df)} observations"
                )

                return df

            except Exception as e:

                last_error = e
                wait = backoff * attempt

                logger.warning(
                    f"fetch_ohlc attempt "
                    f"{attempt}/{retries} failed for {tickers}: "
                    f"{e}"
                )

                if attempt < retries:
                    time.sleep(wait)

        logger.error(
            f"fetch_ohlc failed for {tickers} "
            f"after {retries} attempts: {last_error}"
        )

        return pd.DataFrame()

    # ---------------------------------------------------------
    # MULTIPLE TICKERS
    # ---------------------------------------------------------

    if not tickers:
        return pd.DataFrame()

    tickers = list(dict.fromkeys(tickers))

    min_expected_rows = 10

    valid_data = {}
    failed_tickers = []
    last_error = None

    # ---------------------------------------------------------
    # STEP 1 — ONE BULK DOWNLOAD
    # ---------------------------------------------------------

    bulk_df = pd.DataFrame()

    try:

        logger.info(
            f"Bulk yfinance download: {len(tickers)} tickers"
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
                "yfinance returned an empty DataFrame"
            )

    except Exception as e:

        last_error = e

        logger.warning(
            f"Bulk yfinance download failed: {e}"
        )

    # ---------------------------------------------------------
    # STEP 2 — VALIDATE EACH TICKER
    # ---------------------------------------------------------

    for ticker in tickers:

        try:

            if bulk_df.empty:
                raise ValueError(
                    "No usable bulk response available"
                )

            if (
                isinstance(bulk_df.columns, pd.MultiIndex)
                and ticker in bulk_df.columns.get_level_values(0)
            ):

                ticker_df = bulk_df[ticker]

            elif ticker in bulk_df.columns:

                ticker_df = bulk_df[ticker]

            else:

                raise ValueError(
                    "Ticker missing from bulk response"
                )

            ticker_df = normalize_ohlc(ticker_df)

            ticker_df = ticker_df[
                ~ticker_df.index.duplicated(keep="last")
            ]

            ticker_df = ticker_df.dropna(
                subset=["Close"]
            )

            rows = len(ticker_df)

            logger.info(
                f"{ticker}: bulk download = {rows} observations"
            )

            if rows < min_expected_rows:

                raise ValueError(
                    f"Insufficient bulk history: {rows} rows"
                )

            valid_data[ticker] = ticker_df

        except Exception as e:

            logger.warning(
                f"{ticker}: bulk data unusable: {e}"
            )

            failed_tickers.append(ticker)

    # ---------------------------------------------------------
    # STEP 3 — INDIVIDUAL FALLBACK
    # Skip .BO tickers completely.
    # ---------------------------------------------------------

    bse_skipped = []

    for ticker in failed_tickers:

        if ticker.upper().endswith(".BO"):

            bse_skipped.append(ticker)

            logger.warning(
                f"{ticker}: individual fallback skipped "
                f"(BSE ticker)"
            )

            continue

        try:

            logger.info(
                f"Individual fallback for {ticker}"
            )

            ticker_df = _download_single(
                ticker,
                period,
                interval,
            )

            ticker_df = ticker_df[
                ~ticker_df.index.duplicated(keep="last")
            ]

            ticker_df = ticker_df.dropna(
                subset=["Close"]
            )

            rows = len(ticker_df)

            logger.info(
                f"{ticker}: individual download = {rows} observations"
            )

            if rows < min_expected_rows:

                raise ValueError(
                    f"Insufficient individual history: {rows} rows"
                )

            valid_data[ticker] = ticker_df

        except Exception as e:

            last_error = e

            logger.error(
                f"{ticker}: individual fallback failed: {e}"
            )

    if bse_skipped:

        logger.warning(
            f"BSE tickers skipped without individual fallback: "
            f"{len(bse_skipped)}"
        )

    # ---------------------------------------------------------
    # STEP 4 — BUILD MULTIINDEX DATAFRAME
    # ---------------------------------------------------------

    if not valid_data:

        logger.error(
            f"fetch_ohlc failed for all {len(tickers)} tickers. "
            f"Last error: {last_error}"
        )

        return pd.DataFrame()

    combined = pd.concat(
        valid_data,
        axis=1,
    )

    logger.info(
        f"Multi-ticker fetch complete: "
        f"{len(valid_data)}/{len(tickers)} tickers recovered"
    )

    missing = [
        ticker
        for ticker in tickers
        if ticker not in valid_data
    ]

    if missing:

        logger.warning(
            f"Tickers with no usable historical data: {missing}"
        )

    return combined



def fetch_nse(
    url: str
) -> dict | list:

    """
    Fetch from NSE API with session cookie,
    retry, and backoff.

    Raises RuntimeError after all retries exhausted.
    """

    return nse_get(
        url,
        retries=3,
        backoff=5.0,
    )
