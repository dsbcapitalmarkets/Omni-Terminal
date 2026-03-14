import streamlit as st
import pandas as pd
from core.db import load, last_updated
from config import MODULE_SCHEDULES, DATA_FILES

st.set_page_config(
    page_title="Quant Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 Quant Trading Dashboard")
st.caption("All modules run automatically via GitHub Actions. Data refreshes EOD.")

st.divider()

# ── Module status cards ───────────────────────────────────
st.subheader("Module status")

cols = st.columns(4)
module_items = list(DATA_FILES.items())

for i, (name, filename) in enumerate(module_items):
    data        = load(filename)
    updated     = last_updated(filename)
    schedule    = MODULE_SCHEDULES.get(name, "—")

    with cols[i % 4]:
        if data is None:
            st.error(f"**{name}**\n\nNo data yet")
        elif data.get("status") == "error":
            st.error(
                f"**{name}**\n\n"
                f"❌ Last run failed\n\n"
                f"`{data.get('error','unknown')[:60]}`"
            )
        else:
            st.success(
                f"**{name}**\n\n"
                f"✅ OK — {data.get('timestamp', updated or '—')}"
            )
        st.caption(f"🕐 Runs at {schedule}")

st.divider()

# ── Market snapshot ───────────────────────────────────────
st.subheader("Today's snapshot")

snap_cols = st.columns(3)

# Breadth
with snap_cols[0]:
    breadth = load("breadth.json")
    st.markdown("**📊 Market Breadth**")
    if breadth and breadth.get("status") == "ok":
        st.metric("Regime", breadth.get("regime", "—"))
        c1, c2 = st.columns(2)
        c1.metric("Advances", breadth.get("advances", "—"))
        c2.metric("Declines", breadth.get("declines", "—"))
    else:
        st.info("No data yet.")

# Sector rotation
with snap_cols[1]:
    sector = load("sector_rotation.json")
    st.markdown("**🔄 Sector Rotation**")
    if sector and sector.get("status") == "ok":
        leaders  = sector.get("leaders",  [])
        laggards = sector.get("laggards", [])
        st.metric("Mode", f"{sector.get('run_mode','—')} {sector.get('title_suffix','')}")
        st.success(f"🏆 {', '.join(leaders)}")
        st.error(f"🔻 {', '.join(laggards)}")
    else:
        st.info("No data yet.")

# Smart money
with snap_cols[2]:
    sm = load("smart_money.json")
    st.markdown("**💰 Smart Money**")
    if sm and sm.get("status") == "ok":
        latest = sm.get("latest", {})
        st.metric("Signal", latest.get("signal", "—"))
        c1, c2 = st.columns(2)
        c1.metric("FII Net", f"₹{latest.get('fii_net','—')} Cr")
        c2.metric("DII Net", f"₹{latest.get('dii_net','—')} Cr")
    else:
        st.info("No data yet.")

st.divider()

# ── Portfolio + Screener row ──────────────────────────────
row2 = st.columns(2)

with row2[0]:
    port = load("portfolio_review.json")
    st.markdown("**💼 Portfolio Review**")
    if port and port.get("status") == "ok":
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg P&L",  f"{port.get('avg_pnl', 0):.2f}%")
        c2.metric("🔴 EXIT",  port.get("exit_count", 0))
        c3.metric("🟢 HOLD",  port.get("hold_count", 0))
        holdings = port.get("holdings", [])
        action   = [h for h in holdings if h["signal"] in ("EXIT", "SELL")]
        if action:
            st.warning(f"⚠️ {len(action)} stock(s) need attention")
            for h in action[:3]:    # show max 3 on home
                st.caption(
                    f"{'🔴' if h['signal']=='EXIT' else '🟡'} "
                    f"{h['ticker']} — {h['signal']} | P&L {h['pnl_pct']:+.2f}%"
                )
    else:
        st.info("No data yet.")

with row2[1]:
    screener = load("screener.json")
    st.markdown("**📊 Stock Screener**")
    if screener and screener.get("status") == "ok":
        c1, c2 = st.columns(2)
        c1.metric("Universe",      screener.get("total_universe", "—"))
        c2.metric("Passed filter", screener.get("passed_count",   "—"))
        stocks = screener.get("stocks", [])[:5]  # top 5 on home
        if stocks:
            df = pd.DataFrame(stocks)[["symbol", "score"]]
            df.index = df.index + 1
            st.dataframe(df, use_container_width=True,
                         column_config={
                             "symbol": st.column_config.TextColumn("Symbol"),
                             "score":  st.column_config.NumberColumn("Score", format="%.3f"),
                         })
    else:
        st.info("No data yet.")

st.divider()

# ── Gold silver + Earnings row ────────────────────────────
row3 = st.columns(2)

with row3[0]:
    gs = load("gold_silver.json")
    st.markdown("**🥇 Gold / Silver Ratio**")
    if gs and gs.get("status") == "ok":
        c1, c2 = st.columns(2)
        c1.metric("GSR",    f"{gs.get('gsr', '—'):.4f}",
                  delta=f"{gs.get('gsr_dev_pct', 0):+.2f}% vs mean")
        c2.metric("Signal", gs.get("signal", "—"))
        st.caption(f"Strength: {gs.get('strength','—')} · {gs.get('sentiment','—')}")
    else:
        st.info("No data yet.")

with row3[1]:
    earn = load("earnings.json")
    st.markdown("**📅 Earnings Tracker**")
    if earn and earn.get("status") == "ok":
        c1, c2 = st.columns(2)
        c1.metric("Results today",     earn.get("today_count",    0))
        c2.metric("Upcoming (7 days)", earn.get("upcoming_count", 0))
        today_list = earn.get("today_results", [])[:3]
        if today_list:
            for r in today_list:
                st.caption(f"🔔 {r['symbol']} — {r['company']}")
    else:
        st.info("No data yet.")

st.divider()
st.caption("Built with Streamlit · Data via NSE API + yfinance · Compute via GitHub Actions · Free tier ₹0/month")