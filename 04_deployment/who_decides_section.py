import streamlit as st


def render_who_decides_section() -> None:
	st.markdown("<div class='section-title'>1. Who Decides</div>", unsafe_allow_html=True)
	st.markdown(
		"""
		<div class='narrative-text'>
		Placeholder section for the political voice part of the story.
		</div>
		""",
		unsafe_allow_html=True,
	)
	st.markdown(
		"<div class='template-box'>Template only for now. Add your future text, chart, or annotations here.</div>",
		unsafe_allow_html=True,
	)
