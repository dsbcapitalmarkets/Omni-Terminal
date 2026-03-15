import math
import logging
import math
import pandas as pd
from core.fetcher import fetch_ohlc
from core.utils import normalize_ohlc
from config import GOLD_SILVER
from core.db import save
from core.notifier import send_message
from core.utils import safe_scalar, fmt_pct, timestamp_str

logger = logging.getLogger(__name__)

GOLD_TICKER   = GOLD_SILVER["gold_ticker"]
SILVER_TICKER = GOLD_SILVER["silver_ticker"]
PERIOD        = GOLD_SILVER["period"]

def _safe(v) -> float | None:
    """Return None instead of NaN/inf so the output is valid JSON."""
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 2)
    except (TypeError, ValueError):
        return None

def calc_return(series: pd.Series, days: int) -> float:
    if series is None or len(series) <= days:
        return float("nan")
    try:
        past   = float(series.iloc[-(days + 1)])
        recent = float(series.iloc[-1])
        return (recent / past - 1) * 100.0
    except Exception:
        return float("nan")

def sma_trend(series: pd.Series, window: int = 20) -> str:
    if series is None or len(series) < window:
        return "N/A"
    sma  = series.rolling(window).mean().iloc[-1]
    last = series.iloc[-1]
    return "Bullish" if last > sma else "Bearish"

def annualized_vol(series: pd.Series) -> float:
    if series is None or len(series) < 2:
        return float("nan")
    daily_ret = series.pct_change().dropna()
    if len(daily_ret) < 2:
        return float("nan")
    return float(daily_ret.std() * math.sqrt(252) * 100.0)

# =========================
# Fetch
# =========================
def fetch_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    data = fetch_ohlc([GOLD_TICKER, SILVER_TICKER], period=PERIOD)
    if data.empty:
        raise ValueError("Failed to fetch GOLDBEES or SILVERBEES data.")
    gold   = normalize_ohlc(data[GOLD_TICKER])
    silver = normalize_ohlc(data[SILVER_TICKER])
    gold, silver = gold.align(silver, join="inner", axis=0)
    return gold, silver

# =========================
# Compute stats (your original logic, now in a function)
# =========================
def compute_stats(gold: pd.DataFrame, silver: pd.DataFrame) -> dict:
    gold_close   = safe_scalar(gold["Close"].iloc[-1])
    silver_close = safe_scalar(silver["Close"].iloc[-1])

    # Daily returns
    gold["Return"]   = gold["Close"].pct_change() * 100
    silver["Return"] = silver["Close"].pct_change() * 100
    gold_return_1d   = safe_scalar(gold["Return"].iloc[-1])
    silver_return_1d = safe_scalar(silver["Return"].iloc[-1])

    # Multi-period returns
    periods = {"1D": 1, "1W": 5, "1M": 21, "1Y": 252}
    gold_returns   = {k: calc_return(gold["Close"],   v) for k, v in periods.items()}
    silver_returns = {k: calc_return(silver["Close"], v) for k, v in periods.items()}

    # GSR statistics
    historical_gsr = (gold["Close"] / silver["Close"]).dropna()
    gsr      = gold_close / silver_close
    gsr_mean = safe_scalar(historical_gsr.mean())
    gsr_std  = safe_scalar(historical_gsr.std())
    gsr_dev_pct = ((gsr - gsr_mean) / gsr_mean) * 100.0
    gsr_max  = safe_scalar(historical_gsr.max())
    gsr_min  = safe_scalar(historical_gsr.min())

    # Trends & volatility
    gold_trend   = sma_trend(gold["Close"])
    silver_trend = sma_trend(silver["Close"])
    gold_vol     = annualized_vol(gold["Close"])
    silver_vol   = annualized_vol(silver["Close"])

    # Signal (your original logic)
    signal = "✋ Hold current positions"
    if (gsr > gsr_mean + gsr_std) and (silver_return_1d > gold_return_1d):
        signal = "📈 Consider shifting to Silver"
    elif (gsr < gsr_mean - gsr_std) and (gold_return_1d > silver_return_1d):
        signal = "📈 Consider shifting to Gold"

    # Strength
    abs_gap  = abs(gsr_dev_pct)
    strength = "Neutral"
    if abs_gap >= 3.0:
        strength = "Strong"
    elif abs_gap >= 1.0:
        strength = "Moderate"

    sentiment = "Risk-off (Gold favored)" if gsr_dev_pct >= 0 else "Risk-on (Silver favored)"
    better    = "Gold" if gold_return_1d > silver_return_1d else "Silver"

    return {
        "gold_price":    round(gold_close, 2),
        "silver_price":  round(silver_close, 2),
        "gsr":           round(gsr, 4),
        "gsr_mean":      round(gsr_mean, 4),
        "gsr_std":       round(gsr_std, 4),
        "gsr_dev_pct":   round(gsr_dev_pct, 2),
        "gsr_max":       round(gsr_max, 4),
        "gsr_min":       round(gsr_min, 4),
        "gold_trend":    gold_trend,
        "silver_trend":  silver_trend,
        "gold_vol":     _safe(gold_vol),
        "silver_vol":   _safe(silver_vol),
        "gold_returns":   {k: _safe(v) for k, v in gold_returns.items()},
        "silver_returns": {k: _safe(v) for k, v in silver_returns.items()},
        "signal":        signal,
        "strength":      strength,
        "sentiment":     sentiment,
        "better_performer": better,
    }

