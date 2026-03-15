# app/load_data.py
# Called by every page to ensure data is preloaded into session state.
# Drive is only hit once per 15 minutes regardless of how many pages you visit.

import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import DATA_FILES

def _fetch_all() -> dict:
    """Load all 7 module JSONs from Drive in parallel."""
    from core.db import load

    def fetch(item):
        name, filename = item
        return name, load(filename)

    results = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {
            executor.submit(fetch, item): item
            for item in DATA_FILES.items()
        }
        for future in as_completed(futures):
            name, data = future.result()
            results[name] = data
    return results


def preload(force: bool = False) -> dict:
    """
    Load all module data into session_state once.
    Subsequent calls return instantly from memory.
    Pass force=True to bypass cache and reload from Drive.
    """
    if "module_data" not in st.session_state or force:
        with st.spinner("Loading dashboard data..."):
            st.session_state["module_data"] = _fetch_all()
            st.session_state["module_data_loaded"] = True
    return st.session_state["module_data"]


def get(module_name: str) -> dict | None:
    """Get a single module's data from session state."""
    return preload().get(module_name)