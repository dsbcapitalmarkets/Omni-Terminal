import streamlit as st
import pandas as pd
from core.db import load, last_updated

st.set_page_config(page_title="Stock Screener", page_icon="📊", layout="wide")
st.title("📊 Stock Screener")

data = load("screener.json")

if not data or data.get("status") == "error":
    st.error(f"Last run failed: {data.get('error', 'No data yet.')}" if data else "No data yet. Trigger the workflow to run.")
    st.stop()

# ── Header metrics ────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Universe",      data.get("total_universe", "—"))
c2.metric("Passed filter", data.get("passed_count",   "—"))
c3.metric("Last updated",  data.get("timestamp",      "—"))

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
    use_container_width=True,
    column_config={
        "symbol":      st.column_config.TextColumn("Symbol"),
        "score":       st.column_config.NumberColumn("Score", format="%.3f"),
        "screener.in": st.column_config.LinkColumn("Screener"),
    },
)

# ── Chart: score distribution ─────────────────────────────
st.subheader("Score distribution")
st.bar_chart(df.set_index("symbol")["score"])