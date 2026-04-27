import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_config import GENERATION_ORDER, inject_global_styles

st.set_page_config(
    page_title="Generational Conflict",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_styles()

# ── Page routing (nav hidden — sidebar built manually below) ──────────────────
pg = st.navigation(
    [
        st.Page("generationalConflict_app.py", title="Home", icon="🏠", default=True),
        st.Page("pages/who_decides.py", title="Who Decides", icon="🗳️"),
        st.Page("pages/who_pays.py", title="Who Pays", icon="💸"),
        st.Page("pages/who_owns.py", title="Who Owns", icon="🏡"),
    ],
    position="hidden",
)

# ── Full sidebar: Navigation Panel + Control Panel ────────────────────────────
_YEARS = list(range(2019, 2025))

with st.sidebar:
    # — Navigation Panel —
    st.markdown(
        "<div style='font-size:0.78rem;text-transform:uppercase;letter-spacing:0.1em;"
        "color:#888888;font-weight:700;padding:0.6rem 0 0.5rem;'>🧭 Navigation Panel</div>",
        unsafe_allow_html=True,
    )
    st.page_link("generationalConflict_app.py", label="Home", icon="🏠")
    st.page_link("pages/who_decides.py", label="Who Decides", icon="🗳️")
    st.page_link("pages/who_pays.py", label="Who Pays", icon="💸")
    st.page_link("pages/who_owns.py", label="Who Owns", icon="🏡")

    st.divider()

    # — Control Panel —
    st.markdown(
        "<div style='font-size:0.78rem;text-transform:uppercase;letter-spacing:0.1em;"
        "color:#888888;font-weight:700;padding:0.2rem 0 0.4rem;'>🎛️ Control Panel</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;"
        "color:#666666;margin-bottom:0.3rem;margin-top:0.4rem;'>Compare Generations</div>",
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Generations",
        options=GENERATION_ORDER,
        default=GENERATION_ORDER,
        key="sidebar_generations",
        label_visibility="collapsed",
    )
    current_gens = st.session_state.get("sidebar_generations", GENERATION_ORDER)
    if len(current_gens) < 2:
        st.warning("Select at least 2 generations.", icon="⚠️")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;"
        "color:#666666;margin-bottom:0.3rem;'>Year</div>",
        unsafe_allow_html=True,
    )
    st.slider(
        "Year",
        min_value=_YEARS[0],
        max_value=_YEARS[-1],
        value=_YEARS[-1],
        step=1,
        key="sidebar_year",
        label_visibility="collapsed",
    )
    _sel_year = st.session_state.get("sidebar_year", _YEARS[-1])
    _tick_spans = "".join(
        f"<span style='font-size:0.62rem;"
        f"font-weight:{'700' if y == _sel_year else '400'};"
        f"color:{'#111111' if y == _sel_year else '#bbbbbb'};'>{y}</span>"
        for y in _YEARS
    )
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;"
        f"margin-top:-0.5rem;padding:0 0.3rem;'>{_tick_spans}</div>",
        unsafe_allow_html=True,
    )

pg.run()
