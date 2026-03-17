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
if "Bullish" in regime:      st.success(f"🧭 {regime}")
elif "Bearish" in regime:    st.error(f"🧭 {regime}")
elif "Transition" in regime: st.warning(f"🧭 {regime}")
else:                         st.info(f"🧭 {regime}")

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
c5.metric("🚀 New Highs",    data.get("new_highs",    "—"))
c6.metric("💀 New Lows",     data.get("new_lows",     "—"))
c7.metric("📈 NH-NL Spread", data.get("nh_nl_spread", "—"))

st.divider()

# ── DMA participation (today) ─────────────────────────────
st.subheader("DMA participation")
c8, c9 = st.columns(2)
c8.metric(
    "Above 50 DMA",
    f"{data.get('num_above_50', '—')} stocks",
    delta=f"{data.get('pct_above_50', '—')}%",
)
c9.metric(
    "Above 200 DMA",
    f"{data.get('num_above_200', '—')} stocks",
    delta=f"{data.get('pct_above_200', '—')}%",
)

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

st.divider()

# ── Historical DMA charts ─────────────────────────────────
history = data.get("history", [])

if history:
    st.subheader("📈 DMA participation history")

    df_hist = pd.DataFrame(history)

    # Parse dates — same format written by _append_history: "DD-Mon-YYYY"
    df_hist["date"] = pd.to_datetime(df_hist["date"], format="%d-%b-%Y", errors="coerce")
    df_hist = (
        df_hist
        .dropna(subset=["date"])
        .sort_values("date")
        .set_index("date")
    )

    # ── Chart 1: No. of stocks above 50 DMA ──────────────
    st.markdown("**Stocks above 50 DMA**")
    if "num_above_50" in df_hist.columns:
        st.line_chart(
            df_hist[["num_above_50"]].rename(columns={"num_above_50": "# above 50 DMA"}),
            height=250,
        )
    else:
        st.info("No 50-DMA history yet.")

    st.markdown("")   # spacer

    # ── Chart 2: No. of stocks above 200 DMA ─────────────
    st.markdown("**Stocks above 200 DMA**")
    if "num_above_200" in df_hist.columns:
        st.line_chart(
            df_hist[["num_above_200"]].rename(columns={"num_above_200": "# above 200 DMA"}),
            height=250,
        )
    else:
        st.info("No 200-DMA history yet.")

    st.divider()

    # ── Full history table (optional, collapsed) ──────────
    with st.expander("📋 Full history table"):
        display_cols = [
            c for c in
            ["date", "num_above_50", "pct_above_50", "num_above_200", "pct_above_200",
             "advances", "declines", "ad_ratio", "nh_nl_spread", "regime"]
            if c in df_hist.reset_index().columns
        ]
        st.dataframe(
            df_hist.reset_index()[display_cols].iloc[::-1].reset_index(drop=True),
            hide_index=True,
            width="stretch",
        )

else:
    st.info("History will appear here after the module runs a few times.")