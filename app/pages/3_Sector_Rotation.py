import streamlit as st
import pandas as pd
from core.db import load

st.set_page_config(page_title="Sector Rotation", page_icon="🔄", layout="wide")
st.title("🔄 Sector Rotation Tracker")

data = load("sector_rotation.json")

if not data or data.get("status") == "error":
    st.error(data.get("error", "No data yet.") if data else "No data yet. Trigger the workflow to run.")
    st.stop()

st.caption(f"Last updated: {data.get('timestamp', '—')} · Mode: {data.get('run_mode', '—')} {data.get('title_suffix', '')}")

# ── Leaders / Laggards ────────────────────────────────────
c1, c2 = st.columns(2)
c1.success(f"🏆 Leading: {', '.join(data.get('leaders', []))}")
c2.error(f"🔻 Laggards: {', '.join(data.get('laggards', []))}")

st.divider()

# ── Sector table ──────────────────────────────────────────
sectors = data.get("sectors", [])
if not sectors:
    st.info("No sector data available.")
    st.stop()

df = pd.DataFrame(sectors)

# Rank change arrow column
def rank_arrow(val):
    if val > 0:   return f"▲ {val}"
    elif val < 0: return f"▼ {abs(val)}"
    return "—"

df["rank_change"] = df["rank_change"].apply(rank_arrow)

st.dataframe(
    df[["rank", "sector", "rs", "mom", "signal", "score", "rank_change"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "rank":        st.column_config.NumberColumn("Rank"),
        "sector":      st.column_config.TextColumn("Sector"),
        "rs":          st.column_config.NumberColumn("RS %",  format="%+.2f"),
        "mom":         st.column_config.NumberColumn("MOM %", format="%+.2f"),
        "signal":      st.column_config.TextColumn("Signal"),
        "score":       st.column_config.NumberColumn("Score", format="%.2f"),
        "rank_change": st.column_config.TextColumn("Rank Δ"),
    },
)

st.divider()

# ── RS vs MOM scatter ─────────────────────────────────────
st.subheader("RS vs momentum — quadrant view")
scatter_df = pd.DataFrame(sectors).set_index("sector")
st.scatter_chart(scatter_df[["rs", "mom"]], x="rs", y="mom",
                 use_container_width=True)