"""
Module Name: Stock Screener
Purpose: Filter and rank stocks from the NIFTY Total Market universe using
         technical trend, momentum, and volume criteria.
Inputs:  NIFTY Total Market universe via NSE API; OHLCV via yfinance
Outputs: Ranked list of qualifying stocks saved to screener.json
Dependencies: yfinance, pandas, ta, requests
"""

import logging
import pandas as pd
from datetime import datetime
from ta.momentum import RSIIndicator
from config import SCREENER
from core.db import save
from core.notifier import send_message
from core.utils import timestamp_str, safe_scalar, normalize_ohlc
from core.fetcher import fetch_ohlc, fetch_nse

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
MIN_ABS_VOLUME = 50_000   # minimum 20-day avg volume — filters illiquid microcaps


# ── Helpers ─────────────────────────────────────────────────────────────────

def _extract_symbol_df(data: pd.DataFrame, yahoo_symbol: str) -> pd.DataFrame:
    """
    Safely extract a single symbol's OHLCV DataFrame from a batch download result.

    yfinance.download() returns:
      - MultiIndex columns (ticker, field) when multiple tickers are requested
      - Flat columns (field) when only one ticker is requested or one survives

    This helper handles both cases so callers never need to check.

    Returns an empty DataFrame if the symbol is not present.
    """
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        # Standard multi-ticker case: columns = (field, ticker) or (ticker, field)
        # yfinance groups by ticker at level 0 when group_by="ticker"
        level0 = data.columns.get_level_values(0).unique().tolist()
        if yahoo_symbol in level0:
            df = data[yahoo_symbol].copy()
            return df.dropna(how="all")
        # Some yfinance versions use field at level 0, ticker at level 1
        level1 = data.columns.get_level_values(1).unique().tolist()
        if yahoo_symbol in level1:
            df = data.xs(yahoo_symbol, axis=1, level=1).copy()
            return df.dropna(how="all")
        return pd.DataFrame()

    else:
        # Flat columns — only happens when a single ticker survives the download.
        # In this case the entire df IS that ticker's data.
        expected_cols = {"Open", "High", "Low", "Close", "Volume"}
        if expected_cols.issubset(set(data.columns)):
            return data.dropna(how="all").copy()
        return pd.DataFrame()


# ── Step 1: Fetch Universe ───────────────────────────────────────────────────

def get_nifty_symbols() -> list[str]:
    """Fetch the full NIFTY Total Market symbol list from NSE."""
    url  = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"
    data = fetch_nse(url)
    symbols = [
        item["symbol"]
        for item in data["data"]
        if item.get("priority") != 1 and item.get("symbol")
    ]
    logger.info(f"Universe fetched: {len(symbols)} symbols")
    return symbols


# ── Step 2: Batch Download + Compute Indicators ──────────────────────────────

def compute_indicators(
    symbols: list[str],
    data: pd.DataFrame,
) -> dict[str, dict]:
    """
    Compute all technical indicators for every symbol in ONE pass.

    Returns a dict keyed by yahoo_symbol:
    {
        "close": float, "volume": float,
        "ema9": float, "sma12": float, "sma26": float,
        "sma50": float, "sma200": float,
        "avg_vol20": float, "ret_22d": float,
        "rsi": float,    # only if rsi factor enabled
        "passes": bool,  # True if hard filter conditions are met
    }

    Centralising indicator computation here eliminates the double-computation
    that previously existed between apply_filters_batch() and score_and_rank().
    """
    use_factors = SCREENER["score_factors"]
    indicators  = {}

    for sym in symbols:
        yahoo_symbol = f"{sym}.NS"
        try:
            df = _extract_symbol_df(data, yahoo_symbol)

            if df.empty or len(df) < 200:
                continue

            close  = df["Close"]
            volume = df["Volume"]

            ema9   = float(close.ewm(span=9,   adjust=False).mean().iloc[-1])
            sma12  = float(close.rolling(12).mean().iloc[-1])
            sma26  = float(close.rolling(26).mean().iloc[-1])
            sma50  = float(close.rolling(50).mean().iloc[-1])
            sma200 = float(close.rolling(200).mean().iloc[-1])

            avg_vol20    = float(volume.tail(20).mean())
            latest_close = float(close.iloc[-1])
            latest_vol   = float(volume.iloc[-1])

            # 22-day momentum return (used in scoring)
            ret_22d = (
                (latest_close / float(close.iloc[-22]) - 1) * 100
                if len(close) >= 23 else 0.0
            )

            # RSI (only computed if factor is enabled — avoids dead-code overhead)
            rsi = None
            if use_factors.get("rsi"):
                rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])

            # Hard filter pass/fail
            passes = (
                ema9 > sma12
                and ema9 > sma26
                and latest_close > sma50
                and latest_close > sma200
                and latest_vol > avg_vol20          # relative volume surge
                and avg_vol20 >= MIN_ABS_VOLUME     # minimum liquidity guard
            )

            indicators[yahoo_symbol] = {
                "sym":          sym,
                "close":        latest_close,
                "volume":       latest_vol,
                "ema9":         ema9,
                "sma12":        sma12,
                "sma26":        sma26,
                "sma50":        sma50,
                "sma200":       sma200,
                "avg_vol20":    avg_vol20,
                "ret_22d":      ret_22d,
                "rsi":          rsi,
                "passes":       passes,
            }

        except Exception as e:
            logger.warning(f"Indicator compute failed for {sym}: {e}")
            continue

    return indicators


