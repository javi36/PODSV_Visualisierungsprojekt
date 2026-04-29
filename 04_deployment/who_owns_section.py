from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_config import (
    BEWOHNERTYP_DATA_PATH,
    GENERATION_ORDER,
    WOHNFLAECHE_DATA_PATH,
    generation_from_birth_year,
)

OCCUPANCY_CATEGORIES = ["Eigentümer", "Mieter / Genossenschaftler"]
OCCUPANCY_COLORS = {
    "Eigentümer": "#1d7874",
    "Mieter / Genossenschaftler": "#f4a259",
}

GENERATION_COLORS = {
    "Silent Generation": "#0f4c5c",
    "Babyboomers": "#1d7874",
    "Generation X": "#679289",
    "Millennials / Gen Y": "#f4a259",
    "Generation Z": "#f25c54",
}


@st.cache_data
def load_bewohnertyp_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df["alter"] = pd.to_numeric(df["alter"], errors="coerce")
    df["absolute zahlen"] = pd.to_numeric(df["absolute zahlen"], errors="coerce")
    df["bewohnertyp"] = df["bewohnertyp"].astype(str).str.strip()
    df["bewohnertyp"] = df["bewohnertyp"].replace({
        "Andere Situation2)": "Andere Situation",
        "Mieter oder Genossenschafter": "Mieter / Genossenschaftler",
    })
    df = df[df["bewohnertyp"].isin(OCCUPANCY_CATEGORIES)].copy()
    return df


@st.cache_data
def load_wohnflaeche_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df["alter"] = pd.to_numeric(df["alter"], errors="coerce")
    sqm_col = next((c for c in df.columns if "m2" in c.lower()), None)
    if sqm_col is None:
        raise ValueError("Living space column not found in wohnflaeche data")
    df = df.rename(columns={sqm_col: "sqm_per_person"})
    df["sqm_per_person"] = pd.to_numeric(df["sqm_per_person"], errors="coerce")
    return df


def _map_generation(df: pd.DataFrame, year: int) -> pd.DataFrame:
    df = df.copy()
    df["birth_year"] = year - df["alter"]
    df["generation"] = df["birth_year"].apply(generation_from_birth_year)
    return df[df["generation"].isin(GENERATION_ORDER)]


def build_occupancy_stacked_data(
    df: pd.DataFrame, selected_year: int, selected_gens: list[str]
) -> pd.DataFrame:
    year_data = df[df["time_period"] == selected_year].copy()
    year_data = _map_generation(year_data, selected_year)
    year_data = year_data[year_data["generation"].isin(selected_gens)]
    # Drop "Andere Situation" — too small to be meaningful, clutters the chart
    year_data = year_data[year_data["bewohnertyp"].isin(OCCUPANCY_CATEGORIES)]

    grouped = (
        year_data.groupby(["generation", "bewohnertyp"], as_index=False)["absolute zahlen"]
        .sum()
        .rename(columns={"absolute zahlen": "count"})
    )
    totals = grouped.groupby("generation")["count"].sum().reset_index(name="total")
    grouped = grouped.merge(totals, on="generation")
    grouped["pct"] = grouped["count"] / grouped["total"] * 100
    grouped["count_fmt"] = grouped["count"].apply(
        lambda x: f"{x/1_000_000:.2f} Mio" if x >= 1_000_000 else f"{x:,.0f}".replace(",", "'")
    )

    # Sort generations by Eigentümer share descending so the ownership gradient reads left→right
    eigentuemer_pct = (
        grouped[grouped["bewohnertyp"] == "Eigentümer"]
        .set_index("generation")["pct"]
    )
    sorted_gens = [
        g for g in sorted(selected_gens, key=lambda g: eigentuemer_pct.get(g, 0), reverse=True)
        if g in selected_gens
    ]

    grouped["generation"] = pd.Categorical(grouped["generation"], categories=sorted_gens, ordered=True)
    return grouped.sort_values("generation"), sorted_gens


