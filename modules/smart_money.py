import logging
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests

from core.db import save, load
from core.notifier import send_message, send_photo
from core.utils import timestamp_str

logger = logging.getLogger(__name__)

HISTORY_FILE = "smart_money.json"
MAX_HISTORY  = 60   # days to keep in JSON

# =========================
# Fetch FII/DII (your original logic)
# =========================
def fetch_fii_dii_data() -> tuple[dict, dict]:
    print("Fetching FII/DII data from NSE...")
    url     = "https://www.nseindia.com/api/fiidiiTradeReact"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r    = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        if isinstance(data, list) and len(data) >= 2:
            fii = data[1] if "FII" in data[1]["category"] else data[0]
            dii = data[0] if "DII" in data[0]["category"] else data[1]
            print(f"Fetched — FII net: {fii['netValue']}, DII net: {dii['netValue']}")
            return fii, dii
        raise ValueError("Unexpected NSE API response structure.")
    except Exception as e:
        raise RuntimeError(f"fetch_fii_dii_data failed: {e}") from e

# =========================
# History helpers — replaces Google Sheets
# =========================
def load_history() -> list[dict]:
    data = load(HISTORY_FILE, default={})
    return data.get("history", [])

def append_daily_record(fii: dict, dii: dict, history: list[dict]) -> list[dict]:
    """Append today's row, deduplicate by date, keep last MAX_HISTORY entries."""
    new_row = {
        "date":     fii.get("date", ""),
        "fii_buy":  fii.get("buyValue", 0),
        "fii_sell": fii.get("sellValue", 0),
        "fii_net":  fii.get("netValue", 0),
        "dii_buy":  dii.get("buyValue", 0),
        "dii_sell": dii.get("sellValue", 0),
        "dii_net":  dii.get("netValue", 0),
    }
    # Deduplicate: remove existing entry for same date if re-run today
    history = [r for r in history if r.get("date") != new_row["date"]]
    history.append(new_row)
    return history[-MAX_HISTORY:]   # keep latest MAX_HISTORY rows

# =========================
# Plot trend (your original logic — reads from JSON history)
# =========================
def plot_trend(history: list[dict], chart_path: str = "fii_dii_trend.png") -> str | None:
    try:
        df = pd.DataFrame(history).tail(10)
        if df.empty or "date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date")

        plt.figure(figsize=(8, 5))
        plt.plot(df["Date"], df["fii_net"], marker="o", label="FII Net")
        plt.plot(df["Date"], df["dii_net"], marker="o", label="DII Net")
        plt.title("Smart Money Flow — Last 10 Days")
        plt.xlabel("Date")
        plt.ylabel("Net Value (₹ Cr)")
        plt.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        plt.grid(True)
        plt.legend()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig(chart_path, dpi=120)
        plt.close()
        print(f"Chart saved: {chart_path}")
        return chart_path
    except Exception as e:
        logger.warning(f"plot_trend failed: {e}")
        return None

# =========================
# Format Telegram message (your original format)
# =========================
def format_message(fii: dict, dii: dict, timestamp: str) -> str:
    return (
        f"<b>📊 Smart Money Flow (NSE)</b>\n"
        f"Date: {fii.get('date', '—')}\n"
        f"Updated: {timestamp}\n\n"
        f"<b>FII:</b>\n"
        f"Buy:  ₹{fii.get('buyValue', '—')} Cr\n"
        f"Sell: ₹{fii.get('sellValue', '—')} Cr\n"
        f"Net:  ₹{fii.get('netValue', '—')} Cr\n\n"
        f"<b>DII:</b>\n"
        f"Buy:  ₹{dii.get('buyValue', '—')} Cr\n"
        f"Sell: ₹{dii.get('sellValue', '—')} Cr\n"
        f"Net:  ₹{dii.get('netValue', '—')} Cr"
    )

# =========================
# Signal helper — simple interpretation for dashboard
# =========================
def interpret_flow(fii_net, dii_net) -> str:
    try:
        fn = float(str(fii_net).replace(",", ""))
        dn = float(str(dii_net).replace(",", ""))
        if fn > 0 and dn > 0:   return "Both buying 🟢 Bullish"
        if fn < 0 and dn < 0:   return "Both selling 🔴 Bearish"
        if fn > 0 and dn < 0:   return "FII buying, DII selling 🟡 Cautious"
        if fn < 0 and dn > 0:   return "DII supporting, FII selling 🟡 Mixed"
    except Exception:
        pass
    return "—"

# =========================
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        fii, dii = fetch_fii_dii_data()
        history  = load_history()
        history  = append_daily_record(fii, dii, history)

        signal = interpret_flow(fii.get("netValue"), dii.get("netValue"))

        result = {
            "timestamp": ts,
            "status":    "ok",
            "latest": {
                "date":     fii.get("date"),
                "fii_buy":  fii.get("buyValue"),
                "fii_sell": fii.get("sellValue"),
                "fii_net":  fii.get("netValue"),
                "dii_buy":  dii.get("buyValue"),
                "dii_sell": dii.get("sellValue"),
                "dii_net":  dii.get("netValue"),
                "signal":   signal,
            },
            "history": history,
        }

        # 1. Save to data/smart_money.json
        save(HISTORY_FILE, result)

        # 2. Build and send chart + message
        chart_path = plot_trend(history)
        message    = format_message(fii, dii, ts)

        if chart_path:
            send_photo(chart_path, caption=message, parse_mode="HTML")
        else:
            send_message(message, parse_mode="HTML")

        print(f"Smart money done — signal: {signal}")
        return result

    except Exception as e:
        logger.error(f"smart_money run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save(HISTORY_FILE, error_result)
        send_message(f"❌ <b>Smart Money Tracker failed</b>\n<code>{e}</code>",
                     parse_mode="HTML")
        return error_result

if __name__ == "__main__":
    run()