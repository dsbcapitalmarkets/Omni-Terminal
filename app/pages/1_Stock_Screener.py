import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.load_data import get

st.set_page_config(page_title="Stock Screener", page_icon="📊", layout="wide")
st.title("📊 Stock Screener")

data = get("Stock Screener")

if not data or data.get("status") == "error":
    st.error(f"Last run failed: {data.get('error', 'No data yet.')}" if data else "No data yet. Trigger the workflow to run.")
    st.stop()

# ── Header metrics ────────────────────────────────────────
st.caption(f"Last updated: {data.get('timestamp', '—')}")
c1, c2 = st.columns(2)
c1.metric("Universe",      data.get("total_universe", "—"))
c2.metric("Passed filter", data.get("passed_count",   "—"))

st.divider()

# ── Ranked table ──────────────────────────────────────────
stocks = data.get("stocks", [])
if not stocks:
    st.info("No stocks passed the filter today.")
    st.stop()

df = pd.DataFrame(stocks)
df.index = df.index + 1  # 1-based ranking

# Clickable screener links
df["screener.in"] = df["symbol"].apply(
    lambda s: f"https://www.screener.in/company/{s}/"
)

st.dataframe(
    df[["symbol", "score", "screener.in"]],
    width="stretch",
    column_config={
        "symbol":      st.column_config.TextColumn("Symbol"),
        "score":       st.column_config.NumberColumn("Score", format="%.3f"),
        "screener.in": st.column_config.LinkColumn("Screener"),
    },
)

# ── Chart: score distribution ─────────────────────────────
st.subheader("Score distribution")
st.bar_chart(df.set_index("symbol")["score"])