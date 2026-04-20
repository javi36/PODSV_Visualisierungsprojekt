from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app_config import BEWOHNERTYP_DATA_PATH, GENERATION_ORDER, WHO_OWNS_CATEGORIES, format_ch_number, generation_from_birth_year, generation_label_to_age_range


@st.cache_data
def load_bewohnertyp_data(csv_path: Path) -> pd.DataFrame:
	df = pd.read_csv(csv_path)
	df.columns = df.columns.str.strip()
	df["alter"] = pd.to_numeric(df["alter"], errors="coerce")
	df["absolute zahlen"] = pd.to_numeric(df["absolute zahlen"], errors="coerce")
	df["generation"] = df["alter"].apply(lambda age: generation_from_birth_year(2024 - age) if pd.notna(age) else "Other")
	df["bewohnertyp"] = df["bewohnertyp"].astype(str).str.strip()
	df = df[df["generation"].isin(GENERATION_ORDER)].copy()
	df = df[df["bewohnertyp"].isin(["Andere Situation2)", "Eigentümer", "Mieter oder Genossenschafter"])].copy()
	df["bewohnertyp"] = df["bewohnertyp"].replace({
		"Andere Situation2)": "Andere Situation",
		"Mieter oder Genossenschafter": "Mieter oder Genossenschaftler",
	})
	return df


def build_ownership_distribution(df: pd.DataFrame, generation_label: str) -> pd.DataFrame:
	min_age, max_age = generation_label_to_age_range(generation_label)
	filtered = df[(df["alter"] >= min_age) & (df["alter"] <= max_age)].copy()
	distribution = (
		filtered.groupby("bewohnertyp", as_index=False)["absolute zahlen"]
		.sum()
		.rename(columns={"absolute zahlen": "population"})
	)
	distribution = distribution.set_index("bewohnertyp").reindex(WHO_OWNS_CATEGORIES, fill_value=0).reset_index()
	distribution["generation"] = generation_label
	return distribution


def create_ownership_donut(df: pd.DataFrame, generation_label: str):
	chart_data = build_ownership_distribution(df, generation_label)
	fig = px.pie(
		chart_data,
		names="bewohnertyp",
		values="population",
		hole=0.5,
		category_orders={"bewohnertyp": WHO_OWNS_CATEGORIES},
		color="bewohnertyp",
		color_discrete_sequence=["#8c8c8c", "#1f77b4", "#2ca02c"],
		labels={"bewohnertyp": "Category", "population": "Population"},
		title=generation_label,
	)
	fig.update_traces(
		textinfo="percent",
		textposition="inside",
		insidetextorientation="radial",
		hovertemplate="%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>",
	)
	fig.update_layout(
		height=460,
		margin=dict(t=80, l=20, r=20, b=20),
		showlegend=True,
		legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
	)
	return fig


def render_who_owns_section(bewohnertyp_df: pd.DataFrame) -> None:
	st.markdown("<div class='section-title'>3. Who Owns</div>", unsafe_allow_html=True)
	st.markdown(
		"""
		<div class='narrative-text'>
		This section compares the 2024 bewohnertyp structure across generations. Select two different generations to compare them side by side.
		</div>
		""",
		unsafe_allow_html=True,
	)

	gen_options = GENERATION_ORDER
	col_sel_1, col_sel_2 = st.columns(2)
	with col_sel_1:
		first_generation = st.selectbox("First generation", gen_options, index=0, key="who_owns_first_generation")
	with col_sel_2:
		second_options = [generation for generation in gen_options if generation != first_generation]
		second_generation = st.selectbox("Second generation", second_options, index=0 if second_options else 0, key="who_owns_second_generation")

	comparison_metric_col_1, comparison_metric_col_2 = st.columns(2)
	with comparison_metric_col_1:
		first_total = build_ownership_distribution(bewohnertyp_df, first_generation)["population"].sum()
		st.metric("First generation total", format_ch_number(first_total))
	with comparison_metric_col_2:
		second_total = build_ownership_distribution(bewohnertyp_df, second_generation)["population"].sum()
		st.metric("Second generation total", format_ch_number(second_total))

	chart_col_1, chart_col_2 = st.columns(2, gap="large")
	with chart_col_1:
		st.markdown(
			f"<div class='template-box' style='margin-bottom:0.75rem; font-weight:700; color:#111111;'>{first_generation}</div>",
			unsafe_allow_html=True,
		)
		st.plotly_chart(create_ownership_donut(bewohnertyp_df, first_generation), use_container_width=True)
	with chart_col_2:
		st.markdown(
			f"<div class='template-box' style='margin-bottom:0.75rem; font-weight:700; color:#111111;'>{second_generation}</div>",
			unsafe_allow_html=True,
		)
		st.plotly_chart(create_ownership_donut(bewohnertyp_df, second_generation), use_container_width=True)

	st.markdown(
		"""
		<div class='narrative-text'>
		The donuts show how the 2024 bewohnertyp composition changes by generation. This makes it easier to compare
		how ownership status, renting or cooperative living, and other living situations differ across age cohorts.
		</div>
		""",
		unsafe_allow_html=True,
	)

	st.markdown(
		"""
		<div class='template-box'>
		The bewohnertyp data for 2024 is now connected to the Who Owns section. The next step is to add a short analytical
		story above or below these charts.
		</div>
		""",
		unsafe_allow_html=True,
	)
