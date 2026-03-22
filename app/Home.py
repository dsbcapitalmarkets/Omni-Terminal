import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.load_data import preload
from config import DATA_FILES

# --- Health check endpoint ---
query_params = st.query_params

if "health" in query_params:
    st.write("OK")
    st.stop()

st.set_page_config(
    page_title="DSB Capital - Omni Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Title row with refresh button top right ───────────────
title_col, btn_col = st.columns([6, 1])
with title_col:
    st.title("📈 DSB Capital - Omni Terminal")
    st.caption("Data refreshes EOD.")
with btn_col:
    st.write("")
    if st.button("🔄", use_container_width=True):
        preload(force=True)
        st.rerun()

# Preload all data once
all_data = preload()

st.divider()

# =========================
# Helper
# =========================
def fmt_cr(val) -> str:
    try:
        v = float(val)
        if abs(v) >= 1000:
            return f"₹{v/1000:+.1f}K Cr"
        return f"₹{v:+.0f} Cr"
    except Exception:
        return f"₹{val} Cr"

# =========================
# Row 1 — Market Breadth · Smart Money
# =========================
st.subheader("🌍 Market Sentiment")
r1c1, r1c2 = st.columns(2)

# ── Market Breadth ────────────────────────────────────────
with r1c1:
    breadth = all_data.get("Market Breadth")
    st.markdown("#### 📊 Market Breadth")
    if breadth and breadth.get("status") == "ok":
        regime = breadth.get("regime", "—")
        if "Bullish"     in regime: st.success(regime)
        elif "Bearish"   in regime: st.error(regime)
        elif "Transition" in regime: st.warning(regime)
        else:                        st.info(regime)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Advances",  breadth.get("advances",  "—"))
        c2.metric("Declines",  breadth.get("declines",  "—"))
        c3.metric("A/D Ratio", breadth.get("ad_ratio",  "—"))
        c4.metric("Unchanged", breadth.get("unchanged", "—"))
        c5, c6, c7 = st.columns(3)
        c5.metric("52W High",     breadth.get("new_highs",    "—"))
        c6.metric("52W Low",      breadth.get("new_lows",     "—"))
        c7.metric("NH-NL Spread", breadth.get("nh_nl_spread", "—"))
        st.caption(
            f"Above 50 DMA: {breadth.get('pct_above_50','—')}% · "
            f"Above 200 DMA: {breadth.get('pct_above_200','—')}%"
        )
        st.caption(f"Last updated: {breadth.get('timestamp','—')}")
    else:
        st.info("No data yet.")

# ── Smart Money Flow ──────────────────────────────────────
with r1c2:
    sm = all_data.get("Smart Money Flow")
    st.markdown("#### 💰 Smart Money Flow")
    if sm and sm.get("status") == "ok":
        latest = sm.get("latest", {})
        signal = latest.get("signal", "—")
        if "Bullish" in signal:   st.success(signal)
        elif "Bearish" in signal: st.error(signal)
        else:                     st.warning(signal)
        c1, c2 = st.columns(2)
        c1.metric("FII Net", fmt_cr(latest.get("fii_net", 0)))
        c2.metric("DII Net", fmt_cr(latest.get("dii_net", 0)))
        st.caption(
            f"FII Buy: {fmt_cr(latest.get('fii_buy',0))} · "
            f"Sell: {fmt_cr(latest.get('fii_sell',0))}"
        )
        st.caption(
            f"DII Buy: {fmt_cr(latest.get('dii_buy',0))} · "
            f"Sell: {fmt_cr(latest.get('dii_sell',0))}"
        )
        # FII/DII history mini chart
        history = sm.get("history", [])
        if history:
            df_h = pd.DataFrame(history).tail(10)
            try:
                df_h = df_h.dropna(subset=["fii_net", "dii_net"])
                if not df_h.empty:
                    st.line_chart(
                        df_h[["fii_net", "dii_net"]].reset_index(drop=True),
                        height=150,
                    )
            except Exception:
                pass
        st.caption(f"Date: {latest.get('date','—')} · Updated: {sm.get('timestamp','—')}")
    else:
        st.info("No data yet.")

st.divider()

# =========================
# Row 2 — Sector Rotation · Stock Screener
# =========================
st.subheader("🔍 Stock Selection")
r2c1, r2c2 = st.columns(2)

# ── Sector Rotation ───────────────────────────────────────
with r2c1:
    sector = all_data.get("Sector Rotation")
    st.markdown("#### 🔄 Sector Rotation")
    if sector and sector.get("status") == "ok":
        st.caption(
            f"Mode: {sector.get('run_mode','—')} {sector.get('title_suffix','')}"
        )
        st.success(f"🏆 Leading: {', '.join(sector.get('leaders', []))}")
        st.error(f"🔻 Lagging: {', '.join(sector.get('laggards', []))}")
        st.markdown("**All sectors**")
        for s in sector.get("sectors", []):
            change = s.get("rank_change", 0)
            arrow  = (f"▲{change}" if change > 0
                      else f"▼{abs(change)}" if change < 0 else "—")
            st.caption(
                f"{s['rank']}. **{s['sector']}** — {s['signal']} "
                f"| RS: {s['rs']:+.1f}% | MOM: {s['mom']:+.1f}% | {arrow}"
            )
        st.caption(f"Last updated: {sector.get('timestamp','—')}")
    else:
        st.info("No data yet.")

# ── Stock Screener ────────────────────────────────────────
with r2c2:
    screener = all_data.get("Stock Screener")
    st.markdown("#### 📊 Stock Screener")
    if screener and screener.get("status") == "ok":
        c1, c2, c3 = st.columns(3)
        c1.metric("NSE",           screener.get("nse_universe",   "—"))
        c2.metric("BSE",           screener.get("bse_universe",   "—"))
        c3.metric("Passed filter", screener.get("passed_count",   "—"))
        stocks = screener.get("stocks", [])
        if stocks:
            df = pd.DataFrame(stocks)[["symbol", "score"]]
            df.index = df.index + 1
            st.dataframe(
                df,
                width="stretch",
                hide_index=False,
                column_config={
                    "symbol": st.column_config.TextColumn("Symbol"),
                    "score":  st.column_config.NumberColumn("Score", format="%.3f"),
                }
            )
        else:
            st.info("No stocks passed filter today.")
        st.caption(f"Last updated: {screener.get('timestamp','—')}")
    else:
        st.info("No data yet.")

st.divider()

# =========================
# Row 3 — Portfolio Review · Gold Silver
# =========================
st.subheader("💼 Portfolio & Assets")
r3c1, r3c2 = st.columns(2)

# ── Portfolio Review ──────────────────────────────────────
with r3c1:
    port = all_data.get("Portfolio Review")
    st.markdown("#### 💼 Portfolio Review")
    if port and port.get("status") == "ok":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Holdings", port.get("total",      "—"))
        c2.metric("Avg P&L",  f"{port.get('avg_pnl', 0):.2f}%")
        c3.metric("🔴 EXIT",  port.get("exit_count", 0))
        c4.metric("🟢 HOLD",  port.get("hold_count", 0))
        action = [
            h for h in port.get("holdings", [])
            if h["signal"] in ("EXIT", "SELL")
        ]
        if action:
            st.warning(f"⚠️ {len(action)} stock(s) need attention")
            for h in action[:5]:
                col1, col2, col3, col4 = st.columns(4)
                col1.markdown(
                    f"{'🔴' if h['signal']=='EXIT' else '🟡'} **{h['ticker']}**"
                )
                col2.markdown(h["signal"])
                col3.markdown(f"₹{h['current_price']:.2f}")
                col4.markdown(f"{h['pnl_pct']:+.2f}%")
        else:
            st.success("✅ No action required today")
        # P&L mini chart
        holdings = port.get("holdings", [])
        if holdings:
            df_p = pd.DataFrame(holdings)[["ticker", "pnl_pct"]]
            df_p = df_p.set_index("ticker")
            st.bar_chart(df_p["pnl_pct"], height=150)
        st.caption(f"Last updated: {port.get('timestamp','—')}")
    else:
        st.info("No data yet.")

# ── Gold Silver Ratio ─────────────────────────────────────
with r3c2:
    gs = all_data.get("Gold Silver Ratio")
    st.markdown("#### 🥇 Gold / Silver Ratio")
    if gs and gs.get("status") == "ok":
        signal = gs.get("signal", "—")
        if "Silver" in signal: st.info(signal)
        elif "Gold"  in signal: st.info(signal)
        else:                   st.success(signal)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("GoldBeES",   f"₹{gs.get('gold_price', 0):.2f}")
        c2.metric("SilverBeES", f"₹{gs.get('silver_price', 0):.2f}")
        c3.metric("GSR",        f"{gs.get('gsr', 0):.4f}",
                  delta=f"{gs.get('gsr_dev_pct', 0):+.2f}% vs mean")
        c4.metric("Strength",   gs.get("strength", "—"))
        st.caption(
            f"6M Mean: {gs.get('gsr_mean',0):.4f} · "
            f"Min: {gs.get('gsr_min',0):.4f} · "
            f"Max: {gs.get('gsr_max',0):.4f}"
        )
        st.caption(f"Sentiment: {gs.get('sentiment','—')}")
        gr = gs.get("gold_returns",   {})
        sr = gs.get("silver_returns", {})
        st.markdown("**Returns**")
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Gold 1D",   f"{gr.get('1D', 0):+.2f}%")
        rc2.metric("Gold 1W",   f"{gr.get('1W', 0):+.2f}%")
        rc3.metric("Silver 1D", f"{sr.get('1D', 0):+.2f}%")
        rc4.metric("Silver 1W", f"{sr.get('1W', 0):+.2f}%")
        st.caption(f"Last updated: {gs.get('timestamp','—')}")
    else:
        st.info("No data yet.")

st.divider()

# =========================
# Row 4 — Earnings Tracker (full width)
# =========================
st.subheader("📅 Results & Earnings")
earn = all_data.get("Earnings Tracker")

if earn and earn.get("status") == "ok":

    today_list    = earn.get("today_results",    [])
    upcoming_list = earn.get("upcoming_results", [])
    today_counts  = earn.get("today_counts",     {"quarterly": 0, "annual": 0, "board": 0})
    upc_counts    = earn.get("upcoming_counts",  {"quarterly": 0, "annual": 0, "board": 0})

    # ── Summary metrics ───────────────────────────────────
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Results today",
               today_counts.get("quarterly", 0) + today_counts.get("annual", 0))
    mc2.metric("Board meetings today",  today_counts.get("board", 0))
    mc3.metric("Results upcoming",
               upc_counts.get("quarterly", 0) + upc_counts.get("annual", 0))
    mc4.metric("Meetings upcoming",     upc_counts.get("board", 0))

    e1, e2 = st.columns(2)

    # ── Today ─────────────────────────────────────────────
    with e1:
        if today_list:
            # Separate results from board meetings
            results_today = [r for r in today_list if r.get("category") != "board"]
            boards_today  = [r for r in today_list if r.get("category") == "board"]

            if results_today:
                st.markdown("**🔔 Results declared today**")
                for r in results_today:
                    st.caption(f"• **{r['symbol']}** — {r['company']} _{r['purpose_label']}_")

            if boards_today:
                st.markdown("**🏛️ Board meetings today**")
                for r in boards_today:
                    st.caption(f"• **{r['symbol']}** — {r['company']}")
        else:
            st.info("No result events today.")

    # ── Upcoming ──────────────────────────────────────────
    with e2:
        if upcoming_list:
            st.markdown("**📅 Upcoming (next 7 days)**")
            current_date = None
            shown = 0
            for r in upcoming_list[:12]:   # cap at 12 rows on home page
                if r["date"] != current_date:
                    current_date = r["date"]
                    st.caption(f"**{current_date}**")
                icon = "📊" if r.get("category") != "board" else "🏛️"
                st.caption(f"&nbsp;&nbsp;&nbsp;{icon} **{r['symbol']}** — {r['company']}")
                shown += 1

            remaining = len(upcoming_list) - shown
            if remaining > 0:
                st.caption(f"_+ {remaining} more → see full page_")
        else:
            st.info("No upcoming events in next 7 days.")

    st.caption(f"Last updated: {earn.get('timestamp','—')}")

else:
    st.info("No data yet.")

st.divider()

_, center_col, _ = st.columns([1, 2, 1])
with center_col:
    st.caption("© 2026 DSB Capital. All Rights Reserved.")