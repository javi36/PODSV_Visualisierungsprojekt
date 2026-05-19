import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_config import (
    BEWOHNERTYP_DATA_PATH,
    WOHNFLAECHE_DATA_PATH,
    inject_global_styles,
)
from generationalConflict_app import main as render_home
from references import render_references_section
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

# ── Page routing via query param (?page=references opens the References page) ─
_current_page = st.query_params.get("page", "main")

# ── Sidebar collapse → full-width layout (JS MutationObserver) ───────────────
components.html(
    """
    <script>
    (function () {
        var doc = window.parent.document;
        function applyLayout() {
            var sidebar = doc.querySelector('[data-testid="stSidebar"]');
            var view    = doc.querySelector('[data-testid="stAppViewContainer"]');
            if (!sidebar || !view) return;
            var collapsed = sidebar.getAttribute('aria-expanded') === 'false';
            view.style.setProperty('margin-left', collapsed ? '0'   : '', collapsed ? 'important' : '');
            view.style.setProperty('width',       collapsed ? '100%': '', collapsed ? 'important' : '');
            var bc = view.querySelector('.block-container');
            if (bc) bc.style.setProperty('max-width', collapsed ? '100%' : '', collapsed ? 'important' : '');
        }
        new MutationObserver(applyLayout).observe(doc.body, {
            attributes: true, subtree: true, attributeFilter: ['aria-expanded']
        });
        applyLayout();
    })();
    </script>
    """,
    height=0,
)

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
    if _current_page == "references":
        st.markdown(
            """
            <div class="sidebar-nav-links">
                <a href="?page=main">← Back to Dashboard</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-nav-links">
                <a href="#home">Home</a>
                <a href="#who-decides">🗳️ Who Decides the Rules</a>
                <a href="#who-pays">💸 Who Bears the Costs</a>
                <a href="#who-owns">🏡 Who Holds the Assets</a>
                <a href="?page=references" style="margin-top:0.5rem;border-top:1px solid #eeeeee;padding-top:0.5rem;">📚 References</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Main content — routed by query param ─────────────────────────────────────

if _current_page == "references":
    st.markdown(
        """
        <div class="hero">
            <h1>📚 References</h1>
            <p>Data sources and academic literature cited in this dashboard</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_references_section()
else:
    # 1. Home
    render_home()

    # 2. Who Decides
    st.markdown(
    """
    <div class="hero">
        <h1>Who Decides the Rules</h1>
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
        <h1>Who Bears the Costs</h1>
        <p>Every generation pays in. But not every generation gets the same deal back.</p>
    </div>
    """,
    unsafe_allow_html=True,
    )
    render_who_pays_section()

    # 4. Who Owns
    st.markdown(
    """
    <div class="hero">
        <h1>Who Holds the Assets</h1>
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