# ── Step 3: Apply Filter ─────────────────────────────────────────────────────

def apply_filter(indicators: dict[str, dict]) -> list[str]:
    """
    Return the list of yahoo_symbols that passed the hard filter.
    Uses pre-computed indicators — no re-fetching or re-computation.
    """
    passed = [ysym for ysym, ind in indicators.items() if ind["passes"]]
    logger.info(f"Passed filter: {len(passed)}/{len(indicators)}")
    return passed


# ── Step 4: Score and Rank ───────────────────────────────────────────────────

def score_and_rank(
    passed_symbols: list[str],
    indicators: dict[str, dict],
    use_factors: dict | None = None,
    weights: dict | None = None,
) -> pd.DataFrame:
    """
    Score each passing symbol using pre-computed indicators.
    No re-fetching, no re-computation — pure math on the cached dict.

    Score factors (all configurable in config.py):
      momentum  — 22-day price return
      trend     — close/SMA50 + SMA50/SMA200 (trend health)
      rsi       — RSI zone bonus (50–70 = 1.0, >70 = 0.5, else 0)
      volume    — today's vol / 20-day avg vol
    """
    if use_factors is None:
        use_factors = SCREENER["score_factors"]
    if weights is None:
        weights = SCREENER["score_weights"]

    results = []
    for ysym in passed_symbols:
        ind = indicators.get(ysym)
        if not ind:
            continue
        try:
            scores: dict[str, float] = {}

            scores["momentum"] = ind["ret_22d"] if use_factors.get("momentum") else 0.0

            scores["trend"] = (
                (ind["close"] / ind["sma50"]) + (ind["sma50"] / ind["sma200"])
                if use_factors.get("trend") else 0.0
            )

            if use_factors.get("rsi") and ind["rsi"] is not None:
                rsi = ind["rsi"]
                scores["rsi"] = 1.0 if 50 <= rsi <= 70 else 0.5 if rsi > 70 else 0.0
            else:
                scores["rsi"] = 0.0

            scores["volume"] = (
                ind["volume"] / ind["avg_vol20"]
                if use_factors.get("volume") and ind["avg_vol20"] > 0 else 0.0
            )

            total = sum(scores[f] * weights.get(f, 0.0) for f in scores)

            results.append({
                "symbol": ind["sym"],
                "score":  round(float(total), 3),
            })

        except Exception as e:
            logger.warning(f"Score failed for {ysym}: {e}")

    return pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)


# ── Telegram message (HTML parse_mode) ──────────────────────────────────────

def format_message(ranked_df: pd.DataFrame, ts: str) -> str:
    """
    Format the Telegram alert using HTML parse_mode.
    Avoids Markdown link-breaking issues with dots and parentheses in URLs.
    """
    if ranked_df.empty:
        return f"📊 <b>Stock Screener</b> ({ts})\n\nNo signals today."

    msg = f"📊 <b>Stock Screener</b> ({ts})\n\n"
    for i, row in enumerate(ranked_df.head(20).itertuples(), 1):
        url  = f"https://www.screener.in/company/{row.symbol}/"
        msg += f"{i}. ✅ <a href='{url}'>{row.symbol}</a>\n"
        #msg += f"{i}. ✅ <a href='{url}'>{row.symbol}</a> — score: <code>{row.score}</code>\n"
    msg += "\n💡 EMA/SMA trend + volume filters."
    return msg


# ── run() — entry point for GitHub Actions ───────────────────────────────────

def run() -> dict:
    ts = timestamp_str()
    try:
        # 1. Fetch universe
        universe      = get_nifty_symbols()
        yahoo_symbols = [f"{sym}.NS" for sym in universe]

        # 2. Batch download — "1y" is the correct yfinance period string
        #    (previously "365d" which yfinance does not recognise)
        data = fetch_ohlc(yahoo_symbols, period="1y", interval="1d")

        if data.empty:
            raise RuntimeError("yfinance returned empty DataFrame for the universe.")

        # 3. Compute all indicators in one pass (eliminates double-computation)
        indicators = compute_indicators(universe, data)
        logger.info(f"Indicators computed for {len(indicators)} symbols")

        # 4. Apply hard filter (uses cached indicators — no recompute)
        passed = apply_filter(indicators)

        # 5. Score and rank (uses cached indicators — no recompute)
        ranked_df = score_and_rank(passed, indicators)

        stocks_list = ranked_df.to_dict(orient="records")

        result = {
            "timestamp":      ts,
            "status":         "ok",
            "total_universe": len(universe),
            "passed_count":   len(passed),
            "stocks":         stocks_list,
        }

        # 6. Save to Drive
        save("screener.json", result)

        # 7. Send Telegram alert (HTML parse_mode — fixes Markdown URL breakage)
        send_message(format_message(ranked_df, ts), parse_mode="HTML")

        logger.info(f"Screener done — {len(passed)}/{len(universe)} passed.")
        print(f"Screener done — {len(passed)} stocks passed.")
        return result

    except Exception as e:
        logger.error(f"Screener run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("screener.json", error_result)
        send_message(
            f"❌ <b>Stock Screener failed</b>\n<code>{e}</code>",
            parse_mode="HTML",
        )
        return error_result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()