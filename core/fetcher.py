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
    Fetch OHLC for one or multiple tickers.

    Single ticker:
        returns normal OHLC dataframe.

    Multiple tickers:
        returns grouped MultiIndex dataframe:

            ticker    ^NSEI                 ^CNXIT
                      Open High Low Close   Open High Low Close
            Date
            ...

    For multi-ticker requests:
        1. Try one bulk yfinance download.
        2. Validate each ticker.
        3. Individually re-fetch tickers with missing/insufficient data.
        4. Combine the recovered data.

    Never raises — returns empty DataFrame on total failure.
    """

    is_multi = isinstance(tickers, list)

    # ---------------------------------------------------------
    # Single ticker
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
                    f"{e} — retrying in {wait}s"
                )

                if attempt < retries:
                    time.sleep(wait)

        logger.error(
            f"fetch_ohlc failed for {tickers} "
            f"after {retries} attempts: {last_error}"
        )

        return pd.DataFrame()

    # ---------------------------------------------------------
    # Multiple tickers
    # ---------------------------------------------------------

    if not tickers:
        return pd.DataFrame()

    last_error = None

    # Minimum history required for a ticker to be considered
    # successfully downloaded.
    #
    # This is deliberately not hardcoded to 21 because the
    # fetcher is shared by other modules.
    min_expected_rows = 10

    # ---------------------------------------------------------
    # STEP 1 — bulk download
    # ---------------------------------------------------------

    bulk_df = pd.DataFrame()

    for attempt in range(1, retries + 1):

        try:

            logger.info(
                f"Bulk yfinance download: "
                f"{len(tickers)} tickers"
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
                    "yfinance returned empty DataFrame"
                )

            break

        except Exception as e:

            last_error = e

            wait = backoff * attempt

            logger.warning(
                f"Bulk fetch attempt "
                f"{attempt}/{retries} failed: {e} "
                f"— retrying in {wait}s"
            )

            if attempt < retries:
                time.sleep(wait)

    # ---------------------------------------------------------
    # STEP 2 — inspect each ticker
    # ---------------------------------------------------------

    valid_data = {}
    failed_tickers = []

    for ticker in tickers:

        try:

            # -------------------------------------------------
            # Extract ticker from MultiIndex
            # -------------------------------------------------

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

            # Remove duplicate dates
            ticker_df = ticker_df[
                ~ticker_df.index.duplicated(
                    keep="last"
                )
            ]

            # Remove rows where Close is unavailable
            ticker_df = ticker_df.dropna(
                subset=["Close"]
            )

            rows = len(ticker_df)

            logger.info(
                f"{ticker}: bulk download = "
                f"{rows} observations"
            )

            if rows < min_expected_rows:

                logger.warning(
                    f"{ticker}: only {rows} rows from "
                    f"bulk download — individual retry required"
                )

                failed_tickers.append(ticker)

            else:

                valid_data[ticker] = ticker_df

        except Exception as e:

            logger.warning(
                f"{ticker}: unable to use bulk data: {e}"
            )

            failed_tickers.append(ticker)

    # ---------------------------------------------------------
    # STEP 3 — individually recover failed tickers
    # ---------------------------------------------------------

    for ticker in failed_tickers:

        recovered = False

        for attempt in range(1, retries + 1):

            try:

                logger.info(
                    f"Individual recovery for {ticker} "
                    f"(attempt {attempt}/{retries})"
                )

                ticker_df = _download_single(
                    ticker,
                    period,
                    interval,
                )

                ticker_df = ticker_df[
                    ~ticker_df.index.duplicated(
                        keep="last"
                    )
                ]

                ticker_df = ticker_df.dropna(
                    subset=["Close"]
                )

                rows = len(ticker_df)

                logger.info(
                    f"{ticker}: individual download = "
                    f"{rows} observations"
                )

                if rows < min_expected_rows:

                    raise ValueError(
                        f"only {rows} observations"
                    )

                valid_data[ticker] = ticker_df

                recovered = True

                break

            except Exception as e:

                last_error = e

                wait = backoff * attempt

                logger.warning(
                    f"{ticker}: individual recovery "
                    f"attempt {attempt}/{retries} failed: "
                    f"{e}"
                )

                if attempt < retries:
                    time.sleep(wait)

        if not recovered:

            logger.error(
                f"{ticker}: failed to recover historical data"
            )

    # ---------------------------------------------------------
    # STEP 4 — construct MultiIndex dataframe
    # ---------------------------------------------------------

    if not valid_data:

        logger.error(
            f"fetch_ohlc failed for all tickers: "
            f"{last_error}"
        )

        return pd.DataFrame()

    combined = pd.concat(
        valid_data,
        axis=1,
    )

    # Ensure conventional ordering:
    #
    # ticker
    #   Open
    #   High
    #   Low
    #   Close
    #   Volume
    #
    # This keeps compatibility with:
    #
    # raw[symbol]
    #
    # in sector_rotation.py.

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
            f"Tickers with no usable historical data: "
            f"{missing}"
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