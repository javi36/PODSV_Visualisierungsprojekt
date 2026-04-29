import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app_config import GENERATION_ORDER, find_column, generation_from_birth_year

GENERATION_COLORS: dict[str, str] = {
    "Silent Generation": "#0f4c5c",
    "Babyboomers": "#1d7874",
    "Generation X": "#679289",
    "Millennials / Gen Y": "#f4a259",
    "Generation Z": "#f25c54",
}


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


# ── Alte Implementierung (nach Generation gruppiert, mit Geschlechtertrennung) ─
# def build_generation_pyramid_data(df: pd.DataFrame) -> pd.DataFrame:
#     year_col = find_column(df, ["jahr"])
#     canton_col = find_column(df, ["kanton"])
#     age_col = find_column(df, ["alter"])
#     population_col = find_column(df, ["bestand", "31"])
#
#     if any(c is None for c in [year_col, canton_col, age_col, population_col]):
#         raise ValueError("Missing required columns for pyramid data")
#
#     working = df.copy()
#     working[year_col] = pd.to_numeric(working[year_col], errors="coerce")
#     working[population_col] = pd.to_numeric(working[population_col], errors="coerce")
#     working["age_num"] = pd.to_numeric(
#         working[age_col].astype(str).str.extract(r"(\d+)", expand=False), errors="coerce"
#     )
#     working = working[
#         working[year_col].notna() & working[population_col].notna() & working["age_num"].notna()
#     ].copy()
#     working[year_col] = working[year_col].astype(int)
#
#     if find_column(df, ["staatsange"]):
#         nat_col = find_column(df, ["staatsange"])
#         working = working[working[nat_col].astype(str).str.contains("total", case=False, na=False)].copy()
#
#     working = working[working[canton_col].astype(str).str.strip().str.lower() == "schweiz"].copy()
#     working = working[~working[age_col].astype(str).str.contains("total", case=False, na=False)].copy()
#
#     gender_col = find_column(df, ["geschlecht"])
#     if gender_col and set(["Mann", "Frau"]).issubset(set(working[gender_col].unique())):
#         working = working[working[gender_col].isin(["Mann", "Frau"])].copy()
#         working["gender"] = working[gender_col]
#     else:
#         working = working[working[gender_col].astype(str).str.contains("total", case=False, na=False)].copy()
#         working["gender"] = "Total"
#
#     working["birth_year"] = working[year_col] - working["age_num"]
#     working["generation"] = working["birth_year"].apply(generation_from_birth_year)
#     working = working[working["generation"].isin(GENERATION_ORDER)].copy()
#
#     result = (
#         working.groupby([year_col, "generation", "gender"], as_index=False)[population_col]
#         .sum()
#         .rename(columns={year_col: "year", population_col: "population"})
#     )
#     result["generation"] = pd.Categorical(result["generation"], categories=GENERATION_ORDER, ordered=True)
#     return result
#
#
# def create_generation_pyramid(df: pd.DataFrame, selected_year: int):
#     year_data = df[df["year"] == selected_year].copy()
#     gen_display_order = list(reversed(GENERATION_ORDER))  # oldest at top
#
#     fig = go.Figure()
#     all_pops: list[int] = []
#
#     for gen in gen_display_order:
#         gen_data = year_data[year_data["generation"] == gen]
#         color = GENERATION_COLORS.get(gen, "#888888")
#
#         male_pop = int(gen_data[gen_data["gender"] == "Mann"]["population"].sum())
#         female_pop = int(gen_data[gen_data["gender"] == "Frau"]["population"].sum())
#         all_pops += [male_pop, female_pop]
#
#         fig.add_trace(go.Bar(
#             name=gen,
#             y=[gen],
#             x=[-male_pop],
#             orientation="h",
#             marker_color=color,
#             showlegend=False,
#             customdata=[[gen, male_pop]],
#             hovertemplate="<b>%{customdata[0]}</b><br>Männer: %{customdata[1]:,.0f}<extra></extra>",
#         ))
#         fig.add_trace(go.Bar(
#             name=gen,
#             y=[gen],
#             x=[female_pop],
#             orientation="h",
#             marker_color=color,
#             showlegend=True,
#             customdata=[[gen, female_pop]],
#             hovertemplate="<b>%{customdata[0]}</b><br>Frauen: %{customdata[1]:,.0f}<extra></extra>",
#         ))
#
#     max_pop = max(all_pops) if all_pops else 1_000_000
#     tick_step = 200_000
#     max_tick = (int(max_pop / tick_step) + 1) * tick_step
#     tick_vals = list(range(-max_tick, max_tick + tick_step, tick_step))
#     tick_texts = [f"{abs(v) // 1_000}k" if v != 0 else "0" for v in tick_vals]
#
#     fig.update_layout(
#         barmode="overlay",
#         height=370,
#         margin=dict(t=40, l=10, r=10, b=10),
#         plot_bgcolor="#ffffff",
#         paper_bgcolor="#ffffff",
#         xaxis=dict(
#             tickvals=tick_vals,
#             ticktext=tick_texts,
#             zeroline=True,
#             zerolinecolor="#bbbbbb",
#             zerolinewidth=2,
#             gridcolor="#f0f0f0",
#             range=[-max_tick * 1.08, max_tick * 1.08],
#         ),
#         yaxis=dict(
#             categoryorder="array",
#             categoryarray=gen_display_order,
#             tickfont=dict(size=12, color="#333333"),
#         ),
#         legend=dict(
#             orientation="h",
#             yanchor="bottom",
#             y=-0.22,
#             xanchor="center",
#             x=0.5,
#             title_text="",
#             font=dict(size=11),
#         ),
#         annotations=[
#             dict(
#                 text="← Männer",
#                 x=0.01, y=1.06, xref="paper", yref="paper",
#                 showarrow=False, font=dict(size=12, color="#555555"), xanchor="left",
#             ),
#             dict(
#                 text="Frauen →",
#                 x=0.99, y=1.06, xref="paper", yref="paper",
#                 showarrow=False, font=dict(size=12, color="#555555"), xanchor="right",
#             ),
#         ],
#     )
#     return fig
#
# ── Alternative: single bar per generation (no gender split) ─────────────────
# def create_generation_pyramid(df: pd.DataFrame, selected_year: int):
#     year_data = df[df["year"] == selected_year].copy()
#     totals = (
#         year_data.groupby("generation", as_index=False, observed=True)["population"]
#         .sum()
#     )
#     totals["generation"] = pd.Categorical(
#         totals["generation"], categories=GENERATION_ORDER, ordered=True
#     )
#     totals = totals.sort_values("generation")
#     gen_display_order = list(reversed(GENERATION_ORDER))
#     pop_by_gen = {row["generation"]: int(row["population"]) for _, row in totals.iterrows()}
#
#     fig = go.Figure()
#     for gen in gen_display_order:
#         pop = pop_by_gen.get(gen, 0)
#         fig.add_trace(go.Bar(
#             name=gen, y=[gen], x=[pop], orientation="h",
#             marker_color=GENERATION_COLORS.get(gen, "#888888"), showlegend=True,
#             customdata=[[gen, pop]],
#             hovertemplate="<b>%{customdata[0]}</b><br>Population: %{customdata[1]:,.0f}<extra></extra>",
#         ))
#     max_pop = max(pop_by_gen.values()) if pop_by_gen else 1_000_000
#     tick_step = 200_000
#     max_tick = (int(max_pop / tick_step) + 1) * tick_step
#     tick_vals = list(range(0, max_tick + tick_step, tick_step))
#     tick_texts = [f"{v // 1_000}k" if v > 0 else "0" for v in tick_vals]
#     fig.update_layout(
#         barmode="group", height=360,
#         margin=dict(t=20, l=10, r=30, b=10),
#         plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
#         xaxis=dict(tickvals=tick_vals, ticktext=tick_texts, gridcolor="#f0f0f0",
#                    zeroline=False, range=[0, max_tick * 1.08]),
#         yaxis=dict(categoryorder="array", categoryarray=gen_display_order,
#                    tickfont=dict(size=12, color="#333333")),
#         legend=dict(orientation="h", yanchor="bottom", y=-0.25,
#                     xanchor="center", x=0.5, title_text="", font=dict(size=11)),
#     )
#     return fig
# ─────────────────────────────────────────────────────────────────────────────


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