# =========================
# Format Telegram message (your original format, preserved exactly)
# =========================
def format_message(stats: dict, timestamp: str) -> str:
    g = stats["gold_returns"]
    s = stats["silver_returns"]
    return f"""📊 Weekly Gold/Silver Update ({timestamp}):

💰 Prices
GoldBeES:   ₹{stats['gold_price']:.2f}
SilverBeES: ₹{stats['silver_price']:.2f}

🔁 Ratio
Gold/Silver Ratio:      {stats['gsr']:.4f}
Mean Ratio:             {stats['gsr_mean']:.4f}
Std Dev:                {stats['gsr_std']:.4f}
Deviation from Mean:   {stats['gsr_dev_pct']:+.2f}%
6M Range (GSR):        Min {stats['gsr_min']:.4f} | Max {stats['gsr_max']:.4f}

📈 Returns
Gold   → 1D: {fmt_pct(g['1D'],True)} | 1W: {fmt_pct(g['1W'],True)} | 1M: {fmt_pct(g['1M'],True)} | 1Y: {fmt_pct(g['1Y'],True)}
Silver → 1D: {fmt_pct(s['1D'],True)} | 1W: {fmt_pct(s['1W'],True)} | 1M: {fmt_pct(s['1M'],True)} | 1Y: {fmt_pct(s['1Y'],True)}

📊 Trends & Volatility
Gold   Trend (20 SMA): {stats['gold_trend']}   | Vol: {fmt_pct(stats['gold_vol'])}
Silver Trend (20 SMA): {stats['silver_trend']} | Vol: {fmt_pct(stats['silver_vol'])}

🧭 Market Sentiment: {stats['sentiment']}
📍 Better Performer (1D): {stats['better_performer']}
⚡ Signal:   {stats['signal']}
🔋 Strength: {stats['strength']}"""

# =========================
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        gold, silver = fetch_data()
        stats        = compute_stats(gold, silver)

        result = {"timestamp": ts, "status": "ok", **stats}

        # 1. Save to data/gold_silver.json
        save("gold_silver.json", result)

        # 2. Send Telegram alert
        # send_message(format_message(stats, ts))

        print(f"Gold/Silver done — GSR: {stats['gsr']} | Signal: {stats['signal']}")
        return result

    except Exception as e:
        logger.error(f"gold_silver_ratio run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("gold_silver.json", error_result)
        send_message(f"❌ *Gold/Silver Tracker failed*\n`{e}`")
        return error_result

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()