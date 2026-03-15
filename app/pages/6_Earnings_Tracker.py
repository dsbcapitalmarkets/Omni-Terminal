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

# ── Summary metrics ───────────────────────────────────────
c1, c2 = st.columns(2)
c1.metric("Results today",      data.get("today_count",    0))
c2.metric("Upcoming (7 days)",  data.get("upcoming_count", 0))

st.divider()

# ── Today's results ───────────────────────────────────────
st.subheader("🔔 Results today")
today = data.get("today_results", [])
if today:
    df_today = pd.DataFrame(today)
    st.dataframe(
        df_today[["symbol", "company", "purpose"]],
        width="stretch",
        hide_index=True,
        column_config={
            "symbol":  st.column_config.TextColumn("Symbol"),
            "company": st.column_config.TextColumn("Company"),
            "purpose": st.column_config.TextColumn("Purpose"),
        },
    )
else:
    st.info("No results announced today.")

st.divider()

# ── Upcoming results ──────────────────────────────────────
st.subheader("📅 Upcoming — next 7 days")
upcoming = data.get("upcoming_results", [])
if upcoming:
    df_up = pd.DataFrame(upcoming)

    # Group by date — show as expanders
    for date_val in df_up["date"].unique():
        subset = df_up[df_up["date"] == date_val]
        with st.expander(f"📆 {date_val} — {len(subset)} companies", expanded=True):
            st.dataframe(
                subset[["symbol", "company", "purpose"]].reset_index(drop=True),
                width="stretch",
                hide_index=True,
                column_config={
                    "symbol":  st.column_config.TextColumn("Symbol"),
                    "company": st.column_config.TextColumn("Company"),
                    "purpose": st.column_config.TextColumn("Purpose"),
                },
            )
else:
    st.info("No upcoming results in the next 7 days.")

st.divider()
st.caption(f"📎 Full calendar: {data.get('screener_url', '')}")