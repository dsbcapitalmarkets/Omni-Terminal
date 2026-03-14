import logging
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import requests

from core.db import save, load
from core.gsheets import get_gspread_client, open_or_create_sheet
from core.notifier import send_message, send_photo
from core.utils import timestamp_str

logger = logging.getLogger(__name__)

GOOGLE_SHEET_NAME = "Smart_Money_Flow_Tracker"
WORKSHEET_NAME    = "Sheet1"
SHEET_HEADERS     = ["Date", "FII_Buy", "FII_Sell", "FII_Net",
                      "DII_Buy", "DII_Sell", "DII_Net"]
MAX_HISTORY       = 60

# =========================
# Fetch FII/DII from NSE (your original logic)
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
# Google Sheet — append row (your original logic)
# =========================
def save_to_google_sheet(sheet, fii: dict, dii: dict) -> None:
    try:
        row = [
            fii["date"],
            fii["buyValue"], fii["sellValue"], fii["netValue"],
            dii["buyValue"], dii["sellValue"], dii["netValue"],
        ]
        sheet.append_row(row)
        print("Row appended to Google Sheet.")
    except Exception as e:
        logger.warning(f"Google Sheet append failed (non-fatal): {e}")

# =========================
# Plot trend from Sheet history (your original logic)
# =========================
def plot_trend(sheet, chart_path: str = "fii_dii_trend.png") -> str | None:
    try:
        records = sheet.get_all_records()
        df      = pd.DataFrame(records)
        if df.empty or "Date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date").tail(10)

        # Convert net columns to numeric
        for col in ["FII_Net", "DII_Net"]:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""), errors="coerce"
                )

        print("Plotting 10-day trend...")
        plt.figure(figsize=(8, 5))
        plt.plot(df["Date"], df["FII_Net"], marker="o", label="FII Net Value")
        plt.plot(df["Date"], df["DII_Net"], marker="o", label="DII Net Value")
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
# Build JSON history from Sheet (for Streamlit dashboard)
# =========================
def build_history_from_sheet(sheet) -> list[dict]:
    try:
        records = sheet.get_all_records()
        history = []
        for r in records[-MAX_HISTORY:]:
            history.append({
                "date":     r.get("Date",     ""),
                "fii_buy":  r.get("FII_Buy",  0),
                "fii_sell": r.get("FII_Sell", 0),
                "fii_net":  r.get("FII_Net",  0),
                "dii_buy":  r.get("DII_Buy",  0),
                "dii_sell": r.get("DII_Sell", 0),
                "dii_net":  r.get("DII_Net",  0),
            })
        return history
    except Exception as e:
        logger.warning(f"build_history_from_sheet failed: {e}")
        return []

# =========================
# Signal interpretation
# =========================
def interpret_flow(fii_net, dii_net) -> str:
    try:
        fn = float(str(fii_net).replace(",", ""))
        dn = float(str(dii_net).replace(",", ""))
        if fn > 0 and dn > 0:  return "Both buying 🟢 Bullish"
        if fn < 0 and dn < 0:  return "Both selling 🔴 Bearish"
        if fn > 0 and dn < 0:  return "FII buying, DII selling 🟡 Cautious"
        if fn < 0 and dn > 0:  return "DII supporting, FII selling 🟡 Mixed"
    except Exception:
        pass
    return "—"

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
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        # 1. Connect to Google Sheet
        client    = get_gspread_client()
        sheet     = open_or_create_sheet(
            client, GOOGLE_SHEET_NAME, WORKSHEET_NAME, SHEET_HEADERS
        )

        # 2. Fetch FII/DII data from NSE
        fii, dii = fetch_fii_dii_data()

        # 3. Append row to Google Sheet (historical log)
        save_to_google_sheet(sheet, fii, dii)

        # 4. Build history + signal
        history = build_history_from_sheet(sheet)
        signal  = interpret_flow(fii.get("netValue"), dii.get("netValue"))

        # 5. Build result dict
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

        # 6. Save to Drive (for Streamlit dashboard)
        save("smart_money.json", result)

        # 7. Generate chart from Sheet history + send to Telegram
        message    = format_message(fii, dii, ts)
        chart_path = plot_trend(sheet)

        if chart_path:
            send_photo(chart_path, caption=message, parse_mode="HTML")
        else:
            send_message(message, parse_mode="HTML")

        print(f"Smart money done — signal: {signal}")
        return result

    except Exception as e:
        logger.error(f"smart_money run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("smart_money.json", error_result)
        send_message(
            f"❌ <b>Smart Money Tracker failed</b>\n<code>{e}</code>",
            parse_mode="HTML",
        )
        return error_result

if __name__ == "__main__":
    run()