def create_occupancy_stacked_bar(df: pd.DataFrame, sorted_gens: list[str]) -> go.Figure:
    fig = go.Figure()

    for cat in OCCUPANCY_CATEGORIES:
        cat_data = df[df["bewohnertyp"] == cat]

        y_vals, text_labels = [], []
        for gen in sorted_gens:
            row = cat_data[cat_data["generation"] == gen]
            pct = float(row["pct"].iloc[0]) if not row.empty else 0.0
            cnt = row["count_fmt"].iloc[0] if not row.empty else "—"
            y_vals.append(pct)
            text_labels.append(f"{pct:.0f}%" if pct >= 7 else "")

        fig.add_trace(go.Bar(
            name=cat,
            x=sorted_gens,
            y=y_vals,
            marker_color=OCCUPANCY_COLORS[cat],
            marker_line=dict(color="#ffffff", width=0.8),
            hovertemplate=[
                f"<b>{gen}</b><br>{cat}<br><b>{pct:.1f}%</b> · "
                f"{(cat_data[cat_data['generation'] == gen]['count_fmt'].iloc[0] if not cat_data[cat_data['generation'] == gen].empty else '—')}"
                f"<extra></extra>"
                for gen, pct in zip(sorted_gens, y_vals)
            ],
            text=text_labels,
            textposition="inside",
            textfont=dict(color="#ffffff", size=11, family="Arial"),
            insidetextanchor="middle",
        ))

    # Annotation: highlight the extremes of Eigentümer share
    eigentuemer_data = df[df["bewohnertyp"] == "Eigentümer"]
    annotations = []
    if not eigentuemer_data.empty and len(sorted_gens) >= 2:
        max_row = eigentuemer_data.loc[eigentuemer_data["pct"].idxmax()]
        min_row = eigentuemer_data.loc[eigentuemer_data["pct"].idxmin()]
        gap = max_row["pct"] - min_row["pct"]
        annotations.append(dict(
            x=0.5, y=1.08, xref="paper", yref="paper",
            text=f"<b>{max_row['generation']}</b>: {max_row['pct']:.0f}% Eigentümer "
                 f"— <b>{min_row['generation']}</b>: {min_row['pct']:.0f}% "
                 f"· Unterschied: <b>{gap:.0f} Prozentpunkte</b>",
            showarrow=False,
            font=dict(size=11, color="#555555"),
            xanchor="center",
        ))

    fig.update_layout(
        barmode="stack",
        height=420,
        margin=dict(t=50, l=10, r=10, b=70),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        bargap=0.25,
        yaxis=dict(
            title="Anteil (%)",
            range=[0, 100],
            ticksuffix="%",
            gridcolor="#f0f0f0",
            tickfont=dict(size=11),
        ),
        xaxis=dict(title="", tickfont=dict(size=11)),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
            traceorder="normal",
        ),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#dddddd", font_size=12, font_family="Arial"),
        annotations=annotations,
    )
    return fig


def build_wohnflaeche_data(df: pd.DataFrame, selected_gens: list[str]) -> pd.DataFrame:
    records = []
    for year in sorted(df["time_period"].unique()):
        year_data = _map_generation(df[df["time_period"] == year].copy(), year)
        year_data = year_data[year_data["generation"].isin(selected_gens)]
        gen_avg = (
            year_data.groupby("generation", as_index=False)["sqm_per_person"]
            .mean()
        )
        gen_avg["year"] = int(year)
        records.append(gen_avg)
    return pd.concat(records, ignore_index=True)


def create_wohnflaeche_line_chart(df: pd.DataFrame, selected_gens: list[str]) -> go.Figure:
    """Chart 1: Time trend — one line per generation, x = year.

    Improvements:
    - Direct labels at line ends instead of legend
    - Fill area between highest and lowest generation to highlight the gap
    - Gap annotation showing the m² difference
    """
    fig = go.Figure()
    all_years = sorted(df["year"].unique())
    last_year = max(all_years)

    # Determine top and bottom generation at the last year for the fill area
    last_data = df[df["year"] == last_year]
    filtered_last = last_data[last_data["generation"].isin(selected_gens)]
    top_gen = bottom_gen = None
    if len(filtered_last) >= 2:
        top_gen = filtered_last.loc[filtered_last["sqm_per_person"].idxmax(), "generation"]
        bottom_gen = filtered_last.loc[filtered_last["sqm_per_person"].idxmin(), "generation"]

    # Fill area between top and bottom generation to visualise the gap
    if top_gen and bottom_gen and top_gen != bottom_gen:
        bottom_data = df[df["generation"] == bottom_gen].sort_values("year")
        top_data = df[df["generation"] == top_gen].sort_values("year")
        fig.add_trace(go.Scatter(
            x=bottom_data["year"], y=bottom_data["sqm_per_person"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=top_data["year"], y=top_data["sqm_per_person"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
            fill="tonexty", fillcolor="rgba(100,160,200,0.10)",
        ))

    # Lines + markers per generation
    annotations = []
    for gen in selected_gens:
        gen_data = df[df["generation"] == gen].sort_values("year")
        color = GENERATION_COLORS.get(gen, "#888888")

        fig.add_trace(go.Scatter(
            name=gen,
            x=gen_data["year"],
            y=gen_data["sqm_per_person"],
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=8, color=color, line=dict(color="#ffffff", width=1.5)),
            showlegend=False,
            hovertemplate=f"<b>{gen}</b><br>%{{x}}: <b>%{{y:.1f}} m²/Person</b><extra></extra>",
        ))

        # Direct label at the right end of each line
        last_val = gen_data[gen_data["year"] == last_year]["sqm_per_person"]
        if not last_val.empty:
            annotations.append(dict(
                x=last_year,
                y=float(last_val.iloc[0]),
                xanchor="left",
                yanchor="middle",
                text=f"  <b>{gen}</b>",
                showarrow=False,
                font=dict(size=10, color=color),
                xref="x", yref="y",
            ))

    # Gap annotation between top and bottom at last year
    if top_gen and bottom_gen and top_gen != bottom_gen:
        top_val = float(df[(df["generation"] == top_gen) & (df["year"] == last_year)]["sqm_per_person"].iloc[0])
        bot_val = float(df[(df["generation"] == bottom_gen) & (df["year"] == last_year)]["sqm_per_person"].iloc[0])
        gap = top_val - bot_val
        mid_y = (top_val + bot_val) / 2
        mid_x = all_years[len(all_years) // 2]
        annotations.append(dict(
            x=mid_x,
            y=mid_y,
            xanchor="center",
            yanchor="middle",
            text=f"<b>+{gap:.0f} m²</b> difference",
            showarrow=False,
            font=dict(size=11, color="#555555"),
            bgcolor="rgba(255,255,255,0.75)",
            bordercolor="#cccccc",
            borderwidth=1,
            xref="x", yref="y",
        ))

    fig.update_layout(
        height=340,
        margin=dict(t=10, l=10, r=155, b=30),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            tickvals=all_years,
            ticktext=[str(y) for y in all_years],
            gridcolor="#f0f0f0",
            title="",
        ),
        yaxis=dict(
            title="m² per person",
            gridcolor="#f0f0f0",
            ticksuffix=" m²",
        ),
        showlegend=False,
        annotations=annotations,
    )
    return fig


def create_wohnflaeche_ranking_chart(
    df: pd.DataFrame, selected_year: int, selected_gens: list[str]
) -> go.Figure:
    """Chart 2: Horizontal bar ranking — generations on y-axis, x = m² for selected year."""
    year_data = df[df["year"] == selected_year].copy()
    year_data = year_data[year_data["generation"].isin(selected_gens)]

    # Sort ascending so largest value appears at top of horizontal bar chart
    year_data = year_data.sort_values("sqm_per_person", ascending=True)

    colors = [GENERATION_COLORS.get(g, "#888888") for g in year_data["generation"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        orientation="h",
        x=year_data["sqm_per_person"],
        y=year_data["generation"],
        marker_color=colors,
        text=[f"{v:.1f} m²" for v in year_data["sqm_per_person"]],
        textposition="outside",
        textfont=dict(size=11, color="#444444"),
        hovertemplate="<b>%{y}</b><br><b>%{x:.1f} m²/person</b><extra></extra>",
        cliponaxis=False,
    ))

    x_max = year_data["sqm_per_person"].max()

    fig.update_layout(
        height=280,
        margin=dict(t=10, l=10, r=60, b=40),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            title="m² per person",
            gridcolor="#f0f0f0",
            ticksuffix=" m²",
            range=[0, x_max * 1.18],  # padding so outside labels aren't clipped
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=11),
        ),
        showlegend=False,
    )
    return fig


