import logging
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
from ta.momentum import RSIIndicator
from config import SCREENER
from core.db import save
from core.notifier import send_message
from core.utils import timestamp_str, safe_scalar, normalize_ohlc
from core.fetcher import fetch_ohlc, fetch_nse

logger = logging.getLogger(__name__)

# =========================
# Fetch NIFTY TOTAL MARKET Universe
# =========================
def get_nifty_symbols() -> list[str]:
    url  = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"
    data = fetch_nse(url)
    symbols = [
        item["symbol"]
        for item in data["data"]
        if item.get("priority") != 1 and item.get("symbol")
    ]
    logger.info(f"Universe fetched: {len(symbols)} symbols")
    return symbols

# =========================
# Apply Filters (Batch Download)
# =========================
def apply_filters_batch(symbols: list[str]) -> tuple[list[str], pd.DataFrame]:
    """Returns (passed_symbols, full_data_df) — df reused in score_and_rank."""
    yahoo_symbols = [f"{sym}.NS" for sym in symbols]
    data = fetch_ohlc(yahoo_symbols, period="365d", interval="1d")
    passed_stocks = []
    for sym in symbols:
        yahoo_symbol = f"{sym}.NS"
        try:
            if yahoo_symbol not in data.columns.get_level_values(0):
                continue
            df = data[yahoo_symbol].dropna()
            if df.empty or len(df) < 200:
                continue
            close  = df["Close"]
            volume = df["Volume"]
            ema9   = close.ewm(span=9).mean().iloc[-1]
            sma12  = close.rolling(window=12).mean().iloc[-1]
            sma26  = close.rolling(window=26).mean().iloc[-1]
            sma50  = close.rolling(window=50).mean().iloc[-1]
            sma200 = close.rolling(window=200).mean().iloc[-1]
            avg_vol20    = volume.tail(20).mean()
            latest_close = close.iloc[-1]
            latest_vol   = volume.iloc[-1]
            if (
                ema9 > sma12
                and ema9 > sma26
                and latest_close > sma50
                and latest_close > sma200
                and latest_vol > avg_vol20
            ):
                passed_stocks.append(sym)
        except Exception as e:
            logger.warning(f"Filter error for {sym}: {e}")
    print(f"Passed filter: {len(passed_stocks)}/{len(symbols)}")
    return passed_stocks, data  # return data so score_and_rank reuses it

# =========================
# Score & Rank  (reuses already-downloaded data — no second yf.download)
# =========================
def score_and_rank(
    filtered_stocks: list[str],
    data,                          # the df from apply_filters_batch
    use_factors: dict = None,
    weights: dict = None,
) -> pd.DataFrame:
    if use_factors is None:
        use_factors = SCREENER["score_factors"]
    if weights is None:
        weights = SCREENER["score_weights"]

    results = []
    for sym in filtered_stocks:
        yahoo_symbol = f"{sym}.NS"
        try:
            if yahoo_symbol not in data.columns.get_level_values(0):
                continue
            df = data[yahoo_symbol].dropna()
            if df.empty or len(df) < 200:
                continue
            close  = df["Close"]
            volume = df["Volume"]
            sma50      = close.rolling(50).mean().iloc[-1]
            sma200     = close.rolling(200).mean().iloc[-1]
            avg_vol20  = volume.tail(20).mean()
            latest_vol = volume.iloc[-1]
            scores = {}
            scores["momentum"] = (
                (close.iloc[-1] - close.iloc[-22]) / close.iloc[-22] * 100
                if use_factors.get("momentum") else 0
            )
            scores["trend"] = (
                (close.iloc[-1] / sma50) + (sma50 / sma200)
                if use_factors.get("trend") else 0
            )
            if use_factors.get("rsi"):
                rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
                scores["rsi"] = 1 if 50 <= rsi <= 70 else 0.5 if rsi > 70 else 0
            else:
                scores["rsi"] = 0
            scores["volume"] = (
                latest_vol / avg_vol20 if use_factors.get("volume") and avg_vol20 else 0
            )
            total_score = sum(scores[f] * weights.get(f, 0) for f in scores)
            results.append({"symbol": sym, "score": round(float(total_score), 3)})
        except Exception as e:
            logger.warning(f"Score error for {sym}: {e}")

    return pd.DataFrame(results).sort_values("score", ascending=False)

# =========================
# Format Telegram Message
# =========================
def format_message(ranked_df: pd.DataFrame) -> str:
    today = timestamp_str()
    if ranked_df.empty:
        return f"📊 *Stock Screener* ({today})\n\nNo signals today."
    msg = f"📊 *Stock Screener* ({today})\n\n"
    for i, row in enumerate(ranked_df.itertuples(), 1):
        msg += f"{i}. ✅ [{row.symbol}](https://www.screener.in/company/{row.symbol}/) — score: `{row.score}`\n"
    msg += "\n💡 Based on EMA/SMA trend + volume filters."
    return msg

# =========================
# run() — called by GitHub Actions workflow
# =========================
def run() -> dict:
    try:
        universe              = get_nifty_symbols()
        passed, data          = apply_filters_batch(universe)
        ranked_df             = score_and_rank(passed, data)

        stocks_list = ranked_df.to_dict(orient="records")

        result = {
            "timestamp":       timestamp_str(),
            "total_universe":  len(universe),
            "passed_count":    len(passed),
            "stocks":          stocks_list,
            "status":          "ok",
        }

        # 1. Save to data/screener.json (Streamlit reads this)
        save("screener.json", result)

        # 2. Send Telegram alert
        send_message(format_message(ranked_df))

        print(f"Screener done — {len(passed)} stocks passed.")
        return result

    except Exception as e:
        logger.error(f"Screener run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": timestamp_str()}
        save("screener.json", error_result)
        send_message(f"❌ *Stock Screener failed*\n`{e}`")
        return error_result

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()