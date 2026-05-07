import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_config import (
    BEWOHNERTYP_DATA_PATH,
    WOHNFLAECHE_DATA_PATH,
    inject_global_styles,
)
from generationalConflict_app import main as render_home
from who_decides_section import render_who_decides_section
from who_owns_section import (
    load_bewohnertyp_data,
    load_wohnflaeche_data,
    render_who_owns_section,
)
from who_pays_section import render_who_pays_section

st.set_page_config(
    page_title="Generational Conflict",
    page_icon=":family_man_woman_girl_boy:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_styles()

# ── Sidebar anchor-link styling ───────────────────────────────────────────────
st.markdown(
    """
    <style>
    .sidebar-nav-links a {
        display: block;
        padding: 0.38rem 0.6rem;
        font-size: 0.95rem;
        color: #111111;
        text-decoration: none;
        border-radius: 6px;
        margin-bottom: 2px;
        transition: background 0.12s;
    }
    .sidebar-nav-links a:hover {
        background: #f0f0f0;
        color: #111111;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar: Navigation Panel ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:0.78rem;text-transform:uppercase;letter-spacing:0.1em;"
        "color:#888888;font-weight:700;padding:0.6rem 0 0.5rem;'>🧭 Navigation Panel</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="sidebar-nav-links">
            <a href="#home">Home</a>
            <a href="#who-decides">🗳️ Who Decides</a>
            <a href="#who-pays">💸 Who Pays</a>
            <a href="#who-owns">🏡 Who Owns</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Main content — single scrollable page ────────────────────────────────────

# 1. Home
render_home()

# 2. Who Decides
st.markdown(
    """
    <div class="hero">
        <h1>Who Decides</h1>
        <p>Political power and voting influence across generations in Switzerland</p>
    </div>
    """,
    unsafe_allow_html=True,
)
render_who_decides_section()

# 3. Who Pays
st.markdown(
    """
    <div class="hero">
        <h1>Who Pays</h1>
        <p>Housing cost burden and rent pressure across generations in Switzerland</p>
    </div>
    """,
    unsafe_allow_html=True,
)
render_who_pays_section()

# 4. Who Owns
st.markdown(
    """
    <div class="hero">
        <h1>Who Owns</h1>
        <p>Homeownership rates and living space by generation in Switzerland</p>
    </div>
    """,
    unsafe_allow_html=True,
)
try:
    bewohnertyp_df = load_bewohnertyp_data(BEWOHNERTYP_DATA_PATH)
    wohnflaeche_df = load_wohnflaeche_data(WOHNFLAECHE_DATA_PATH)
except Exception as exc:
    st.error("Could not load ownership data.")
    st.exception(exc)
    st.stop()

render_who_owns_section(bewohnertyp_df, wohnflaeche_df)
