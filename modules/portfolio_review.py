import logging
import os
import numpy as np
import pandas as pd
import yfinance as yf
from config import PORTFOLIO
from datetime import datetime
from core.db import save
from core.gsheets import get_gspread_client, get_worksheet
from core.notifier import send_message
from core.utils import timestamp_str, normalize_ohlc
from core.fetcher import fetch_ohlc

logger = logging.getLogger(__name__)

NIFTY           = PORTFOLIO["nifty_ticker"]
GOOGLE_SHEET_ID   = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SHEET_NAME = "Auto_Portfolio_Reviewer"
WORKSHEET_NAME  = PORTFOLIO["worksheet_name"]

# =========================
# Indicators (your original logic)
# =========================
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = np.maximum(
        df["High"] - df["Low"],
        np.maximum(
            abs(df["High"] - df["Close"].shift()),
            abs(df["Low"]  - df["Close"].shift()),
        ),
    )
    return tr.rolling(period).mean()

def relative_strength(stock_df: pd.DataFrame, nifty_df: pd.DataFrame,
                      lookback: int = 30) -> float:
    if len(stock_df) < lookback + 1 or len(nifty_df) < lookback + 1:
        return 0.0
    return (
        (stock_df["Close"].iloc[-1] / stock_df["Close"].iloc[-lookback] - 1)
        - (nifty_df["Close"].iloc[-1] / nifty_df["Close"].iloc[-lookback] - 1)
    ) * 100

def supertrend(df: pd.DataFrame, period: int = 10, multiplier: int = 3) -> str:
    """Fixed: uses .loc[] to avoid chained assignment pandas warning."""
    df = df.copy().reset_index(drop=True)
    hl2         = (df["High"] + df["Low"]) / 2
    df["atr"]   = atr(df, period)
    df["upper"] = hl2 + multiplier * df["atr"]
    df["lower"] = hl2 - multiplier * df["atr"]
    df["f_upper"]   = 0.0
    df["f_lower"]   = 0.0
    df["uptrend"]   = True

    for i in range(1, len(df)):
        # Final upper band
        if (df.loc[i, "upper"] < df.loc[i - 1, "f_upper"]
                or df.loc[i - 1, "Close"] > df.loc[i - 1, "f_upper"]):
            df.loc[i, "f_upper"] = df.loc[i, "upper"]
        else:
            df.loc[i, "f_upper"] = df.loc[i - 1, "f_upper"]
        # Final lower band
        if (df.loc[i, "lower"] > df.loc[i - 1, "f_lower"]
                or df.loc[i - 1, "Close"] < df.loc[i - 1, "f_lower"]):
            df.loc[i, "f_lower"] = df.loc[i, "lower"]
        else:
            df.loc[i, "f_lower"] = df.loc[i - 1, "f_lower"]
        # Trend direction
        if df.loc[i, "Close"] > df.loc[i - 1, "f_upper"]:
            df.loc[i, "uptrend"] = True
        elif df.loc[i, "Close"] < df.loc[i - 1, "f_lower"]:
            df.loc[i, "uptrend"] = False
        else:
            df.loc[i, "uptrend"] = df.loc[i - 1, "uptrend"]

    return "Buy" if df.loc[len(df) - 1, "uptrend"] else "Sell"

# =========================
# Analyze single stock (your original logic + RS re-enabled)
# =========================
def analyze_stock(row: dict, df: pd.DataFrame, nifty_df: pd.DataFrame) -> dict:
    if len(df) < 50:
        last_price = float(df["Close"].iloc[-1])
        return {
            "current_price": last_price,
            "pct_change":    0.0,
            "rs":            0.0,
            "ema_trend":     "N/A",
            "supertrend":    "N/A",
            "trailing_sl":   row.get("current_sl", row.get("initial_sl", last_price * 0.95)),
            "ema_20":        0.0,
            "ema_50":        0.0,
            "trend_state":   "N/A",
            "risk_status":   "N/A",
            "pnl_pct":       0.0,
            "signal":        "HOLD",
        }

    last_price = float(df["Close"].iloc[-1])
    prev_price = float(df["Close"].iloc[-2])

    # EMAs
    ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
    ema50 = float(df["Close"].ewm(span=50).mean().iloc[-1])

    # SuperTrend
    st_signal = supertrend(df)

    # Relative strength vs NIFTY (re-enabled)
    rs = relative_strength(df, nifty_df)

    # Trailing stop loss
    prev_sl      = float(row.get("current_sl") or row.get("initial_sl") or last_price * 0.95)
    trailing_sl  = max(prev_sl, last_price * 0.95)

    # P&L
    buy_price = float(row.get("buy_price", last_price))
    pnl_pct   = (last_price - buy_price) / buy_price * 100
    pct_change = (last_price - prev_price) / prev_price * 100

    # Trend state
    if st_signal == "Buy"  and ema20 > ema50: trend_state = "UPTREND"
    elif st_signal == "Sell" and ema20 < ema50: trend_state = "DOWNTREND"
    else:                                       trend_state = "NEUTRAL"

    # Risk status
    risk_status = "BREACHED" if last_price < trailing_sl else "ACTIVE"

    # Signal
    if risk_status == "BREACHED":   signal = "EXIT"
    elif trend_state == "DOWNTREND": signal = "SELL"
    else:                            signal = "HOLD"

    return {
        "current_price": round(last_price, 2),
        "pct_change":    round(pct_change,  2),
        "rs":            round(rs,           2),
        "ema_20":        round(ema20,        2),
        "ema_50":        round(ema50,        2),
        "supertrend":    st_signal,
        "trend_state":   trend_state,
        "risk_status":   risk_status,
        "trailing_sl":   round(trailing_sl,  2),
        "pnl_pct":       round(pnl_pct,      2),
        "signal":        signal,
    }

