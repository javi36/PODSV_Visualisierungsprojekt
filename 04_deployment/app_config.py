from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DEMOGRAPHIC_DATA_PATH = BASE_DIR / "data" / "demografischeBilanz.csv"
BEWOHNERTYP_DATA_PATH = BASE_DIR / "data" / "whoOwns" / "processed" / "bfs_bewohnertyp_20260414_clean.csv"

GENERATION_ORDER = [
	"Silent Generation",
	"Babyboomers",
	"Generation X",
	"Millennials / Gen Y",
	"Generation Z",
]

WHO_OWNS_CATEGORIES = [
	"Andere Situation",
	"Eigentümer",
	"Mieter oder Genossenschaftler",
]

GLOBAL_STYLES = """
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
"""


def inject_global_styles() -> None:
	st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)


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


def generation_label_to_age_range(generation_label: str) -> tuple[int, int]:
	ranges = {
		"Silent Generation": (79, 120),
		"Babyboomers": (60, 78),
		"Generation X": (44, 59),
		"Millennials / Gen Y": (28, 43),
		"Generation Z": (12, 27),
	}
	return ranges[generation_label]


def format_ch_number(value: int | float) -> str:
	return f"{int(value):,}".replace(",", "'")
