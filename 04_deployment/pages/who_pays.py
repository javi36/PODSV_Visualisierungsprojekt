import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from who_pays_section import render_who_pays_section

st.markdown("<div class='back-btn-wrapper'>", unsafe_allow_html=True)
if st.button("← Back to Overview", key="back_btn"):
    st.switch_page("generationalConflict_app.py")
st.markdown("</div>", unsafe_allow_html=True)

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
