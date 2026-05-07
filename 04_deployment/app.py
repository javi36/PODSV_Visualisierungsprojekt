import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_config import inject_global_styles

st.set_page_config(
    page_title="Generational Conflict",
    page_icon=":family_man_woman_girl_boy:",
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


pg.run()