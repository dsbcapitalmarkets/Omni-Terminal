import logging
from datetime import datetime
import os
import pandas as pd
import requests
import yfinance as yf
from config import MARKET_BREADTH
from core.db import save, load
from core.gsheets import get_gspread_client, get_worksheet
from core.notifier import send_message
from core.utils import timestamp_str, normalize_ohlc
from core.fetcher import fetch_ohlc, fetch_nse

logger = logging.getLogger(__name__)

GOOGLE_SHEET_ID   = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SHEET_NAME = MARKET_BREADTH["google_sheet_name"]
WORKSHEET_NAME    = MARKET_BREADTH["worksheet_name"]
SHEET_HEADERS     = [
    "timestamp", "advances", "declines", "unchanged",
    "new_highs", "new_lows", "ad_ratio", "nh_nl_spread",
    "num_above_50", "pct_above_50", "num_above_200", "pct_above_200", "regime",
]

MAX_HISTORY = 60   # rolling window kept in breadth.json (mirrors smart_money)


# =========================
# Fetch NSE data (unchanged)
# =========================
def get_nse_data() -> tuple[dict, list[str]]:
    url      = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"
    response = fetch_nse(url)
    nse_data = response["data"]

    symbols   = []
    advances  = declines = unchanged = 0
    new_highs = new_lows = 0

    for item in nse_data:
        if item.get("priority") == 1:
            continue
        symbol = item.get("symbol")
        if symbol:
            symbols.append(symbol + ".NS")
        try:
            p_change = float(item.get("pChange", 0))
            if p_change > 0:    advances  += 1
            elif p_change < 0:  declines  += 1
            else:               unchanged += 1
        except Exception:
            continue
        try:
            last_price = float(item.get("lastPrice", 0))
            year_high  = float(item.get("yearHigh",  0))
            year_low   = float(item.get("yearLow",   0))
            tol        = 1
            if year_high > 0 and last_price >= year_high * (1 - tol / 100):
                new_highs += 1
            if year_low > 0 and last_price <= year_low * (1 + tol / 100):
                new_lows += 1
        except Exception:
            continue

    ad_ratio     = round(advances / declines, 2) if declines != 0 else 0
    nh_nl_spread = new_highs - new_lows

    breadth = {
        "advances":     advances,
        "declines":     declines,
        "unchanged":    unchanged,
        "new_highs":    new_highs,
        "new_lows":     new_lows,
        "ad_ratio":     ad_ratio,
        "nh_nl_spread": nh_nl_spread,
    }
    return breadth, symbols


# =========================
# Compute DMA counts (unchanged)
# =========================
def compute_dma_counts(symbols: list[str]) -> tuple[int, float, int, float]:
    data = fetch_ohlc(symbols, period="1y", interval="1d")
    num_above_50 = num_above_200 = valid_stocks = 0

    for sym in symbols:
        try:
            df = data[sym].dropna()
            if df.empty or len(df) < 200:
                continue
            valid_stocks += 1
            close = df["Close"]
            if close.iloc[-1] > close.rolling(50).mean().iloc[-1]:
                num_above_50 += 1
            if close.iloc[-1] > close.rolling(200).mean().iloc[-1]:
                num_above_200 += 1
        except Exception as e:
            logger.warning(f"DMA compute skipped {sym}: {e}")
            continue

    pct_50  = round((num_above_50  / valid_stocks) * 100, 2) if valid_stocks else 0
    pct_200 = round((num_above_200 / valid_stocks) * 100, 2) if valid_stocks else 0
    return num_above_50, pct_50, num_above_200, pct_200


# =========================
# Regime classifier (unchanged)
# =========================
def classify_regime(pct_200: float, nh: int, nl: int) -> str:
    if pct_200 > 65 and nh > nl:    return "🟢 Strong Bullish Breadth"
    if pct_200 < 35 and nl > nh:    return "🔴 Bearish Expansion"
    if 40 <= pct_200 <= 60:         return "🟡 Transition Zone"
    return "⚪ Mixed Breadth"