def render_who_owns_section(
    bewohnertyp_df: pd.DataFrame,
    wohnflaeche_df: pd.DataFrame,
) -> None:
    # ── Read shared filters from sidebar session_state ────────────────────────
    selected_gens: list[str] = st.session_state.get("sidebar_generations", GENERATION_ORDER)
    selected_year: int = st.session_state.get("sidebar_year", 2024)

    if len(selected_gens) < 2:
        st.info("Please select at least 2 generations in the sidebar Control Panel.", icon="ℹ️")
        return

    # ── Intro ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="narrative-text">
        Homeownership in Switzerland is deeply unequal across generations. While older cohorts accumulated
        property during decades of low interest rates, younger generations are increasingly locked out of
        the housing market — renting by necessity rather than choice. Below you can explore how occupancy
        types and living space have evolved since 2019, broken down by generation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 100% Stacked bar ──────────────────────────────────────────────────────
    st.markdown("<div class='pyramid-title'>Occupancy Type by Generation</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='pyramid-subtitle'>Share of housing tenure types · {selected_year}</div>",
        unsafe_allow_html=True,
    )

    stacked_data, sorted_gens = build_occupancy_stacked_data(bewohnertyp_df, selected_year, selected_gens)
    st.plotly_chart(
        create_occupancy_stacked_bar(stacked_data, sorted_gens),
        use_container_width=True,
    )

    # ── Text box 1 ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="narrative-text">
        <em>Story placeholder — add your analysis here: e.g., Babyboomers hold the highest ownership rate
        while Generation Z and Millennials are predominantly renters.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart 1: Time trend ───────────────────────────────────────────────────
    st.markdown("<div class='pyramid-title'>Average Living Space per Person — Trend Over Time</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='pyramid-subtitle'>m² per person by generation · 2019–2024 · use sidebar to filter generations</div>",
        unsafe_allow_html=True,
    )

    wf_data = build_wohnflaeche_data(wohnflaeche_df, selected_gens)
    st.plotly_chart(
        create_wohnflaeche_line_chart(wf_data, selected_gens),
        use_container_width=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart 2: Ranking per selected year ────────────────────────────────────
    st.markdown("<div class='pyramid-title'>Living Space Ranking by Generation</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='pyramid-subtitle'>m² per person · ranked largest to smallest · {selected_year}</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        create_wohnflaeche_ranking_chart(wf_data, selected_year, selected_gens),
        use_container_width=True,
    )

    # ── Text box 2 ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="narrative-text">
        <em>Story placeholder — add your analysis here: e.g., older generations enjoy significantly more
        living space per person, partly due to children leaving and ownership of larger properties.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )