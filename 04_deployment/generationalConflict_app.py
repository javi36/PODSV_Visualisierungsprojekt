import streamlit as st

from app_config import DEMOGRAPHIC_DATA_PATH, BEWOHNERTYP_DATA_PATH, GENERATION_ORDER, format_ch_number, inject_global_styles, load_demographic_data
from demographic_section import build_generation_pie_data, create_generation_pie
from who_decides_section import render_who_decides_section
from who_pays_section import render_who_pays_section
from who_owns_section import load_bewohnertyp_data, render_who_owns_section


st.set_page_config(
	page_title="Generational Conflict",
	page_icon="🏠",
	layout="wide",
	initial_sidebar_state="collapsed",
)

inject_global_styles()


def main() -> None:
	st.markdown(
		"""
		<div class="hero">
			<h1>Generational Conflict</h1>
			<p>A one-page storytelling template for housing, power, and ownership</p>
		</div>
		""",
		unsafe_allow_html=True,
	)

	st.markdown(
		"""
		<div class='narrative-text'>
		This page is intentionally minimal for now. The three story sections below stay empty as a template,
		while the active visualization compares the 2024 bewohnertyp distribution across generations.
		</div>
		""",
		unsafe_allow_html=True,
	)

	try:
		demographic_df = load_demographic_data(DEMOGRAPHIC_DATA_PATH)
		pie_data = build_generation_pie_data(demographic_df)
	except Exception as exc:  # noqa: BLE001
		st.error("Could not prepare the demographic data.")
		st.exception(exc)
		st.stop()

	try:
		bewohnertyp_df = load_bewohnertyp_data(BEWOHNERTYP_DATA_PATH)
	except Exception as exc:  # noqa: BLE001
		st.error("Could not prepare the bewohnertyp data.")
		st.exception(exc)
		st.stop()

	available_years = sorted(pie_data["year"].dropna().unique().tolist())
	if not available_years:
		st.error("No years were found in the demographic data.")
		st.stop()

	selected_year = st.selectbox("Select year", available_years, index=len(available_years) - 1, key="demographic_year_select")
	filtered_year = pie_data[pie_data["year"] == selected_year].copy()

	st.markdown("<div class='section-title'>Demographic Balance</div>", unsafe_allow_html=True)
	col_chart, col_stats = st.columns([2, 1])

	with col_chart:
		st.plotly_chart(create_generation_pie(pie_data, selected_year), use_container_width=True)
		st.markdown(
			"""
			<div class='narrative-text'>
			The pie chart shows how the Swiss population is distributed across the five generations for the selected year.
			This is the only active visual for now, so you can use it as the base for the final storytelling flow.
			</div>
			""",
			unsafe_allow_html=True,
		)

	with col_stats:
		st.metric("Selected year", selected_year)
		st.metric("Generations shown", len(GENERATION_ORDER))
		st.metric("Population total", format_ch_number(filtered_year["year_total"].iloc[0]))
		st.caption("The chart uses the demographic balance data and filters by year.")

	st.markdown("---")
	render_who_decides_section()
	st.markdown("<br>", unsafe_allow_html=True)
	render_who_pays_section()
	st.markdown("<br>", unsafe_allow_html=True)
	render_who_owns_section(bewohnertyp_df)

	st.markdown("---")
	st.markdown(
		"""
		<div style='text-align: center; color: #888; font-size: 0.9rem; padding: 1rem 0 2rem;'>
		Template version: only the demographic balance visualization is active.
		</div>
		""",
		unsafe_allow_html=True,
	)


if __name__ == "__main__":
	main()
