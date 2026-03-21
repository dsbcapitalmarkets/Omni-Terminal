import logging
from datetime import datetime, timedelta
from config import EARNINGS
from core.db import save
from core.notifier import send_message
from core.utils import timestamp_str, IST
from core.fetcher import fetch_nse

logger = logging.getLogger(__name__)

SCREENER_URL     = EARNINGS["screener_url"]
DAYS_AHEAD       = EARNINGS["days_ahead"]
NSE_CALENDAR_URL = EARNINGS["nse_calendar_url"]

# ── Purpose classification ───────────────────────────────────────────────────

# Exact-match allowlist (lowercased). Only these purpose strings are kept.
# "Board Meeting" variants are critical — NSE labels same-day result events
# as board meetings rather than "Quarterly Results".
RESULT_PURPOSES = {
    "quarterly results",
    "financial results",
    "half yearly results",
    "annual results",
    "unaudited financial results",
    "board meeting",
    "board meeting-finalisation of accounts",
}

# Human-readable labels and emoji for each purpose (used in UI + Telegram)
PURPOSE_META = {
    "quarterly results":                  ("📊 Quarterly Results",  "quarterly"),
    "financial results":                  ("📊 Financial Results",  "quarterly"),
    "half yearly results":                ("📊 Half Yearly Results","quarterly"),
    "annual results":                     ("📊 Annual Results",     "annual"),
    "unaudited financial results":        ("📊 Unaudited Results",  "quarterly"),
    "board meeting":                      ("🏛️ Board Meeting",       "board"),
    "board meeting-finalisation of accounts": ("🏛️ Board Meeting (Accounts)", "board"),
}

def _classify_purpose(raw_purpose: str) -> tuple[str, str]:
    """
    Returns (display_label, category) for a raw NSE purpose string.
    category is one of: 'quarterly', 'annual', 'board'
    """
    key = raw_purpose.lower().strip()
    return PURPOSE_META.get(key, (f"📋 {raw_purpose}", "board"))


# ── Fetch ────────────────────────────────────────────────────────────────────

def fetch_earnings(days_ahead: int = DAYS_AHEAD) -> tuple[list[dict], list[dict]]:
    url = "https://www.nseindia.com/api/event-calendar"
    try:
        nse_data = fetch_nse(url)
    except Exception as e:
        logger.warning(f"NSE calendar fetch failed: {e}")
        return [], []

    # Use IST-aware today — GitHub Actions runs in UTC; without this,
    # today's date can be off by up to 5.5 hours relative to IST
    today   = datetime.now(IST).date()
    date_to = today + timedelta(days=days_ahead)

    today_results    = []
    upcoming_results = []

    for event in nse_data:
        raw_purpose = event.get("purpose", "")
        purpose_key = raw_purpose.lower().strip()

        # Exact-match allowlist — drops dividends, AGM, splits, buybacks, etc.
        if purpose_key not in RESULT_PURPOSES:
            continue

        try:
            event_date = datetime.strptime(
                event.get("date", ""), "%d-%b-%Y"
            ).date()
        except Exception:
            continue

        display_label, category = _classify_purpose(raw_purpose)

        entry = {
            "symbol":        event.get("symbol",  "—"),
            "company":       event.get("company", event.get("symbol", "—")),
            "date":          event_date.strftime("%d %b %Y"),
            "purpose":       raw_purpose,
            "purpose_label": display_label,
            "category":      category,   # 'quarterly' | 'annual' | 'board'
            "series":        event.get("series", "EQ"),
        }

        if event_date == today:
            today_results.append(entry)
        elif today < event_date <= date_to:
            upcoming_results.append(entry)

    today_results.sort(key=lambda x: x["symbol"])
    upcoming_results.sort(key=lambda x: (x["date"], x["symbol"]))

    return today_results, upcoming_results


# ── Telegram message ─────────────────────────────────────────────────────────

def format_message(
    today_results: list[dict],
    upcoming_results: list[dict],
    timestamp: str,
) -> str:
    today_str = datetime.now(IST).strftime("%d %b %Y")
    msg = f"📊 <b>Results &amp; Earnings Tracker</b>\n🕐 {timestamp}\n\n"

    # Today — group by category
    if today_results:
        msg += f"<b>🔔 Today ({today_str}) — {len(today_results)} events</b>\n"
        boards     = [r for r in today_results if r["category"] == "board"]
        financials = [r for r in today_results if r["category"] != "board"]

        if financials:
            msg += "\n<i>Financial Results</i>\n"
            for r in financials:
                msg += f"• <b>{r['symbol']}</b> — {r['company']}\n"
        if boards:
            msg += "\n<i>Board Meetings</i>\n"
            for r in boards:
                msg += f"• <b>{r['symbol']}</b> — {r['company']}\n"
    else:
        msg += f"<b>🔔 No result events today</b>\n"

    msg += "\n"

    # Upcoming — group by date
    if upcoming_results:
        msg += f"<b>📅 Upcoming (next {DAYS_AHEAD} days) — {len(upcoming_results)} events</b>\n"
        current_date = None
        for r in upcoming_results:
            if r["date"] != current_date:
                current_date = r["date"]
                msg += f"\n<i>{current_date}</i>\n"
            msg += f"• <b>{r['symbol']}</b> {r['purpose_label']}\n"
    else:
        msg += f"<b>📅 No upcoming events in next {DAYS_AHEAD} days</b>\n"

    msg += f"\n🔗 <a href='{SCREENER_URL}'>Full calendar on Screener</a>"
    return msg


# ── run() ─────────────────────────────────────────────────────────────────────

def run() -> dict:
    ts = timestamp_str()
    try:
        today_results, upcoming_results = fetch_earnings(DAYS_AHEAD)

        # Summary counts split by category — useful for the dashboard
        def _counts(lst):
            return {
                "quarterly": sum(1 for r in lst if r["category"] == "quarterly"),
                "annual":    sum(1 for r in lst if r["category"] == "annual"),
                "board":     sum(1 for r in lst if r["category"] == "board"),
            }

        result = {
            "timestamp":        ts,
            "status":           "ok",
            "today_count":      len(today_results),
            "upcoming_count":   len(upcoming_results),
            "today_counts":     _counts(today_results),
            "upcoming_counts":  _counts(upcoming_results),
            "today_results":    today_results,
            "upcoming_results": upcoming_results,
            "screener_url":     SCREENER_URL,
        }

        save("earnings.json", result)
        send_message(format_message(today_results, upcoming_results, ts), parse_mode="HTML")

        print(f"Earnings tracker done — today: {len(today_results)}, "
              f"upcoming: {len(upcoming_results)}")
        return result

    except Exception as e:
        logger.error(f"earnings_tracker run() failed: {e}")
        error_result = {"status": "error", "error": str(e), "timestamp": ts}
        save("earnings.json", error_result)
        send_message(f"❌ <b>Earnings Tracker failed</b>\n<code>{e}</code>",
                     parse_mode="HTML")
        return error_result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()