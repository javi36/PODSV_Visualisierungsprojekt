import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app_config import GENERATION_COLORS, GENERATION_ORDER, find_column, generation_from_birth_year


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

def build_generation_pyramid_data(df: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per (year, age, generation) with total population (no gender split)."""
    year_col = find_column(df, ["jahr"])
    canton_col = find_column(df, ["kanton"])
    age_col = find_column(df, ["alter"])
    population_col = find_column(df, ["bestand", "31"])

    if any(c is None for c in [year_col, canton_col, age_col, population_col]):
        raise ValueError("Missing required columns for age pyramid data")

    working = df.copy()
    working[year_col] = pd.to_numeric(working[year_col], errors="coerce")
    working[population_col] = pd.to_numeric(working[population_col], errors="coerce")
    working["age_num"] = pd.to_numeric(
        working[age_col].astype(str).str.extract(r"(\d+)", expand=False), errors="coerce"
    )
    working = working[
        working[year_col].notna() & working[population_col].notna() & working["age_num"].notna()
    ].copy()
    working[year_col] = working[year_col].astype(int)

    if find_column(df, ["staatsange"]):
        nat_col = find_column(df, ["staatsange"])
        working = working[working[nat_col].astype(str).str.contains("total", case=False, na=False)].copy()

    if find_column(df, ["geschlecht"]):
        gender_col = find_column(df, ["geschlecht"])
        working = working[working[gender_col].astype(str).str.contains("total", case=False, na=False)].copy()

    working = working[working[canton_col].astype(str).str.strip().str.lower() == "schweiz"].copy()
    working = working[~working[age_col].astype(str).str.contains("total", case=False, na=False)].copy()

    working["birth_year"] = working[year_col] - working["age_num"]
    working["generation"] = working["birth_year"].apply(generation_from_birth_year)
    working = working[working["generation"].isin(GENERATION_ORDER)].copy()

    result = (
        working.groupby([year_col, "age_num", "generation"], as_index=False)[population_col]
        .sum()
        .rename(columns={year_col: "year", population_col: "population"})
    )
    result["generation"] = pd.Categorical(result["generation"], categories=GENERATION_ORDER, ordered=True)
    result["age_num"] = result["age_num"].astype(int)
    return result


def create_generation_pyramid(df: pd.DataFrame, selected_year: int):
    """Symmetric stacked bar chart: y = age 0–100, bars mirrored left/right, colored by generation."""
    year_data = df[df["year"] == selected_year].copy()
    all_ages = list(range(0, 101))

    fig = go.Figure()

    for gen in GENERATION_ORDER:
        gen_data = year_data[year_data["generation"] == gen].set_index("age_num")
        pops = [int(gen_data.loc[age, "population"]) if age in gen_data.index else 0 for age in all_ages]
        color = GENERATION_COLORS.get(gen, "#888888")

        # left side (negative)
        fig.add_trace(go.Bar(
            name=gen,
            y=all_ages,
            x=[-p for p in pops],
            orientation="h",
            marker_color=color,
            showlegend=False,
            hovertemplate=f"<b>{gen}</b><br>Alter: %{{y}}<br>Bevölkerung: %{{customdata:,.0f}}<extra></extra>",
            customdata=pops,
        ))
        # right side (positive) — carries the legend entry
        fig.add_trace(go.Bar(
            name=gen,
            y=all_ages,
            x=pops,
            orientation="h",
            marker_color=color,
            showlegend=True,
            hovertemplate=f"<b>{gen}</b><br>Alter: %{{y}}<br>Bevölkerung: %{{x:,.0f}}<extra></extra>",
        ))

    max_pop = int(year_data["population"].max()) if not year_data.empty else 100_000
    tick_step = 20_000
    max_tick = (int(max_pop / tick_step) + 1) * tick_step
    tick_vals = list(range(-max_tick, max_tick + tick_step, tick_step))
    tick_texts = [f"{abs(v) // 1_000}k" if v != 0 else "0" for v in tick_vals]

    fig.update_layout(
        barmode="overlay",
        height=750,
        margin=dict(t=20, l=10, r=30, b=80),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            tickvals=tick_vals,
            ticktext=tick_texts,
            zeroline=True,
            zerolinecolor="#bbbbbb",
            zerolinewidth=2,
            gridcolor="#f0f0f0",
            range=[-max_tick * 1.08, max_tick * 1.08],
        ),
        yaxis=dict(
            tickmode="linear",
            tick0=0,
            dtick=5,
            range=[-0.5, 100.5],
            tickfont=dict(size=10, color="#333333"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            title_text="",
            font=dict(size=11),
        ),
    )
    return fig


def create_generation_area_chart(df: pd.DataFrame, from_year: int, to_year: int, relative: bool):
    """Stacked area chart: x = year, areas = generations, colored by GENERATION_COLORS."""
    gen_year = (
        df.groupby(["year", "generation"], observed=True)["population"]
        .sum()
        .reset_index()
    )
    gen_year = gen_year[(gen_year["year"] >= from_year) & (gen_year["year"] <= to_year)].copy()

    if relative:
        total_per_year = gen_year.groupby("year")["population"].transform("sum")
        gen_year["value"] = gen_year["population"] / total_per_year * 100
    else:
        gen_year["value"] = gen_year["population"]

    fig = go.Figure()
    for gen in GENERATION_ORDER:
        sub = gen_year[gen_year["generation"] == gen].sort_values("year")
        color = GENERATION_COLORS.get(gen, "#888888")
        hover = f"<b>{gen}</b><br>Year: %{{x}}<br>{'Share: %{y:.1f}%' if relative else 'Population: %{y:,.0f}'}<extra></extra>"
        fig.add_trace(go.Scatter(
            name=gen,
            x=sub["year"],
            y=sub["value"],
            mode="lines",
            stackgroup="one",
            line=dict(width=0.5, color=color),
            fillcolor=color,
            hovertemplate=hover,
        ))

    fig.update_layout(
        height=400,
        margin=dict(t=10, l=10, r=30, b=50),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            tickmode="linear",
            dtick=1,
            gridcolor="#f0f0f0",
            tickfont=dict(size=13, color="#555555"),
            tickangle=45,
        ),
        yaxis=dict(
            gridcolor="#f0f0f0",
            ticksuffix="%" if relative else "",
            tickformat=".0f" if relative else ",.0f",
            tickfont=dict(size=13, color="#555555"),
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="right",
            x=1,
            title_text="",
            font=dict(size=13),
            bgcolor="rgba(255,255,255,0.8)",
        ),
        hoverlabel=dict(font=dict(size=14)),
        hovermode="x unified",
        legend_itemclick=False,
        legend_itemdoubleclick=False,
    )
    return fig


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
