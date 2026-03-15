import logging
import requests
from datetime import datetime, timedelta
from config import EARNINGS
from core.db import save
from core.notifier import send_message
from core.utils import timestamp_str
from core.fetcher import fetch_nse

logger = logging.getLogger(__name__)

SCREENER_URL = EARNINGS["screener_url"]
DAYS_AHEAD   = EARNINGS["days_ahead"]
NSE_CALENDAR_URL = EARNINGS["nse_calendar_url"]

# =========================
# Fetch from NSE event calendar
# =========================
def fetch_earnings(days_ahead: int = DAYS_AHEAD) -> tuple[list[dict], list[dict]]:
    url = "https://www.nseindia.com/api/event-calendar"
    try:
        nse_data = fetch_nse(url)
    except Exception as e:
        logger.warning(f"NSE calendar fetch failed: {e}")
        return [], []

    today   = datetime.now().date()
    date_to = today + timedelta(days=DAYS_AHEAD)

    today_results    = []
    upcoming_results = []

    for event in nse_data:
        purpose = event.get("purpose", "").lower()
        if not any(k in purpose for k in ["result", "financial", "quarterly", "annual"]):
            continue
        try:
            event_date = datetime.strptime(
                event.get("date", ""), "%d-%b-%Y"
            ).date()
        except Exception:
            continue

        entry = {
            "symbol":  event.get("symbol",  "—"),
            "company": event.get("company", event.get("symbol", "—")),
            "date":    event_date.strftime("%d %b %Y"),
            "purpose": event.get("purpose", "—"),
            "series":  event.get("series",  "EQ"),
        }

        if event_date == today:
            today_results.append(entry)
        elif today < event_date <= date_to:
            upcoming_results.append(entry)

    today_results.sort(key=lambda x: x["date"])
    upcoming_results.sort(key=lambda x: x["date"])

    return today_results, upcoming_results

# =========================
# Format Telegram message
# =========================
def format_message(
    today_results: list[dict],
    upcoming_results: list[dict],
    timestamp: str,
) -> str:
    today_str = datetime.now().strftime("%d %b %Y")
    msg = f"📊 <b>Results &amp; Earnings Tracker</b>\n"
    msg += f"🕐 {timestamp}\n\n"

    # Today's results
    if today_results:
        msg += f"<b>🔔 Results today ({today_str}) — {len(today_results)} companies</b>\n"
        for r in today_results:
            msg += f"• <b>{r['symbol']}</b> — {r['company']}\n"
    else:
        msg += f"<b>🔔 No results announced today</b>\n"

    msg += "\n"

    # Upcoming — group by date
    if upcoming_results:
        msg += f"<b>📅 Upcoming (next 7 days) — {len(upcoming_results)} companies</b>\n"
        current_date = None
        for r in upcoming_results:
            if r["date"] != current_date:
                current_date = r["date"]
                msg += f"\n<i>{current_date}</i>\n"
            msg += f"• <b>{r['symbol']}</b> — {r['company']}\n"
    else:
        msg += "<b>📅 No upcoming results in next 7 days</b>\n"

    msg += f"\n🔗 <a href='{SCREENER_URL}'>View full calendar on Screener</a>"
    return msg

# =========================
# run() — called by GitHub Actions
# =========================
def run() -> dict:
    ts = timestamp_str()
    try:
        today_results, upcoming_results = fetch_earnings(DAYS_AHEAD)

        result = {
            "timestamp":        ts,
            "status":           "ok",
            "today_count":      len(today_results),
            "upcoming_count":   len(upcoming_results),
            "today_results":    today_results,
            "upcoming_results": upcoming_results,
            "screener_url":     SCREENER_URL,
        }

        # 1. Save to data/earnings.json
        save("earnings.json", result)

        # 2. Send Telegram alert
        message = format_message(today_results, upcoming_results, ts)
        send_message(message, parse_mode="HTML")

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