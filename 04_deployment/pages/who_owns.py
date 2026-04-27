import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_config import BEWOHNERTYP_DATA_PATH, WOHNFLAECHE_DATA_PATH
from who_owns_section import load_bewohnertyp_data, load_wohnflaeche_data, render_who_owns_section

st.markdown("<div class='back-btn-wrapper'>", unsafe_allow_html=True)
if st.button("← Back to Overview", key="back_btn"):
    st.switch_page("generationalConflict_app.py")
st.markdown("</div>", unsafe_allow_html=True)

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
