import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.load_data import get
from core.utils import fmt_pct

st.set_page_config(page_title="Gold/Silver Ratio", page_icon="🥇", layout="wide")
st.title("🥇 Gold / Silver Ratio Tracker")

data = get("Gold Silver Ratio")
if not data or data.get("status") == "error":
    st.error(data.get("error", "No data yet.") if data else "No data yet. Trigger the workflow to run.")
    st.stop()

st.caption(f"Last updated: {data.get('timestamp', '—')}")

# ── Price & GSR cards ─────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("GoldBeES",   f"₹{data['gold_price']:.2f}")
c2.metric("SilverBeES", f"₹{data['silver_price']:.2f}")
c3.metric("GSR",        f"{data['gsr']:.4f}",
          delta=f"{data['gsr_dev_pct']:+.2f}% vs mean")
c4.metric("Signal strength", data["strength"])

st.divider()

# ── Signal banner ─────────────────────────────────────────
signal = data.get("signal", "")
if "Silver" in signal:
    st.info(f"⚡ {signal}")
elif "Gold" in signal:
    st.info(f"⚡ {signal}")
else:
    st.success(f"⚡ {signal}")

# ── GSR stats ─────────────────────────────────────────────
col1, col2 = st.columns(2)
# with col1:
    # st.subheader("GSR statistics")
    # st.dataframe(pd.DataFrame({
    #     "Metric": ["Current GSR", "6M Mean", "Std Dev", "6M Min", "6M Max", "Deviation from mean"],
    #     "Value":  [
    #         f"{data['gsr']:.4f}",
    #         f"{data['gsr_mean']:.4f}",
    #         f"{data['gsr_std']:.4f}",
    #         f"{data['gsr_min']:.4f}",
    #         f"{data['gsr_max']:.4f}",
    #         f"{data['gsr_dev_pct']:+.2f}%",
    #     ]
    # }), hide_index=True, width="stretch")

with col1:
    st.subheader("Trends & volatility")
    st.dataframe(pd.DataFrame({
        "":           ["Gold", "Silver"],
        "Trend":      [data["gold_trend"],  data["silver_trend"]],
        "Ann. Vol":   [fmt_pct(data["gold_vol"]), fmt_pct(data["silver_vol"])],
    }), hide_index=True, width="stretch")

# st.divider()

# ── Returns table ─────────────────────────────────────────
with col2:
    st.subheader("Returns comparison")
    gr = data.get("gold_returns",   {})
    sr = data.get("silver_returns", {})
    periods = ["1D", "1W", "1M", "1Y"]
    returns_df = pd.DataFrame({
        "Period":  periods,
        "Gold":    [fmt_pct(gr.get(p), plus=True) for p in periods],
        "Silver":  [fmt_pct(sr.get(p), plus=True) for p in periods],
    })
    st.dataframe(returns_df, hide_index=True, width="stretch")

st.divider()

# ── Sentiment ─────────────────────────────────────────────
col3, col4 = st.columns(2)
col3.metric("Market sentiment",    data.get("sentiment", "—"))
col4.metric("Better performer (1D)", data.get("better_performer", "—"))