import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.load_data import get

st.set_page_config(page_title="Earnings Tracker", page_icon="📅", layout="wide")
st.title("📅 Results & Earnings Tracker")

data = get("Earnings Tracker")

if not data or data.get("status") == "error":
    st.error(data.get("error", "No data yet.") if data else "No data yet. Trigger the workflow to run.")
    st.stop()

st.caption(f"Last updated: {data.get('timestamp', '—')}")

# ── Summary bar ───────────────────────────────────────────────────────────────
today_count    = data.get("today_count", 0)
upcoming_count = data.get("upcoming_count", 0)
today_counts   = data.get("today_counts",   {"quarterly": 0, "annual": 0, "board": 0})
upcoming_counts= data.get("upcoming_counts",{"quarterly": 0, "annual": 0, "board": 0})

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Today — total",      today_count)
c2.metric("📊 Results today",   today_counts.get("quarterly", 0) + today_counts.get("annual", 0))
c3.metric("🏛️ Meetings today",  today_counts.get("board", 0))
c4.metric("Upcoming — total",   upcoming_count)
c5.metric("Next 7 days",        f"{upcoming_counts.get('quarterly',0) + upcoming_counts.get('annual',0)} results · {upcoming_counts.get('board',0)} meetings")

st.divider()

# ── Helpers ───────────────────────────────────────────────────────────────────

CATEGORY_ICON  = {"quarterly": "📊", "annual": "📋", "board": "🏛️"}
CATEGORY_LABEL = {"quarterly": "Results", "annual": "Annual Results", "board": "Board Meeting"}

# Purpose → category mapping (mirrors modules/earnings_tracker.py)
_PURPOSE_CATEGORY = {
    "quarterly results":                      "quarterly",
    "financial results":                      "quarterly",
    "half yearly results":                    "quarterly",
    "unaudited financial results":            "quarterly",
    "annual results":                         "annual",
    "board meeting":                          "board",
    "board meeting-finalisation of accounts": "board",
}

def _normalize(events: list[dict]) -> list[dict]:
    """
    Backfill 'category' and 'purpose_label' fields that are missing in old
    cached JSON (pre-fix). Safe to call on already-normalized entries too.
    """
    out = []
    for r in events:
        r = dict(r)  # don't mutate the original
        if "category" not in r:
            key = r.get("purpose", "").lower().strip()
            r["category"] = _PURPOSE_CATEGORY.get(key, "board")
        if "purpose_label" not in r:
            icon = CATEGORY_ICON.get(r["category"], "📋")
            r["purpose_label"] = f"{icon} {r.get('purpose', r['category'].title())}"
        out.append(r)
    return out

# ── Tab layout ────────────────────────────────────────────────────────────────
tab_today, tab_upcoming, tab_all = st.tabs([
    f"🔔 Today  ({today_count})",
    f"📅 Upcoming  ({upcoming_count})",
    "📋 Full table",
])

