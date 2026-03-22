"""
Module Name: Stock Screener
Purpose: Filter and rank stocks from the full NSE + BSE universe
         using technical trend, momentum, and volume criteria.
Inputs:  nse_symbols.json + bse_symbols.json from Google Drive
         (updated weekly by universe_updater.py)
Outputs: Ranked list of qualifying stocks saved to screener.json
Dependencies: yfinance, pandas, ta
"""

import logging
import time
import pandas as pd
from ta.momentum import RSIIndicator
from config import SCREENER
from core.db import save, load
from core.notifier import send_message
from core.utils import timestamp_str
from core.fetcher import fetch_ohlc, fetch_nse

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
MIN_ABS_VOLUME = 50_000
BATCH_SIZE     = 500   # safe yfinance batch size — avoids rate limits/timeouts


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_symbol_df(data: pd.DataFrame, yahoo_symbol: str) -> pd.DataFrame:
    """
    Safely extract a single symbol's OHLCV DataFrame from a batch download.
    Handles both MultiIndex (multi-ticker) and flat (single-ticker) columns.
    Returns empty DataFrame if symbol not present.
    """
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        level0 = data.columns.get_level_values(0).unique().tolist()
        if yahoo_symbol in level0:
            return data[yahoo_symbol].copy().dropna(how="all")
        level1 = data.columns.get_level_values(1).unique().tolist()
        if yahoo_symbol in level1:
            return data.xs(yahoo_symbol, axis=1, level=1).copy().dropna(how="all")
        return pd.DataFrame()
    else:
        expected = {"Open", "High", "Low", "Close", "Volume"}
        if expected.issubset(set(data.columns)):
            return data.dropna(how="all").copy()
        return pd.DataFrame()


def _batch_fetch(yahoo_symbols: list[str], period: str = "1y") -> pd.DataFrame:
    """
    Download OHLCV for a large universe in batches to avoid yfinance
    rate limits and connection timeouts.

    Splits yahoo_symbols into chunks of BATCH_SIZE (500), downloads each
    chunk separately with a 2s pause between batches, then concatenates
    all results into a single DataFrame.

    Returns empty DataFrame if all batches fail.
    """
    batches = [
        yahoo_symbols[i: i + BATCH_SIZE]
        for i in range(0, len(yahoo_symbols), BATCH_SIZE)
    ]
    frames = []

    for idx, batch in enumerate(batches, 1):
        logger.info(
            f"Downloading batch {idx}/{len(batches)} "
            f"({len(batch)} symbols)..."
        )
        try:
            df = fetch_ohlc(batch, period=period, interval="1d")
            if not df.empty:
                frames.append(df)
        except Exception as e:
            logger.warning(f"Batch {idx} failed: {e}")

        # Pause between batches — avoids hammering yfinance
        if idx < len(batches):
            time.sleep(2)

    if not frames:
        return pd.DataFrame()

    if len(frames) == 1:
        return frames[0]

    # Concatenate all batch results along columns axis
    try:
        return pd.concat(frames, axis=1)
    except Exception as e:
        logger.error(f"Failed to concatenate batch results: {e}")
        return frames[0]  # return first batch rather than nothing


# ── Step 1: Build Universe ───────────────────────────────────────────────────

def get_nse_universe() -> tuple[list[tuple[str, str, str]], set[str]]:
    """
    Load NSE symbols from nse_symbols.json on Google Drive.

    Filters out:
      - is_suspended = True
      - is_etf = True
      - series != "EQ"

    Falls back to NIFTY Total Market API if JSON is missing.

    Returns:
        universe : list of (symbol, yahoo_ticker, company)
        isins    : set of NSE ISINs for BSE deduplication
    """
    data = load("nse_symbols.json")

    if data and data.get("status") == "ok" and data.get("symbols"):
        all_symbols = data["symbols"]

        symbols = [
            s for s in all_symbols
            if s.get("series")           == "EQ"
            and not s.get("is_etf",       False)
            and not s.get("is_suspended", False)
        ]

        universe = [
            (s["symbol"], f"{s['symbol']}.NS", s.get("company", ""))
            for s in symbols
        ]
        isins = {s["isin"] for s in symbols if s.get("isin")}

        logger.info(
            f"NSE universe (Drive JSON): {len(universe)} EQ stocks "
            f"(filtered from {len(all_symbols)} total) "
            f"[updated: {data.get('timestamp', '—')}]"
        )
        return universe, isins

    # Fallback — NIFTY Total Market API (no company name or ISINs available)
    logger.warning(
        "nse_symbols.json not on Drive — falling back to NIFTY Total Market API. "
        "Run universe_updater.py to populate."
    )
    try:
        url      = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"
        api_data = fetch_nse(url)
        universe = [
            (item["symbol"], f"{item['symbol']}.NS", "")
            for item in api_data["data"]
            if item.get("priority") != 1 and item.get("symbol")
        ]
        logger.info(f"NSE universe (API fallback): {len(universe)} symbols")
        return universe, set()

    except Exception as e:
        logger.error(f"NSE API fallback failed: {e}")
        return [], set()


