from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DEMOGRAPHIC_DATA_PATH = BASE_DIR / "data" / "demografischeBilanz.csv"
BEWOHNERTYP_DATA_PATH = BASE_DIR / "data" / "whoOwns" / "processed" / "bfs_bewohnertyp_20260414_clean.csv"
WOHNFLAECHE_DATA_PATH = BASE_DIR / "data" / "whoOwns" / "processed" / "bfs_wohnflaeche_20260414_clean.csv"

GENERATION_ORDER = [
	"Silent Generation",
	"Babyboomers",
	"Generation X",
	"Millennials / Gen Y",
	"Generation Z",
]

GENERATION_COLORS: dict[str, str] = {
	"Silent Generation": "#0f4c5c",
	"Babyboomers": "#1d7874",
	"Generation X": "#679289",
	"Millennials / Gen Y": "#f4a259",
	"Generation Z": "#f25c54",
}

SIDEBAR_YEARS: list[int] = list(range(2019, 2025))

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
		min-width: 290px !important;
		width: 290px !important;
	}
	section[data-testid="stSidebar"] > div:first-child {
		padding-top: 0.5rem;
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
	.filter-panel {
		background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
		border: 1px solid #e9e9e9;
		border-radius: 20px;
		padding: 1rem 1.1rem 1.05rem;
		box-shadow: 0 12px 28px rgba(17, 17, 17, 0.05);
		margin: 0.5rem 0 1.4rem;
	}
	.filter-title {
		font-size: 0.84rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: #6f6f6f;
		margin-bottom: 0.35rem;
	}
	.filter-heading {
		font-size: 1.1rem;
		font-weight: 700;
		color: #111111;
		margin-bottom: 0.25rem;
	}
	.filter-copy {
		font-size: 0.95rem;
		line-height: 1.55;
		color: #5d5d5d;
		margin-bottom: 0.8rem;
	}
	.stat-panel {
		background: linear-gradient(180deg, #ffffff 0%, #fbfbfb 100%);
		border: 1px solid #ececec;
		border-radius: 18px;
		padding: 1rem 1rem 0.9rem;
		box-shadow: 0 10px 28px rgba(17, 17, 17, 0.05);
	}
	.stat-card {
		background: #ffffff;
		border: 1px solid #ececec;
		border-radius: 14px;
		padding: 0.85rem 0.95rem;
		box-shadow: 0 4px 14px rgba(17, 17, 17, 0.04);
	}
	.stat-label {
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #707070;
		margin-bottom: 0.25rem;
	}
	.stat-value {
		font-size: 1.35rem;
		font-weight: 700;
		color: #111111;
		line-height: 1.2;
	}
	.stat-subtle {
		font-size: 0.92rem;
		color: #5f5f5f;
		margin-top: 0.15rem;
	}
	.generation-list-title {
		font-size: 0.95rem;
		font-weight: 700;
		margin: 0.15rem 0 0.75rem;
		color: #111111;
	}
	.generation-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.62rem 0.8rem;
		margin-bottom: 0.5rem;
		background: #f8f8f8;
		border: 1px solid #e8e8e8;
		border-radius: 12px;
	}
	.generation-name {
		font-weight: 600;
		color: #111111;
	}
	.generation-pop {
		font-variant-numeric: tabular-nums;
		color: #555555;
	}
	.gen-card {
		background: #ffffff;
		border: 1px solid #ececec;
		border-radius: 14px;
		padding: 1.1rem 1rem 1rem;
		box-shadow: 0 4px 14px rgba(17,17,17,0.05);
		height: 100%;
	}
	.gen-card-name {
		font-size: 0.88rem;
		font-weight: 700;
		color: #111111;
		margin-bottom: 0.25rem;
		line-height: 1.3;
	}
	.gen-card-years {
		font-size: 0.75rem;
		color: #888888;
		margin-bottom: 0.3rem;
	}
	.gen-card-age {
		font-size: 1.05rem;
		font-weight: 700;
		color: #111111;
		margin-bottom: 0.6rem;
	}
	.gen-card-facts {
		font-size: 0.8rem;
		color: #444444;
		padding-left: 1rem;
		margin: 0;
		line-height: 1.5;
	}
	.gen-card-facts li {
		margin-bottom: 0.2rem;
	}
	.pyramid-section {
		background: #ffffff;
		border: 1px solid #ececec;
		border-radius: 18px;
		padding: 1.2rem 1.4rem 0.8rem;
		box-shadow: 0 6px 22px rgba(17,17,17,0.04);
		margin-top: 1.4rem;
	}
	.pyramid-title {
		font-size: 1.25rem;
		font-weight: 700;
		color: #111111;
		margin-bottom: 0.2rem;
	}
	.pyramid-subtitle {
		font-size: 0.9rem;
		color: #666666;
		margin-bottom: 0.6rem;
	}
	.slider-label {
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #888888;
		margin-bottom: 0.1rem;
	}
	.nav-section-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: #111111;
		text-align: center;
		margin-top: 2.2rem;
		margin-bottom: 0.4rem;
	}
	.nav-section-subtitle {
		font-size: 0.95rem;
		color: #666666;
		text-align: center;
		margin-bottom: 1.4rem;
	}
	.nav-card {
		background: #f8f9fa;
		border: 1px solid #e8e8e8;
		border-radius: 16px;
		padding: 1.4rem 1rem 1rem;
		text-align: center;
		margin-bottom: 0.8rem;
		transition: box-shadow 0.15s;
	}
	.nav-card-icon {
		font-size: 2.2rem;
		margin-bottom: 0.5rem;
	}
	.nav-card-title {
		font-size: 1.05rem;
		font-weight: 700;
		color: #111111;
		margin-bottom: 0.3rem;
	}
	.nav-card-desc {
		font-size: 0.84rem;
		color: #666666;
		line-height: 1.5;
		margin-bottom: 0.2rem;
	}
	.back-btn-wrapper {
		padding: 0.5rem 0 1.2rem;
	}
	div[data-testid="stSlider"] [data-testid="stTickBarMin"],
	div[data-testid="stSlider"] [data-testid="stTickBarMax"],
	div[data-testid="stSlider"] [data-testid="stTickBarMin"]:hover,
	div[data-testid="stSlider"] [data-testid="stTickBarMax"]:hover {
		display: none !important;
		visibility: hidden !important;
		opacity: 0 !important;
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