# ============================================================
# TAB 1 — TODAY
# ============================================================
with tab_today:
    today_list = _normalize(data.get("today_results", []))

    if not today_list:
        st.info("No result events scheduled for today.")
    else:
        # Split into results vs board meetings
        results_today = [r for r in today_list if r.get("category") != "board"]
        boards_today  = [r for r in today_list if r.get("category") == "board"]

        # ── Financial Results ─────────────────────────────
        if results_today:
            st.subheader(f"📊 Financial Results — {len(results_today)} companies")
            df = pd.DataFrame(results_today)
            df["screener"] = df["symbol"].apply(
                lambda s: f"https://www.screener.in/company/{s}/"
            )
            st.dataframe(
                df[["symbol", "company", "purpose_label", "series", "screener"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "symbol":        st.column_config.TextColumn("Symbol",  width="small"),
                    "company":       st.column_config.TextColumn("Company"),
                    "purpose_label": st.column_config.TextColumn("Type",    width="medium"),
                    "series":        st.column_config.TextColumn("Series",  width="small"),
                    "screener":      st.column_config.LinkColumn("Screener",width="small"),
                },
            )

        if results_today and boards_today:
            st.markdown("")  # spacer

        # ── Board Meetings ────────────────────────────────
        if boards_today:
            st.subheader(f"🏛️ Board Meetings — {len(boards_today)} companies")
            st.caption("These companies have board meetings today — results may be declared during/after the meeting.")
            df_b = pd.DataFrame(boards_today)
            df_b["screener"] = df_b["symbol"].apply(
                lambda s: f"https://www.screener.in/company/{s}/"
            )
            st.dataframe(
                df_b[["symbol", "company", "purpose_label", "series", "screener"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "symbol":        st.column_config.TextColumn("Symbol",  width="small"),
                    "company":       st.column_config.TextColumn("Company"),
                    "purpose_label": st.column_config.TextColumn("Meeting type", width="medium"),
                    "series":        st.column_config.TextColumn("Series",  width="small"),
                    "screener":      st.column_config.LinkColumn("Screener",width="small"),
                },
            )

# ============================================================
# TAB 2 — UPCOMING
# ============================================================
with tab_upcoming:
    upcoming = _normalize(data.get("upcoming_results", []))

    if not upcoming:
        st.info("No upcoming events in the next 7 days.")
    else:
        df_up = pd.DataFrame(upcoming)

        # ── Filter controls ───────────────────────────────
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            type_filter = st.selectbox(
                "Filter by type",
                ["All", "📊 Results only", "🏛️ Board Meetings only"],
                label_visibility="collapsed",
            )
        with col_f2:
            st.caption(f"Showing events from today through next {data.get('upcoming_count',0) and 7} days")

        if type_filter == "📊 Results only":
            df_up = df_up[df_up["category"] != "board"]
        elif type_filter == "🏛️ Board Meetings only":
            df_up = df_up[df_up["category"] == "board"]

        if df_up.empty:
            st.info("No events match the selected filter.")
        else:
            # Group by date — one expander per date
            for date_val in df_up["date"].unique():
                subset   = df_up[df_up["date"] == date_val].reset_index(drop=True)
                n_res    = len(subset[subset["category"] != "board"])
                n_board  = len(subset[subset["category"] == "board"])

                parts = []
                if n_res:   parts.append(f"{n_res} result{'s' if n_res>1 else ''}")
                if n_board: parts.append(f"{n_board} meeting{'s' if n_board>1 else ''}")
                label = f"📆 {date_val} — {', '.join(parts)}"

                with st.expander(label, expanded=True):
                    subset["screener"] = subset["symbol"].apply(
                        lambda s: f"https://www.screener.in/company/{s}/"
                    )
                    st.dataframe(
                        subset[["symbol", "company", "purpose_label", "series", "screener"]],
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "symbol":        st.column_config.TextColumn("Symbol",  width="small"),
                            "company":       st.column_config.TextColumn("Company"),
                            "purpose_label": st.column_config.TextColumn("Type",    width="medium"),
                            "series":        st.column_config.TextColumn("Series",  width="small"),
                            "screener":      st.column_config.LinkColumn("Screener",width="small"),
                        },
                    )

# ============================================================
# TAB 3 — FULL TABLE (all events, sortable)
# ============================================================
with tab_all:
    all_events = _normalize(data.get("today_results", []) + data.get("upcoming_results", []))

    if not all_events:
        st.info("No data available.")
    else:
        df_all = pd.DataFrame(all_events)
        df_all["screener"] = df_all["symbol"].apply(
            lambda s: f"https://www.screener.in/company/{s}/"
        )
        df_all["when"] = df_all.apply(
            lambda r: "Today" if r == data.get("today_results", [{}])[0].get("date", "")
            else r["date"], axis=1
        )
        # Simpler: just show the date column as-is
        st.dataframe(
            df_all[["date", "symbol", "company", "purpose_label", "series", "screener"]],
            hide_index=True,
            width="stretch",
            column_config={
                "date":          st.column_config.TextColumn("Date",    width="small"),
                "symbol":        st.column_config.TextColumn("Symbol",  width="small"),
                "company":       st.column_config.TextColumn("Company"),
                "purpose_label": st.column_config.TextColumn("Type",    width="medium"),
                "series":        st.column_config.TextColumn("Series",  width="small"),
                "screener":      st.column_config.LinkColumn("Screener",width="small"),
            },
        )
        st.caption(f"Total: {len(df_all)} events · {data.get('today_count',0)} today · {data.get('upcoming_count',0)} upcoming")

st.divider()
st.caption(f"📎 Full calendar: {data.get('screener_url', '')}")