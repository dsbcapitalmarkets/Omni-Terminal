import streamlit as st
import pandas as pd
from core.db import load

st.set_page_config(page_title="Portfolio Review", page_icon="💼", layout="wide")
st.title("💼 Auto Portfolio Reviewer")

data = load("portfolio_review.json")

if not data or data.get("status") == "error":
    st.error(data.get("error", "No data yet.") if data else "No data yet. Trigger the workflow to run.")
    st.stop()

st.caption(f"Last updated: {data.get('timestamp', '—')}")

# ── Portfolio summary metrics ─────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total holdings", data.get("total",      "—"))
c2.metric("Avg P&L",        f"{data.get('avg_pnl', 0):.2f}%")
c3.metric("🔴 EXIT",        data.get("exit_count", 0))
c4.metric("🟡 SELL",        data.get("sell_count", 0))
c5.metric("🟢 HOLD",        data.get("hold_count", 0))

st.divider()

holdings = data.get("holdings", [])
if not holdings:
    st.info("No holdings data available.")
    st.stop()

df = pd.DataFrame(holdings)

# ── Signal filter ─────────────────────────────────────────
signals    = ["ALL"] + sorted(df["signal"].unique().tolist())
selected   = st.selectbox("Filter by signal", signals)
if selected != "ALL":
    df = df[df["signal"] == selected]

# ── Holdings table ────────────────────────────────────────
def signal_color(val):
    if val == "EXIT":  return "background-color: #ff4b4b; color: white"
    if val == "SELL":  return "background-color: #ffa500; color: white"
    if val == "HOLD":  return "background-color: #21c354; color: white"
    return ""

st.dataframe(
    df[[
        "ticker", "signal", "current_price", "pnl_pct",
        "trend_state", "risk_status", "supertrend",
        "ema_20", "ema_50", "trailing_sl", "rs",
    ]].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
    column_config={
        "ticker":        st.column_config.TextColumn("Ticker"),
        "signal":        st.column_config.TextColumn("Signal"),
        "current_price": st.column_config.NumberColumn("Price ₹",     format="₹%.2f"),
        "pnl_pct":       st.column_config.NumberColumn("P&L %",       format="%+.2f%%"),
        "trend_state":   st.column_config.TextColumn("Trend"),
        "risk_status":   st.column_config.TextColumn("Risk"),
        "supertrend":    st.column_config.TextColumn("Supertrend"),
        "ema_20":        st.column_config.NumberColumn("EMA 20",       format="%.2f"),
        "ema_50":        st.column_config.NumberColumn("EMA 50",       format="%.2f"),
        "trailing_sl":   st.column_config.NumberColumn("Trailing SL",  format="%.2f"),
        "rs":            st.column_config.NumberColumn("RS vs NIFTY",  format="%+.2f%%"),
    },
)

st.divider()

# ── P&L distribution chart ────────────────────────────────
st.subheader("P&L distribution")
full_df = pd.DataFrame(data.get("holdings", []))
if not full_df.empty:
    st.bar_chart(
        full_df.set_index("ticker")["pnl_pct"],
        use_container_width=True,
    )

# ── EXIT / SELL watchlist ─────────────────────────────────
action_df = full_df[full_df["signal"].isin(["EXIT", "SELL"])]
if not action_df.empty:
    st.divider()
    st.subheader("⚠️ Action required")
    for _, row in action_df.iterrows():
        label = "🔴 EXIT" if row["signal"] == "EXIT" else "🟡 SELL"
        st.warning(
            f"{label} — **{row['ticker']}** | "
            f"Price ₹{row['current_price']:.2f} | "
            f"P&L {row['pnl_pct']:+.2f}% | "
            f"Risk: {row['risk_status']}"
        )