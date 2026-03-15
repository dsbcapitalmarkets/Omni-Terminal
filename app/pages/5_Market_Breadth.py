import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.load_data import get

st.set_page_config(page_title="Market Breadth", page_icon="📊", layout="wide")
st.title("📊 Market Breadth Tracker")

data = get("Market Breadth")
if not data or data.get("status") == "error":
    st.error(data.get("error", "No data yet.") if data else "No data yet. Trigger the workflow to run.")
    st.stop()

st.caption(f"Last updated: {data.get('timestamp', '—')}")

# ── Regime banner ─────────────────────────────────────────
regime = data.get("regime", "")
if "Bullish" in regime:   st.success(f"🧭 {regime}")
elif "Bearish" in regime: st.error(f"🧭 {regime}")
elif "Transition" in regime: st.warning(f"🧭 {regime}")
else:                     st.info(f"🧭 {regime}")

st.divider()

# ── Advance / Decline ─────────────────────────────────────
st.subheader("Advance / Decline")
c1, c2, c3, c4 = st.columns(4)
c1.metric("🔼 Advances",  data.get("advances",  "—"))
c2.metric("🔽 Declines",  data.get("declines",  "—"))
c3.metric("⚖️ Unchanged", data.get("unchanged", "—"))
c4.metric("A/D Ratio",    data.get("ad_ratio",  "—"))

st.divider()

# ── 52-Week Highs / Lows ──────────────────────────────────
st.subheader("52-Week Highs / Lows")
c5, c6, c7 = st.columns(3)
c5.metric("🚀 New Highs",     data.get("new_highs",    "—"))
c6.metric("💀 New Lows",      data.get("new_lows",     "—"))
c7.metric("📈 NH-NL Spread",  data.get("nh_nl_spread", "—"))

st.divider()

# ── DMA participation ─────────────────────────────────────
st.subheader("DMA participation")
c8, c9 = st.columns(2)
c8.metric("Above 50 DMA",
    f"{data.get('num_above_50','—')} stocks",
    delta=f"{data.get('pct_above_50','—')}%")
c9.metric("Above 200 DMA",
    f"{data.get('num_above_200','—')} stocks",
    delta=f"{data.get('pct_above_200','—')}%")

# ── DMA gauge bars ────────────────────────────────────────
st.divider()
st.subheader("Participation gauge")
pct_50  = data.get("pct_above_50",  0)
pct_200 = data.get("pct_above_200", 0)

col1, col2 = st.columns(2)
with col1:
    st.caption("% above 50 DMA")
    st.progress(int(pct_50))
    st.caption(f"{pct_50}%")
with col2:
    st.caption("% above 200 DMA")
    st.progress(int(pct_200))
    st.caption(f"{pct_200}%")