# =========================
# History management — mirrors smart_money pattern
# =========================
def _load_history() -> list[dict]:
    """Load existing history from breadth.json, return [] if not found."""
    existing = load("breadth.json", default={})
    return existing.get("history", [])


def _append_history(history: list[dict], breadth: dict, regime: str) -> list[dict]:
    """
    Append today's snapshot to the rolling history list.
    Deduplicates by date so re-runs on the same day don't double-add.
    Keeps the last MAX_HISTORY entries.
    """
    today = datetime.now().strftime("%d-%b-%Y")

    new_row = {
        "date":          today,
        "num_above_50":  breadth["num_above_50"],
        "pct_above_50":  breadth["pct_above_50"],
        "num_above_200": breadth["num_above_200"],
        "pct_above_200": breadth["pct_above_200"],
        "advances":      breadth["advances"],
        "declines":      breadth["declines"],
        "ad_ratio":      breadth["ad_ratio"],
        "nh_nl_spread":  breadth["nh_nl_spread"],
        "regime":        regime,
    }

    # Remove any existing entry for today (idempotent re-run)
    history = [r for r in history if r.get("date") != today]
    history.append(new_row)

    # Keep rolling window
    return history[-MAX_HISTORY:]


# =========================
# Format Telegram message (unchanged)
# =========================
def format_message(results: dict, regime: str, timestamp: str) -> str:
    return f"""📊 *Market Breadth — Nifty Total Market*
━━━━━━━━━━━━━━━━━━
🕐 {timestamp}

🔼 Advances:  {results['advances']}
🔽 Declines:  {results['declines']}
⚖️ Unchanged: {results['unchanged']}
⚖️ A/D Ratio: {results['ad_ratio']}

🚀 52W High:     {results['new_highs']}
💀 52W Low:      {results['new_lows']}
📈 NH-NL Spread: {results['nh_nl_spread']}

📊 Above 50 DMA:  {results['num_above_50']} stocks ({results['pct_above_50']}%)
🏦 Above 200 DMA: {results['num_above_200']} stocks ({results['pct_above_200']}%)

🧭 Regime: {regime}
━━━━━━━━━━━━━━━━━━"""


# =========================
# Write to Google Sheet (unchanged)
# =========================
def write_to_gsheet(worksheet, results: dict, regime: str) -> None:
    row = {**results, "regime": regime,
           "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    values = [row[k] for k in SHEET_HEADERS]
    worksheet.append_row(values)
    logger.info("Market breadth row appended to Google Sheet.")


# =========================
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        # 1. Fetch NSE breadth data
        breadth, symbols = get_nse_data()

        # 2. Compute DMA counts
        num_50, pct_50, num_200, pct_200 = compute_dma_counts(symbols)
        breadth.update({
            "num_above_50":  num_50,
            "pct_above_50":  pct_50,
            "num_above_200": num_200,
            "pct_above_200": pct_200,
        })

        # 3. Classify regime
        regime = classify_regime(pct_200, breadth["new_highs"], breadth["new_lows"])

        # 4. Write to Google Sheet (historical log)
        try:
            client    = get_gspread_client()
            worksheet = get_worksheet(client, GOOGLE_SHEET_ID, WORKSHEET_NAME)
            write_to_gsheet(worksheet, breadth, regime)
        except Exception as e:
            logger.warning(f"Google Sheet write failed (non-fatal): {e}")

        # 5. Load existing history → append today → keep rolling window
        history = _load_history()
        history = _append_history(history, breadth, regime)

        # 6. Build result dict (history included — same shape as smart_money.json)
        result = {
            "timestamp":    ts,
            "status":       "ok",
            "regime":       regime,
            **breadth,
            "history":      history,
        }

        # 7. Save to breadth.json for Streamlit dashboard
        save("breadth.json", result)

        # 8. Send Telegram alert
        send_message(format_message(breadth, regime, ts))

        print(f"Market breadth done — regime: {regime}, history: {len(history)} rows")
        return result

    except Exception as e:
        logger.error(f"market_breadth run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("breadth.json", error_result)
        send_message(f"❌ *Market Breadth Tracker failed*\n`{e}`")
        return error_result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()