def get_bse_universe() -> list[tuple[str, str, str]]:
    """
    Load BSE symbols from bse_symbols.json on Google Drive.

    Returns list of (scrip_code, yahoo_ticker, company):
        [("542772", "542772.BO", "360 ONE WAM LIMITED"), ...]
    """
    data = load("bse_symbols.json")

    if not data or data.get("status") != "ok" or not data.get("symbols"):
        logger.warning(
            "bse_symbols.json not on Drive — skipping BSE universe. "
            "Run universe_updater.py to populate."
        )
        return []

    universe = [
        (item["scrip_code"], f"{item['scrip_code']}.BO", item.get("company", ""))
        for item in data["symbols"]
        if item.get("scrip_code")
    ]

    logger.info(
        f"BSE universe (Drive JSON): {len(universe)} stocks "
        f"[updated: {data.get('timestamp', '—')}]"
    )
    return universe


def get_universe() -> tuple[list[tuple[str, str]], int, int, dict[str, str]]:
    """
    Combine NSE EQ + BSE into the full screening universe.

    Also builds company_map — a yahoo_ticker → company name lookup dict.
    Built here once from already-loaded Drive JSONs (milliseconds, no extra
    network call). Used only by format_message() for screener.in URL slugs.

    Returns:
        universe    : list of (display_symbol, yahoo_ticker)
        nse_count   : number of NSE stocks
        bse_count   : number of BSE stocks
        company_map : dict of {yahoo_ticker: company_name}
    """
    nse_universe, nse_isins = get_nse_universe()
    bse_universe             = get_bse_universe()

    # Combine into (symbol, yahoo_ticker) tuples for downstream functions
    universe = [
        (sym, yt)
        for sym, yt, _ in nse_universe + bse_universe
    ]

    # Build company_map before stripping company field
    # yahoo_ticker → company name, used only in format_message()
    company_map = {
        yt: company
        for _, yt, company in nse_universe + bse_universe
    }

    nse_count = len(nse_universe)
    bse_count = len(bse_universe)

    logger.info(
        f"Total universe: {len(universe)} stocks "
        f"({nse_count} NSE + {bse_count} BSE)"
    )
    return universe, nse_count, bse_count, company_map


# ── Step 2: Compute Indicators ───────────────────────────────────────────────

def compute_indicators(
    universe: list[tuple[str, str]],
    data: pd.DataFrame,
) -> dict[str, dict]:
    """
    Compute all technical indicators for every symbol in ONE pass.
    Returns dict keyed by yahoo_ticker.
    """
    use_factors = SCREENER["score_factors"]
    indicators  = {}

    for sym, yahoo_symbol in universe:
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

            ret_22d = (
                (latest_close / float(close.iloc[-22]) - 1) * 100
                if len(close) >= 23 else 0.0
            )

            rsi = None
            if use_factors.get("rsi"):
                rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])

            passes = (
                ema9 > sma12
                and ema9 > sma26
                and latest_close > sma50
                and latest_close > sma200
                and latest_vol > avg_vol20
                and avg_vol20 >= MIN_ABS_VOLUME
            )

            indicators[yahoo_symbol] = {
                "sym":       sym,
                "yahoo":     yahoo_symbol,
                "exchange":  "BSE" if yahoo_symbol.endswith(".BO") else "NSE",
                "close":     latest_close,
                "volume":    latest_vol,
                "ema9":      ema9,
                "sma12":     sma12,
                "sma26":     sma26,
                "sma50":     sma50,
                "sma200":    sma200,
                "avg_vol20": avg_vol20,
                "ret_22d":   ret_22d,
                "rsi":       rsi,
                "passes":    passes,
            }

        except Exception as e:
            logger.warning(f"Indicator compute failed for {sym}: {e}")
            continue

    return indicators


