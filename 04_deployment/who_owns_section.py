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

OCCUPANCY_CATEGORIES = ["Eigentümer", "Mieter / Genossenschaftler", "Andere Situation"]
OCCUPANCY_COLORS = {
    "Eigentümer": "#1d7874",
    "Mieter / Genossenschaftler": "#f4a259",
    "Andere Situation": "#cccccc",
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

    grouped = (
        year_data.groupby(["generation", "bewohnertyp"], as_index=False)["absolute zahlen"]
        .sum()
        .rename(columns={"absolute zahlen": "count"})
    )
    totals = grouped.groupby("generation")["count"].sum().reset_index(name="total")
    grouped = grouped.merge(totals, on="generation")
    grouped["pct"] = grouped["count"] / grouped["total"] * 100
    grouped["generation"] = pd.Categorical(grouped["generation"], categories=selected_gens, ordered=True)
    return grouped.sort_values("generation")


def create_occupancy_stacked_bar(df: pd.DataFrame, selected_gens: list[str]) -> go.Figure:
    fig = go.Figure()
    for cat in OCCUPANCY_CATEGORIES:
        cat_data = df[df["bewohnertyp"] == cat]
        gen_order = [g for g in selected_gens if g in cat_data["generation"].values]
        x_vals = [g for g in selected_gens]
        y_vals = []
        for gen in selected_gens:
            row = cat_data[cat_data["generation"] == gen]
            y_vals.append(float(row["pct"].iloc[0]) if not row.empty else 0.0)

        fig.add_trace(go.Bar(
            name=cat,
            x=x_vals,
            y=y_vals,
            marker_color=OCCUPANCY_COLORS[cat],
            hovertemplate=(
                "<b>%{x}</b><br>"
                + cat
                + ": <b>%{y:.1f}%</b><extra></extra>"
            ),
            text=[f"{v:.0f}%" if v >= 5 else "" for v in y_vals],
            textposition="inside",
            textfont=dict(color="#ffffff", size=11),
        ))

    fig.update_layout(
        barmode="stack",
        height=380,
        margin=dict(t=20, l=10, r=10, b=80),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        yaxis=dict(
            title="Share (%)",
            range=[0, 100],
            ticksuffix="%",
            gridcolor="#f0f0f0",
        ),
        xaxis=dict(title="", tickfont=dict(size=11)),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.28,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
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
    fig = go.Figure()
    all_years = sorted(df["year"].unique())

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
            hovertemplate=(
                f"<b>{gen}</b><br>"
                "%{x}: <b>%{y:.1f} m²/person</b><extra></extra>"
            ),
        ))

    fig.update_layout(
        height=380,
        margin=dict(t=20, l=10, r=10, b=80),
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.28,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
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

    stacked_data = build_occupancy_stacked_data(bewohnertyp_df, selected_year, selected_gens)
    st.plotly_chart(
        create_occupancy_stacked_bar(stacked_data, selected_gens),
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

    # ── Living space line chart ───────────────────────────────────────────────
    st.markdown("<div class='pyramid-title'>Average Living Space per Person</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='pyramid-subtitle'>m² per person by generation · 2019–2024 · use sidebar to filter generations</div>",
        unsafe_allow_html=True,
    )

    wf_data = build_wohnflaeche_data(wohnflaeche_df, selected_gens)
    st.plotly_chart(
        create_wohnflaeche_line_chart(wf_data, selected_gens),
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
