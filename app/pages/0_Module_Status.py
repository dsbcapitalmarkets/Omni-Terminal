import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.load_data import preload
from config import MODULE_SCHEDULES
from datetime import datetime, timedelta
import pytz

st.set_page_config(
    page_title="Module Status",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🖥️ Module Status")
st.caption("Live status of all 7 modules running on GitHub Actions.")

all_data = preload()

IST = pytz.timezone("Asia/Kolkata")

# =========================
# Helpers
# =========================
def parse_timestamp(ts_str: str) -> datetime | None:
    if not ts_str or ts_str == "—":
        return None
    formats = [
        "%d %b %Y, %I:%M %p IST",
        "%d %b %Y, %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts_str.replace(" IST", ""), fmt.replace(" IST", ""))
            return IST.localize(dt)
        except Exception:
            continue
    return None

def freshness_label(ts_str: str) -> tuple[str, str]:
    dt = parse_timestamp(ts_str)
    if dt is None:
        return "Unknown", "red"
    now   = datetime.now(IST)
    delta = now - dt
    hours = delta.total_seconds() / 3600
    if hours < 2:
        return f"{int(delta.total_seconds() / 60)} min ago", "green"
    elif hours < 24:
        return f"{int(hours)} hrs ago", "green"
    elif hours < 48:
        return "1 day ago", "orange"
    elif hours < 72:
        return "2 days ago", "orange"
    else:
        return f"{int(hours / 24)} days ago", "red"

def next_run_label(schedule: str) -> str:
    now = datetime.now(IST)
    try:
        time_str  = schedule.replace(" IST", "").strip()
        scheduled = datetime.strptime(time_str, "%I:%M %p")
        scheduled_today = IST.localize(
            now.replace(
                hour=scheduled.hour,
                minute=scheduled.minute,
                second=0,
                microsecond=0,
            )
        )
        if now > scheduled_today:
            next_day = now + timedelta(days=1)
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            return f"Tomorrow {schedule}"
        else:
            mins_until = int((scheduled_today - now).total_seconds() / 60)
            if mins_until < 60:
                return f"In {mins_until} min ({schedule})"
            else:
                return f"In {int(mins_until/60)}h {mins_until%60}m ({schedule})"
    except Exception:
        return schedule

# =========================
# Module definitions
# =========================
MODULES = [
    {
        "name":     "Stock Screener",
        "icon":     "📊",
        "desc":     "Scans NIFTY Total Market universe with EMA/SMA/volume filters",
        "schedule": MODULE_SCHEDULES.get("Stock Screener", "—"),
    },
    {
        "name":     "Gold Silver Ratio",
        "icon":     "🥇",
        "desc":     "Tracks GoldBeES vs SilverBeES ratio with signal generation",
        "schedule": MODULE_SCHEDULES.get("Gold Silver Ratio", "—"),
    },
    {
        "name":     "Sector Rotation",
        "icon":     "🔄",
        "desc":     "Relative strength and momentum across 10 NSE sector indices",
        "schedule": MODULE_SCHEDULES.get("Sector Rotation", "—"),
    },
    {
        "name":     "Smart Money Flow",
        "icon":     "💰",
        "desc":     "FII/DII daily net flow from NSE with trend chart",
        "schedule": MODULE_SCHEDULES.get("Smart Money Flow", "—"),
    },
    {
        "name":     "Market Breadth",
        "icon":     "📈",
        "desc":     "Advance/decline, 52W highs/lows, DMA participation",
        "schedule": MODULE_SCHEDULES.get("Market Breadth", "—"),
    },
    {
        "name":     "Earnings Tracker",
        "icon":     "📅",
        "desc":     "NSE board meeting and results calendar for next 7 days",
        "schedule": MODULE_SCHEDULES.get("Earnings Tracker", "—"),
    },
    {
        "name":     "Portfolio Review",
        "icon":     "💼",
        "desc":     "Auto-analyzes holdings with Supertrend + EMA signals",
        "schedule": MODULE_SCHEDULES.get("Portfolio Review", "—"),
    },
]

# =========================
# Summary bar
# =========================
total         = len(MODULES)
ok_count      = sum(1 for m in MODULES if all_data.get(m["name"], {}).get("status") == "ok")
err_count     = sum(1 for m in MODULES if all_data.get(m["name"], {}).get("status") == "error")
pending_count = total - ok_count - err_count

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Total modules", total)
sc2.metric("✅ Running",    ok_count)
sc3.metric("❌ Failed",     err_count)
sc4.metric("⏳ Pending",    pending_count)

st.divider()

# =========================
# Module cards — 2 per row
# =========================
for i in range(0, len(MODULES), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        if i + j >= len(MODULES):
            break
        mod  = MODULES[i + j]
        data = all_data.get(mod["name"])

        with col:
            if data is None:
                status      = "pending"
                status_icon = "⏳"
            elif data.get("status") == "error":
                status      = "error"
                status_icon = "❌"
            else:
                status      = "ok"
                status_icon = "✅"

            with st.container(border=True):

                # ── Header ────────────────────────────────
                h1, h2 = st.columns([3, 1])
                with h1:
                    st.markdown(f"### {mod['icon']} {mod['name']}")
                    st.caption(mod["desc"])
                with h2:
                    if status == "ok":
                        st.success(f"{status_icon} OK")
                    elif status == "error":
                        st.error(f"{status_icon} Failed")
                    else:
                        st.warning(f"{status_icon} Pending")

                st.divider()

                # ── Details ───────────────────────────────
                if status == "ok":
                    ts               = data.get("timestamp", "—")
                    fresh, colour    = freshness_label(ts)
                    next_run         = next_run_label(mod["schedule"])

                    d1, d2, d3 = st.columns(3)
                    with d1:
                        st.markdown("**Last run**")
                        st.caption(ts)
                    with d2:
                        st.markdown("**Data freshness**")
                        if colour == "green":
                            st.success(fresh)
                        elif colour == "orange":
                            st.warning(fresh)
                        else:
                            st.error(fresh)
                    with d3:
                        st.markdown("**Next run**")
                        st.caption(next_run)

                elif status == "error":
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown("**Last attempted**")
                        st.caption(data.get("timestamp", "—"))
                    with d2:
                        st.markdown("**Next run**")
                        st.caption(next_run_label(mod["schedule"]))
                    st.markdown("**Error details**")
                    st.error(data.get("error", "Unknown error"))
                    st.caption(
                        "💡 Check GitHub Actions logs — "
                        "Actions → your workflow → failed run"
                    )

                else:
                    st.markdown("**Next run**")
                    st.caption(next_run_label(mod["schedule"]))
                    st.info(
                        "⏳ No data yet — trigger the workflow manually "
                        "from GitHub Actions to populate this module."
                    )

    st.divider()

_, center_col, _ = st.columns([1, 2, 1])
with center_col:
    st.caption("© 2026 DSB Capital. All Rights Reserved.")