# =============================================================
# config.py — central config for all modules + dashboard
# No secrets here. All sensitive values go in GitHub Secrets.
# =============================================================

# =========================
# Watchlist (used by screener as override — leave empty to use
# full NIFTY TOTAL MARKET universe from NSE API)
# =========================
WATCHLIST: list[str] = []   # e.g. ["RELIANCE", "TCS", "INFY"]

# =========================
# Screener filter thresholds
# =========================
SCREENER = {
    "min_data_days":   200,    # minimum trading days required
    "volume_lookback": 20,     # days for avg volume calculation
    "score_factors": {
        "momentum": True, 
        "trend": True, 
        "rsi": False, 
        "volume": True
    },
    "score_weights": {
        "momentum": 0.2,
        "trend":    0.3,
        "rsi":      0.1,
        "volume":   0.4,
    },
}

# =========================
# Gold / Silver ratio
# =========================
GOLD_SILVER = {
    "gold_ticker":   "GOLDBEES.NS",
    "silver_ticker": "SILVERBEES.NS",
    "period":        "6mo",
    "strong_signal_threshold":   3.0,   # % deviation for Strong
    "moderate_signal_threshold": 1.0,   # % deviation for Moderate
}

# =========================
# Sector rotation
# =========================
SECTORS: dict[str, str] = {
    "NIFTY 50": "^NSEI",
    "BANK":     "^NSEBANK",
    "IT":       "^CNXIT",
    "AUTO":     "^CNXAUTO",
    "FMCG":     "^CNXFMCG",
    "PHARMA":   "^CNXPHARMA",
    "METAL":    "^CNXMETAL",
    "ENERGY":   "^CNXENERGY",
    "REALTY":   "^CNXREALTY",
    "MEDIA":    "^CNXMEDIA",
}

SECTOR_ROTATION = {
    "daily_rs_lookback":    20,
    "daily_mom_lookback":   5,
    "weekly_rs_lookback":   60,
    "weekly_mom_lookback":  20,
    # Signal thresholds
    "strong_up_rs":   2.0,
    "strong_up_mom":  1.0,
    "strong_dn_rs":  -2.0,
    "strong_dn_mom": -1.0,
    "emerging_mom":   0.3,
    "emerging_short": 0.2,
}

# =========================
# Smart money flow
# =========================
SMART_MONEY = {
    "google_sheet_name": "Smart_Money_Flow_Tracker",
    "max_history_days":  60,
}

# =========================
# Market breadth
# =========================
MARKET_BREADTH = {
    "google_sheet_name": "Market_Breadth_Tracker",
    "worksheet_name":    "Sheet1",
    "nh_nl_tolerance":   1.0,   # % tolerance for 52W high/low
    "regime_thresholds": {
        "strong_bullish_pct200": 65,
        "bearish_pct200":        35,
        "transition_low":        40,
        "transition_high":       60,
    },
}

# =========================
# Earnings tracker
# =========================
EARNINGS = {
    "days_ahead":    7,     # how many days forward to fetch
    "screener_url":  "https://www.screener.in/upcoming-results/",
    "nse_calendar_url": "https://www.nseindia.com/api/event-calendar",
}

# =========================
# Portfolio reviewer
# =========================
PORTFOLIO = {
    "google_sheet_name": "My_Holdings-Portfolio_Reviewer",
    "worksheet_name":    "Sheet1",
    "nifty_ticker":      "^NSEI",
    "data_period":       "6mo",
    "supertrend_period":     10,
    "supertrend_multiplier":  3,
    "trailing_sl_pct":    0.95,   # 5% trailing stop
    "rs_lookback":        30,
}

# =========================
# Telegram alert schedules (IST) — for Home.py display only
# Actual scheduling is in .github/workflows/*.yml
# =========================
MODULE_SCHEDULES: dict[str, str] = {
    "Stock Screener":    "4:00 PM IST",
    "Gold Silver Ratio": "4:00 PM IST",
    "Market Breadth":    "3:45 PM IST",
    "Portfolio Review":  "3:45 PM IST",
    "Earnings Tracker":  "4:30 PM IST",
    "Sector Rotation":   "5:30 PM IST",
    "Smart Money Flow":  "7:30 PM IST",
}

# =========================
# Data file names — single source of truth
# All modules and pages reference these constants
# =========================
DATA_FILES: dict[str, str] = {
    "Stock Screener":    "screener.json",
    "Gold Silver Ratio": "gold_silver.json",
    "Sector Rotation":   "sector_rotation.json",
    "Smart Money Flow":  "smart_money.json",
    "Market Breadth":    "breadth.json",
    "Earnings Tracker":  "earnings.json",
    "Portfolio Review":  "portfolio_review.json",
}