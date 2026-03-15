import logging
import pandas as pd
import yfinance as yf
from config import SECTORS, SECTOR_ROTATION
from datetime import datetime
from core.utils import timestamp_str, normalize_ohlc
from core.fetcher import fetch_ohlc
from core.db import save, load
from core.notifier import send_message
from core.utils import timestamp_str

logger = logging.getLogger(__name__)

# =========================
# Config
# =========================


PREV_STATE_FILE = "sector_prev_state.json"  # lives in data/

# =========================
# Run mode
# =========================
def get_run_mode() -> str:
    return "WEEKLY" if datetime.today().weekday() == 4 else "DAILY"

# =========================
# Fetch (your original logic)
# =========================
def fetch_data(tickers: dict, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    symbols = list(tickers.values())
    names   = list(tickers.keys())
    raw     = fetch_ohlc(symbols, period=period, interval=interval)
    if raw.empty:
        raise ValueError("No sector data fetched.")

    data = {}
    for name, symbol in zip(names, symbols):
        try:
            close = normalize_ohlc(raw[symbol])["Close"]
            close.name = name
            data[name] = close
        except Exception as e:
            logger.warning(f"Skipped {name}: {e}")

    if not data:
        raise ValueError("No valid sector data after processing.")

    df_final = pd.concat(data.values(), axis=1)
    df_final.columns = list(data.keys())
    return df_final.dropna()

# =========================
# Analyze (your original logic)
# =========================
def analyze_sector_rotation(df: pd.DataFrame, run_mode: str) -> tuple[pd.DataFrame, str]:
    if run_mode == "WEEKLY":
        rs_lb, mom_lb, title_suffix = 60, 20, "(3M / 1M)"
    else:
        rs_lb, mom_lb, title_suffix = 20, 5,  "(1M / 1W)"

    results = []
    benchmark = df["NIFTY 50"]

    for sector in df.columns:
        if sector == "NIFTY 50":
            continue
        ratio = df[sector] / benchmark
        if len(ratio) <= max(rs_lb, mom_lb, 3):
            continue

        rs        = ((ratio.iloc[-1] / ratio.iloc[-rs_lb - 1]) - 1) * 100
        mom       = ((ratio.iloc[-1] / ratio.iloc[-mom_lb - 1]) - 1) * 100
        short_mom = ((ratio.iloc[-1] / ratio.iloc[-3]) - 1) * 100

        if rs < 0 and mom > 0.3 and short_mom > 0.2:
            signal = "Emerging ⚡"
        elif rs > 2 and mom > 1:
            signal = "Strong Uptrend 🚀"
        elif rs > 0 and mom > 0:
            signal = "Moderate Uptrend 📈"
        elif rs < -2 and mom < -1:
            signal = "Strong Downtrend 🔻"
        else:
            signal = "Neutral ⚖️"

        results.append({
            "Sector": sector,
            "RS":     round(rs, 2),
            "MOM":    round(mom, 2),
            "Signal": signal,
            "Score":  rs + mom,
        })

    df_out = (pd.DataFrame(results)
              .sort_values("Score", ascending=False)
              .reset_index(drop=True))
    return df_out, title_suffix

# =========================
# State persistence — now uses data/ folder so it survives Actions runs
# =========================
def load_prev_state() -> dict:
    return load(PREV_STATE_FILE, default={})

def save_prev_state(df_result: pd.DataFrame, prev_state: dict) -> None:
    new_state = {}
    for idx, row in df_result.iterrows():
        rank   = idx + 1
        sector = row["Sector"]
        old_ranks = prev_state.get(sector, {}).get("ranks", [])
        new_state[sector] = {"ranks": (old_ranks + [rank])[-3:]}
    save(PREV_STATE_FILE, new_state)

# =========================
# Format Telegram message (your original logic, HTML parse_mode)
# =========================
def format_sector_message(df_result: pd.DataFrame, title_suffix: str,
                           prev_state: dict | None = None) -> str:
    message      = f"📊 <b>NIFTY Sector Rotation {title_suffix}</b>\n\n"
    biggest_up   = None
    biggest_down = None
    max_improve  = 0
    max_drop     = 0

    for idx, row in df_result.iterrows():
        rank       = idx + 1
        arrow      = ""
        slope_icon = ""

        if prev_state and row["Sector"] in prev_state:
            prev_ranks = prev_state[row["Sector"]].get("ranks", [])
            if prev_ranks:
                prev_rank = prev_ranks[-1]
                if rank < prev_rank:
                    arrow = " ▲"
                elif rank > prev_rank:
                    arrow = " ▼"
                diff = prev_rank - rank
                if diff > max_improve:
                    max_improve = diff
                    biggest_up = row["Sector"]
                if diff < max_drop:
                    max_drop = diff
                    biggest_down = row["Sector"]
                if len(prev_ranks) >= 2:
                    r2 = prev_ranks[-2]
                    if rank < prev_rank < r2:
                        slope_icon = " 🔼"
                    elif rank > prev_rank > r2:
                        slope_icon = " 🔽"

        message += (
            f"<b>{rank}.</b> {row['Sector']} | "
            f"RS: {row['RS']:+.1f}% | "
            f"MOM: {row['MOM']:+.1f}% → "
            f"{row['Signal']}{arrow}{slope_icon}\n"
        )

    message += "\n"
    if biggest_up:
        message += f"<b>Biggest Climber:</b> {biggest_up}\n"
    if biggest_down:
        message += f"<b>Biggest Drop:</b> {biggest_down}\n"

    leaders  = ", ".join(df_result.head(2)["Sector"])
    laggards = ", ".join(df_result.tail(2)["Sector"])
    message += f"\n<b>Leading:</b>  {leaders}"
    message += f"\n<b>Laggards:</b> {laggards}"
    return message

# =========================
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        run_mode       = get_run_mode()
        period         = "1y" if run_mode == "WEEKLY" else "6mo"
        df             = fetch_data(SECTORS, period=period)
        df_result, title_suffix = analyze_sector_rotation(df, run_mode)
        prev_state     = load_prev_state()
        message        = format_sector_message(df_result, title_suffix, prev_state)

        # Build structured result for dashboard
        sectors_list = []
        for idx, row in df_result.iterrows():
            rank       = idx + 1
            prev_ranks = prev_state.get(row["Sector"], {}).get("ranks", [])
            prev_rank  = prev_ranks[-1] if prev_ranks else rank
            sectors_list.append({
                "rank":       rank,
                "sector":     row["Sector"],
                "rs":         row["RS"],
                "mom":        row["MOM"],
                "signal":     row["Signal"],
                "score":      round(row["Score"], 2),
                "rank_change": prev_rank - rank,   # positive = climbed
            })

        result = {
            "timestamp":    ts,
            "run_mode":     run_mode,
            "title_suffix": title_suffix,
            "sectors":      sectors_list,
            "leaders":      list(df_result.head(2)["Sector"]),
            "laggards":     list(df_result.tail(2)["Sector"]),
            "status":       "ok",
        }

        # 1. Save dashboard data
        save("sector_rotation.json", result)

        # 2. Update rank history (persisted via git commit in workflow)
        save_prev_state(df_result, prev_state)

        # 3. Send Telegram alert (HTML parse mode)
        send_message(message, parse_mode="HTML")

        print(f"Sector rotation done — mode: {run_mode}")
        return result

    except Exception as e:
        logger.error(f"sector_rotation run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("sector_rotation.json", error_result)
        send_message(f"❌ <b>Sector Rotation failed</b>\n<code>{e}</code>",
                     parse_mode="HTML")
        return error_result

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()