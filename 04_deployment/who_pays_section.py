import streamlit as st


def render_who_pays_section() -> None:
	st.markdown('<div id="who-pays"></div>', unsafe_allow_html=True)
	st.markdown("<div class='section-title'>2. Who Pays</div>", unsafe_allow_html=True)
	st.markdown(
		"""
		<div class='narrative-text'>
		Placeholder section for the housing cost burden part of the story.
		</div>
		""",
		unsafe_allow_html=True,
	)
	st.markdown(
		"<div class='template-box'>Template only for now. Add your future text, chart, or annotations here.</div>",
		unsafe_allow_html=True,
	)
