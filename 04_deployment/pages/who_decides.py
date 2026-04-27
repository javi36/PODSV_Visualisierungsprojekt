import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_config import inject_global_styles
from who_decides_section import render_who_decides_section

st.set_page_config(
    page_title="Who Decides · Generational Conflict",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_styles()

st.markdown(
    """
    <div class="back-btn-wrapper">
    """,
    unsafe_allow_html=True,
)
if st.button("← Back to Overview", key="back_btn"):
    st.switch_page("generationalConflict_app.py")
st.markdown("</div>", unsafe_allow_html=True)

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