# ── Step 3: Apply Filter ─────────────────────────────────────────────────────

def apply_filter(indicators: dict[str, dict]) -> list[str]:
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
                "symbol":   ind["sym"],
                "exchange": ind["exchange"],
                "score":    round(float(total), 3),
            })

        except Exception as e:
            logger.warning(f"Score failed for {ysym}: {e}")

    return pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)


# ── Telegram message ─────────────────────────────────────────────────────────

def _company_to_slug(company: str) -> str:
    """Convert company name to a screener.in URL slug."""
    slug = company.lower().strip()
    slug = slug.replace(" ", "-")
    slug = slug.replace(".", "")
    slug = slug.replace("'", "")
    slug = slug.replace("&", "and")
    slug = slug.replace(",", "")
    slug = slug.replace("(", "")
    slug = slug.replace(")", "")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def format_message(
    ranked_df: pd.DataFrame,
    ts: str,
    company_map: dict[str, str],
) -> str:
    if ranked_df.empty:
        return f"📊 <b>Stock Screener</b> ({ts})\n\nNo signals today."

    msg = f"📊 <b>Stock Screener</b> ({ts})\n\n"

    for i, row in enumerate(ranked_df.head(20).itertuples(), 1):
        exchange = getattr(row, "exchange", "NSE")
        yahoo_ticker = f"{row.symbol}.BO" if exchange == "BSE" else f"{row.symbol}.NS"
        display_name = company_map.get(yahoo_ticker, row.symbol)

        if exchange == "NSE":
            url = f"https://www.screener.in/company/{row.symbol}/"
        else:
            company = company_map.get(yahoo_ticker, "")
            if company:
                slug = _company_to_slug(company)
                url  = f"https://www.screener.in/company/{slug}/"
            else:
                url = f"https://www.screener.in/company/{row.symbol}/"

        msg += f"{i}. ✅ <a href='{url}'>{display_name}</a>\n"

    msg += "\n💡 EMA/SMA trend + volume filters."
    return msg


# ── run() ────────────────────────────────────────────────────────────────────

def run() -> dict:
    ts = timestamp_str()
    try:
        # 1. Build universe from Drive JSONs + company_map
        universe, nse_count, bse_count, company_map = get_universe()

        if not universe:
            raise RuntimeError(
                "Universe is empty. Run universe_updater.py first to "
                "populate nse_symbols.json and bse_symbols.json on Drive."
            )

        yahoo_symbols = [yt for _, yt in universe]

        # 2. Batched OHLCV download — splits universe into chunks of 500
        #    to avoid yfinance rate limits and connection timeouts
        data = _batch_fetch(yahoo_symbols, period="1y")
        if data.empty:
            raise RuntimeError("yfinance returned empty DataFrame for the universe.")

        # 3. Compute indicators in one pass
        indicators = compute_indicators(universe, data)
        logger.info(f"Indicators computed for {len(indicators)} symbols")

        # 4. Apply hard filter
        passed = apply_filter(indicators)

        # 5. Score and rank
        ranked_df   = score_and_rank(passed, indicators)
        stocks_list = ranked_df.to_dict(orient="records")

        result = {
            "timestamp":      ts,
            "status":         "ok",
            "total_universe": len(universe),
            "nse_universe":   nse_count,
            "bse_universe":   bse_count,
            "passed_count":   len(passed),
            "stocks":         stocks_list,
        }

        save("screener.json", result)
        send_message(format_message(ranked_df, ts, company_map), parse_mode="HTML")

        print(
            f"Screener done — {len(passed)}/{len(universe)} passed "
            f"({nse_count} NSE + {bse_count} BSE universe)."
        )
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