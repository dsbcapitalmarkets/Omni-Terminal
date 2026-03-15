import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.load_data import get

st.set_page_config(page_title="Smart Money Flow", page_icon="💰", layout="wide")
st.title("💰 Smart Money Flow Tracker")

data = get("Smart Money Flow")

if not data or data.get("status") == "error":
    st.error(data.get("error", "No data yet.") if data else "No data yet. Trigger the workflow to run.")
    st.stop()

st.caption(f"Last updated: {data.get('timestamp', '—')}")

latest = data.get("latest", {})

# ── Signal banner ─────────────────────────────────────────
signal = latest.get("signal", "")
if "Bullish" in signal:
    st.success(f"📡 {signal}")
elif "Bearish" in signal:
    st.error(f"📡 {signal}")
else:
    st.warning(f"📡 {signal}")

# ── Today's metrics ───────────────────────────────────────
st.subheader(f"Today — {latest.get('date', '—')}")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("FII Net",  f"₹{latest.get('fii_net', '—')} Cr")
    st.caption(f"Buy ₹{latest.get('fii_buy','—')} Cr · Sell ₹{latest.get('fii_sell','—')} Cr")
with c2:
    st.metric("DII Net",  f"₹{latest.get('dii_net', '—')} Cr")
    st.caption(f"Buy ₹{latest.get('dii_buy','—')} Cr · Sell ₹{latest.get('dii_sell','—')} Cr")
with c3:
    try:
        combined = latest.get("fii_net", 0) + latest.get("dii_net", 0)
        st.metric("Combined Net", f"₹{combined:,.0f} Cr")
    except Exception:
        st.metric("Combined Net", "—")

st.divider()

# ── Historical trend chart ────────────────────────────────
history = data.get("history", [])
if history:
    st.subheader("FII / DII net flow — last 30 days")
    df = pd.DataFrame(history).tail(30)
    try:
        df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").set_index("date")
        st.line_chart(df[["fii_net", "dii_net"]], width="stretch")
    except Exception as e:
        st.warning(f"Could not render chart: {e}")

    st.divider()

    # ── History table ─────────────────────────────────────
    st.subheader("Daily history")
    display_df = pd.DataFrame(history).tail(30).iloc[::-1].reset_index(drop=True)
    st.dataframe(display_df, width="stretch", hide_index=True)