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

st.caption(f"Last updated: {data.get('timestamp', '—')}")

# ── Universe metrics ──────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Universe",  data.get("total_universe", "—"))
c2.metric("NSE Stocks",      data.get("nse_universe",   "—"))
c3.metric("BSE Stocks",      data.get("bse_universe",   "—"))
c4.metric("Passed Filter",   data.get("passed_count",   "—"))

st.divider()

# ── Ranked table ──────────────────────────────────────────
stocks = data.get("stocks", [])
if not stocks:
    st.info("No stocks passed the filter today.")
    st.stop()

df = pd.DataFrame(stocks)
df.index = df.index + 1   # 1-based ranking

# Screener.in link for all — NSE uses symbol, BSE uses scrip code as slug
df["link"] = df["symbol"].apply(
    lambda s: f"https://www.screener.in/company/{s}/"
)

# Exchange filter
if "exchange" in df.columns:
    options  = ["All"] + sorted(df["exchange"].unique().tolist())
    selected = st.selectbox("Filter by exchange", options)
    if selected != "All":
        df = df[df["exchange"] == selected]

# Display columns
display_cols = ["symbol"]
col_config   = {
    "symbol":   st.column_config.TextColumn("Symbol"),
    "exchange": st.column_config.TextColumn("Exchange", width="small"),
    "score":    st.column_config.NumberColumn("Score", format="%.3f"),
    "link":     st.column_config.LinkColumn("Screener"),
}

if "exchange" in df.columns:
    display_cols.append("exchange")

display_cols += ["score", "link"]

st.dataframe(
    df[display_cols],
    width="stretch",
    hide_index=False,
    column_config=col_config,
)

# ── Score distribution chart ──────────────────────────────
st.subheader("Score distribution")
st.bar_chart(df.set_index("symbol")["score"])