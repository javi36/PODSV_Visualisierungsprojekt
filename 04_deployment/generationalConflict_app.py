from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
	page_title="Generational Conflict",
	page_icon="🏠",
	layout="wide",
	initial_sidebar_state="collapsed",
)

st.markdown(
	"""
	<style>
		.stApp {
			background: #ffffff;
			color: #111111;
		}
		.main {
			max-width: 1200px;
			margin: 0 auto;
		}
		[data-testid="stSidebar"] {
			background: #ffffff;
		}
		.hero {
			text-align: center;
			padding: 2rem 0 1rem;
		}
		.hero h1 {
			font-size: 3rem;
			margin-bottom: 0.25rem;
			color: #111111;
		}
		.hero p {
			font-size: 1.2rem;
			color: #555555;
		}
		.narrative-text {
			font-size: 1.05rem;
			line-height: 1.7;
			background: #f7f7f7;
			border-left: 4px solid #1f77b4;
			padding: 1.25rem 1.4rem;
			border-radius: 4px;
			color: #111111;
		}
		.template-box {
			background: #fcfcfc;
			border: 1px dashed #c9c9c9;
			border-radius: 8px;
			padding: 1rem 1.1rem;
			color: #666666;
		}
		.section-title {
			font-size: 1.8rem;
			font-weight: 700;
			margin-top: 2rem;
			margin-bottom: 0.8rem;
			color: #111111;
		}
	</style>
	""",
	unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parents[1]
DEMOGRAPHIC_DATA_PATH = BASE_DIR / "data" / "demografischeBilanz.csv"

GENERATION_ORDER = [
	"Silent Generation",
	"Babyboomers",
	"Generation X",
	"Millennials / Gen Y",
	"Generation Z",
]
GENERATION_ORDER_WITH_YEAR = [
	'Silent Generation (<=1945)',
    'Babyboomers (1946-1964)',
    'Generation X (1965-1980)',
    'Millennials / Gen Y (1981-1996)',
    'Generation Z (1997-2012)',
]

@st.cache_data
def load_demographic_data(csv_path: Path) -> pd.DataFrame:
	df = pd.read_csv(csv_path, sep=";", encoding="latin1")
	df.columns = df.columns.str.strip()
	return df


def find_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
	for column in df.columns:
		column_lower = str(column).lower()
		if all(keyword in column_lower for keyword in keywords):
			return column
	return None


def generation_from_birth_year(birth_year: float) -> str:
	if pd.isna(birth_year):
		return "Other"
	if birth_year <= 1945:
		return "Silent Generation"
	if 1946 <= birth_year <= 1964:
		return "Babyboomers"
	if 1965 <= birth_year <= 1980:
		return "Generation X"
	if 1981 <= birth_year <= 1996:
		return "Millennials / Gen Y"
	if 1997 <= birth_year <= 2012:
		return "Generation Z"
	return "Other"


def format_ch_number(value: int | float) -> str:
	return f"{int(value):,}".replace(",", "'")


def build_generation_pie_data(df: pd.DataFrame) -> pd.DataFrame:
	year_col = find_column(df, ["jahr"])
	canton_col = find_column(df, ["kanton"])
	age_col = find_column(df, ["alter"])
	population_col = find_column(df, ["bestand", "31"])

	if any(column is None for column in [year_col, canton_col, age_col, population_col]):
		missing = [
			name
			for name, column in [
				("year", year_col),
				("canton", canton_col),
				("age", age_col),
				("population", population_col),
			]
			if column is None
		]
		raise ValueError(f"Missing required columns in demographic data: {missing}")

	working = df.copy()
	working[year_col] = pd.to_numeric(working[year_col], errors="coerce")
	working[population_col] = pd.to_numeric(working[population_col], errors="coerce")
	working["age_num"] = pd.to_numeric(working[age_col].astype(str).str.extract(r"(\d+)", expand=False), errors="coerce")
	working = working[
		working[year_col].notna()
		& working[population_col].notna()
		& working["age_num"].notna()
	].copy()
	working[year_col] = working[year_col].astype(int)
	if find_column(df, ["staatsange"]):
		nationality_col = find_column(df, ["staatsange"])
		working = working[working[nationality_col].astype(str).str.contains("total", case=False, na=False)].copy()
	if find_column(df, ["geschlecht"]):
		gender_col = find_column(df, ["geschlecht"])
		working = working[working[gender_col].astype(str).str.contains("total", case=False, na=False)].copy()
	working = working[working[canton_col].astype(str).str.strip().str.lower() == "schweiz"].copy()

	year_totals = (
		working[working[age_col].astype(str).str.contains("total", case=False, na=False)]
		.groupby(year_col, as_index=False)[population_col]
		.sum()
		.rename(columns={year_col: "year", population_col: "year_total"})
	)

	working = working[~working[age_col].astype(str).str.contains("total", case=False, na=False)].copy()
	working["birth_year"] = working[year_col] - working["age_num"]
	working["generation"] = working["birth_year"].apply(generation_from_birth_year)
	working = working[working["generation"].isin(GENERATION_ORDER)].copy()

	result = (
		working.groupby([year_col, "generation"], as_index=False)[population_col]
		.sum()
		.rename(columns={year_col: "year", population_col: "population"})
	)
	result = result.merge(year_totals, on="year", how="left")
	result["year_total"] = result["year_total"].fillna(result.groupby("year")["population"].transform("sum"))
	result["generation"] = pd.Categorical(result["generation"], categories=GENERATION_ORDER, ordered=True)
	return result


def create_generation_pie(df: pd.DataFrame, selected_year: int):
	year_data = df[df["year"] == selected_year].sort_values("generation")
	fig = px.pie(
		year_data,
		names="generation",
		values="population",
		hole=0.35,
		title=f"Swiss population by generation in {selected_year}",
		category_orders={"generation": GENERATION_ORDER},
		color="generation",
		color_discrete_sequence=["#0f4c5c", "#1d7874", "#679289", "#f4a259", "#f25c54"],
	)

	fig.update_layout(height=520, margin=dict(t=70, l=20, r=20, b=20))
	fig.update_traces(
		textposition="inside",
		textinfo="label",
	)

	return fig


def render_template_section(title: str, subtitle: str) -> None:
	st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
	st.markdown(f"<div class='narrative-text'>{subtitle}</div>", unsafe_allow_html=True)
	st.markdown(
		"<div class='template-box'>Template only for now. Add your future text, chart, or annotations here.</div>",
		unsafe_allow_html=True,
	)


def main() -> None:
	st.markdown(
		"""
		<div class="hero">
			<h1>Generational Conflict</h1>
			<p>blablabla</p>
		</div>
		""",
		unsafe_allow_html=True,
	)

	st.markdown(
		"""
		<div class='narrative-text'>
		Introduction text goes here.
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

	available_years = sorted(pie_data["year"].dropna().unique().tolist())
	if not available_years:
		st.error("No years were found in the demographic data.")
		st.stop()

	selected_year = st.selectbox("Select year", available_years, index=len(available_years) - 1)
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

	render_template_section(
		"1. Who Decides",
		"Placeholder section for the political voice part of the story.",
	)
	st.markdown("<br>", unsafe_allow_html=True)
	render_template_section(
		"2. Who Pays",
		"Placeholder section for the housing cost burden part of the story.",
	)
	st.markdown("<br>", unsafe_allow_html=True)
	render_template_section(
		"3. Who Owns",
		"Placeholder section for the ownership part of the story.",
	)

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