# =========================
# Write computed columns back to Sheet (your original logic)
# =========================
def update_sheet(sheet, row_idx: int, r: dict) -> None:
    sheet.update(
        range_name=f"E{row_idx}:N{row_idx}",
        values=[[
            r["trailing_sl"],
            r["current_price"],
            r["pct_change"],
            r["supertrend"],
            r["ema_20"],
            r["ema_50"],
            r["trend_state"],
            r["risk_status"],
            r["pnl_pct"],
            r["signal"],
        ]],
    )

# =========================
# Format per-stock Telegram alert (your original logic)
# =========================
def format_alert(ticker: str, result: dict) -> str:
    return (
        f"🔔 <b>{ticker}</b>\n"
        f"Signal: <b>{result['signal']}</b>\n"
        f"Price:  ₹{result['current_price']:.2f}\n"
        f"P&amp;L:   {result['pnl_pct']:.2f}%\n"
        f"Trend:  {result['trend_state']}\n"
        f"Risk:   {result['risk_status']}\n"
        f"RS vs NIFTY: {result['rs']:.2f}%"
    )

# =========================
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        # 1. Connect to Google Sheet (source of truth for holdings)
        client    = get_gspread_client()
        sheet     = get_worksheet(client, GOOGLE_SHEET_ID, WORKSHEET_NAME)
        data      = pd.DataFrame(sheet.get_all_records())

        if data.empty:
            raise ValueError("Holdings sheet is empty.")

        # 2. Batch download NIFTY + all holdings at once
        tickers = [
            (t if t.endswith(".NS") else t + ".NS")
            for t in data["ticker"].tolist()
        ]
        all_tickers = [NIFTY] + tickers
        raw = fetch_ohlc(all_tickers, period="6mo", interval="1d")
    
        nifty_df = normalize_ohlc(
            raw[NIFTY] if NIFTY in raw.columns.get_level_values(0)
            else pd.DataFrame()
        )

        # 3. Analyze each holding
        holdings  = []
        alerts    = []
        valid_ct  = 0

        for i, row in data.iterrows():
            ticker = row["ticker"]
            symbol = ticker if ticker.endswith(".NS") else ticker + ".NS"
            row_idx = i + 2  # Sheet row (1=header, data starts row 2)

            try:
                df = normalize_ohlc(
                raw[symbol] if symbol in raw.columns.get_level_values(0)
                else pd.DataFrame()
                )
                
                if df.empty or len(df) < 50:
                    logger.warning(f"Skipping {symbol}: insufficient data")
                    continue

                result  = analyze_stock(row.to_dict(), df, nifty_df)
                valid_ct += 1   

                # Compare BEFORE writing last_signal & Alert if signal changed
                if result["signal"] != str(row.get("last_signal", "")):
                    alerts.append(format_alert(ticker, result))

                # Write computed columns (does NOT touch last_signal column)
                update_sheet(sheet, row_idx, result)

                holdings.append({"ticker": ticker, **result})

                # Now write last_signal = current signal (becomes "previous" on next run)
                sheet.update(range_name=f"O{row_idx}", values=[[result["signal"]]])

            except Exception as e:
                logger.warning(f"analyze_stock failed for {symbol}: {e}")
                continue

        # 4. Portfolio summary
        avg_pnl    = round(sum(h["pnl_pct"] for h in holdings) / valid_ct, 2) if valid_ct else 0
        exit_count = sum(1 for h in holdings if h["signal"] == "EXIT")
        sell_count = sum(1 for h in holdings if h["signal"] == "SELL")
        hold_count = sum(1 for h in holdings if h["signal"] == "HOLD")

        result_dict = {
            "timestamp":  ts,
            "status":     "ok",
            "holdings":   holdings,
            "avg_pnl":    avg_pnl,
            "total":      valid_ct,
            "exit_count": exit_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
        }

        # 5. Save to data/portfolio_review.json for Streamlit
        save("portfolio_review.json", result_dict)

        # 6. Send Telegram alerts (only changed signals)
        if alerts:
            summary = (
                f"\n\n📊 <b>Portfolio Summary</b>\n"
                f"Avg P&amp;L: {avg_pnl:.2f}% | "
                f"EXIT: {exit_count} | SELL: {sell_count} | HOLD: {hold_count}"
            )
            send_message("\n\n".join(alerts) + summary, parse_mode="HTML")
        else:
            send_message(
                f"✅ <b>Portfolio Review</b> — {ts}\n"
                f"No signal changes today.\n"
                f"Avg P&amp;L: {avg_pnl:.2f}% across {valid_ct} holdings.",
                parse_mode="HTML",
            )

        print(f"Portfolio review done — {valid_ct} stocks, avg P&L: {avg_pnl:.2f}%")
        return result_dict

    except Exception as e:
        logger.error(f"portfolio_review run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("portfolio_review.json", error_result)
        send_message(
            f"❌ <b>Portfolio Reviewer failed</b>\n<code>{e}</code>",
            parse_mode="HTML",
        )
        return error_result

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()