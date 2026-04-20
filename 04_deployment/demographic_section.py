import pandas as pd
import plotly.express as px

from app_config import GENERATION_ORDER, find_column, generation_from_birth_year


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
	year_total = float(year_data["year_total"].iloc[0]) if not year_data.empty else 0
	fig = px.pie(
		year_data,
		names="generation",
		values="population",
		hole=0.46,
		title="",
		category_orders={"generation": GENERATION_ORDER},
		color="generation",
		color_discrete_sequence=["#0f4c5c", "#1d7874", "#679289", "#f4a259", "#f25c54"],
	)
	fig.update_layout(
		height=560,
		margin=dict(t=30, l=20, r=20, b=20),
		showlegend=True,
		legend=dict(orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5),
		annotations=[
			dict(
				text=f"<b>{selected_year}</b><br>{int(year_total):,}".replace(",", "'"),
				showarrow=False,
				x=0.5,
				y=0.5,
				font=dict(size=20, color="#111111"),
				align="center",
			),
		],
	)
	fig.update_traces(
		textposition="inside",
		textinfo="label+percent",
		insidetextorientation="radial",
		hovertemplate="<b>%{label}</b><br>Population: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
		marker=dict(line=dict(color="#ffffff", width=3)),
	)
	return fig
