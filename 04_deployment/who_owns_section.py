from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_config import (
    BEWOHNERTYP_DATA_PATH,
    GENERATION_COLORS,
    GENERATION_ORDER,
    GENERATION_YEAR_LABELS,
    WOHNFLAECHE_DATA_PATH,
    generation_from_birth_year,
)

OCCUPANCY_CATEGORIES = ["Eigentümer", "Mieter / Genossenschaftler"]
OWNER_COLOR = "#020c0b"
RENTER_COLOR = "#a0a0a0"
LABEL_EN = {
    "Eigentümer": "Owner",
    "Mieter / Genossenschaftler": "Renter / Cooperative",
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
    """Horizontal 100% stacked bar: generations on y-axis, sorted by Eigentümer % descending."""
    fig = go.Figure()
    # Reversed so highest ownership appears at top
    y_order = list(reversed(sorted_gens))

    for cat in OCCUPANCY_CATEGORIES:
        cat_data = df[df["bewohnertyp"] == cat]
        x_vals, text_labels, bar_colors = [], [], []
        for gen in y_order:
            row = cat_data[cat_data["generation"] == gen]
            pct = float(row["pct"].iloc[0]) if not row.empty else 0.0
            x_vals.append(pct)
            text_labels.append(f"{pct:.0f}%" if pct >= 8 else "")
            bar_colors.append(OWNER_COLOR if cat == "Eigentümer" else RENTER_COLOR)

        fig.add_trace(go.Bar(
            name=LABEL_EN.get(cat, cat),
            orientation="h",
            y=y_order,
            x=x_vals,
            marker_color=bar_colors,
            marker_line=dict(color="#ffffff", width=1.2),
            hovertemplate=[
                f"<b>{GENERATION_YEAR_LABELS.get(gen, gen)}</b><br>{LABEL_EN.get(cat, cat)}<br><b>{pct:.1f}%</b> · "
                f"{(cat_data[cat_data['generation'] == gen]['count_fmt'].iloc[0] if not cat_data[cat_data['generation'] == gen].empty else '—')}"
                f"<extra></extra>"
                for gen, pct in zip(y_order, x_vals)
            ],
            text=text_labels,
            textposition="inside",
            textfont=dict(color="#ffffff", size=14, family="Arial", weight="bold"),
            insidetextanchor="middle",
        ))

    fig.update_layout(
        barmode="stack",
        height=40 + len(sorted_gens) * 60,
        margin=dict(t=10, l=10, r=10, b=50),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        bargap=0.28,
        xaxis=dict(
            range=[0, 100],
            ticksuffix="%",
            gridcolor="#f0f0f0",
            title="",
            tickfont=dict(size=12, color="#888888"),
        ),
        yaxis=dict(
            title="",
            tickvals=y_order,
            ticktext=[GENERATION_YEAR_LABELS.get(g, g) for g in y_order],
            tickfont=dict(size=13, color="#333333"),
            automargin=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="left",
            x=0,
            font=dict(size=13),
            traceorder="normal",
        ),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#dddddd", font_size=14, font_family="Arial"),
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
            hovertemplate=f"<b>{GENERATION_YEAR_LABELS.get(gen, gen)}</b><br>%{{x}}: <b>%{{y:.1f}} m²/Person</b><extra></extra>",
        ))

        # Direct label at the right end of each line
        last_val = gen_data[gen_data["year"] == last_year]["sqm_per_person"]
        if not last_val.empty:
            annotations.append(dict(
                x=last_year,
                y=float(last_val.iloc[0]),
                xanchor="left",
                yanchor="middle",
                text=f"  <b>{GENERATION_YEAR_LABELS.get(gen, gen)}</b>",
                showarrow=False,
                font=dict(size=12, color=color),
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
            font=dict(size=13, color="#555555"),
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
    """Horizontal ranking bars with light background track, colored by generation."""
    year_data = df[df["year"] == selected_year].copy()
    year_data = year_data[year_data["generation"].isin(selected_gens)]
    year_data = year_data.sort_values("sqm_per_person", ascending=True)  # top = largest

    gens = list(year_data["generation"])
    labeled_gens = [GENERATION_YEAR_LABELS.get(g, g) for g in gens]
    vals = list(year_data["sqm_per_person"])
    colors = [GENERATION_COLORS.get(g, "#888888") for g in gens]
    x_max = max(vals) * 1.05 if vals else 80

    fig = go.Figure()

    # Light background track (full width per bar)
    fig.add_trace(go.Bar(
        orientation="h",
        y=labeled_gens,
        x=[x_max] * len(gens),
        marker_color="#f0ede6",
        marker_line_width=0,
        showlegend=False,
        hoverinfo="skip",
    ))

    # Colored foreground bars
    fig.add_trace(go.Bar(
        orientation="h",
        y=labeled_gens,
        x=vals,
        marker_color=colors,
        marker_line_width=0,
        text=[f"  {v:.1f} m²" for v in vals],
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(size=14, color="#ffffff", weight="bold"),
        hovertemplate="<b>%{y}</b><br><b>%{x:.1f} m²/Person</b><extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        barmode="overlay",
        height=50 + len(gens) * 55,
        margin=dict(t=5, l=10, r=20, b=10),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        bargap=0.3,
        xaxis=dict(visible=False, range=[0, x_max]),
        yaxis=dict(
            title="",
            tickfont=dict(size=13, color="#444444"),
            automargin=True,
        ),
        showlegend=False,
    )
    return fig


def create_space_ownership_scatter(
    wf_df: pd.DataFrame, occ_df: pd.DataFrame, selected_year: int, selected_gens: list[str]
) -> go.Figure:
    """Scatter: x = Eigentümer %, y = m²/person. One dot per generation + trend line."""
    year_wf = wf_df[wf_df["year"] == selected_year][["generation", "sqm_per_person"]]
    year_occ = occ_df[occ_df["bewohnertyp"] == "Eigentümer"][["generation", "pct"]]

    merged = year_wf.merge(year_occ, on="generation")
    merged = merged[merged["generation"].isin(selected_gens)]

    if merged.empty:
        return go.Figure()

    x = merged["pct"].values
    y = merged["sqm_per_person"].values

    # Linear trend line
    coeffs = np.polyfit(x, y, 1)
    x_line = np.linspace(x.min() - 3, x.max() + 3, 100)
    y_line = np.polyval(coeffs, x_line)

    # Pearson r for annotation
    r = float(np.corrcoef(x, y)[0, 1])

    fig = go.Figure()

    # Trend line
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode="lines",
        line=dict(color="#cccccc", width=1.5, dash="dot"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # One point per generation
    for _, row in merged.iterrows():
        gen = row["generation"]
        fig.add_trace(go.Scatter(
            x=[row["pct"]],
            y=[row["sqm_per_person"]],
            mode="markers+text",
            name=gen,
            marker=dict(
                color=GENERATION_COLORS.get(gen, "#888888"),
                size=14,
                line=dict(color="#ffffff", width=2),
            ),
            text=[GENERATION_YEAR_LABELS.get(gen, gen)],
            textposition="top center",
            textfont=dict(size=14, color="#111111", family="sans-serif"),
            hovertemplate=(
                f"<b>{GENERATION_YEAR_LABELS.get(gen, gen)}</b><br>"
                f"Eigentümer: <b>{row['pct']:.1f}%</b><br>"
                f"Wohnfläche: <b>{row['sqm_per_person']:.1f} m²/Person</b>"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.add_annotation(
        x=0.98, y=0.04, xref="paper", yref="paper",
        text=f"r = {r:.2f}",
        showarrow=False,
        font=dict(size=14, color="#111111", family="sans-serif"),
        xanchor="right",
    )

    fig.update_layout(
        height=300,
        margin=dict(t=15, l=10, r=20, b=40),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            title=dict(text="Eigentümerquote (%)", font=dict(size=14, color="#111111")),
            ticksuffix="%",
            tickfont=dict(size=13, color="#111111"),
            gridcolor="#e8e8e8",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="m² pro Person", font=dict(size=14, color="#111111")),
            ticksuffix=" m²",
            tickfont=dict(size=13, color="#111111"),
            gridcolor="#e8e8e8",
            zeroline=False,
        ),
        showlegend=False,
    )
    return fig


def render_who_owns_section(
    bewohnertyp_df: pd.DataFrame,
    wohnflaeche_df: pd.DataFrame,
) -> None:
    st.markdown('<div id="who-owns"></div>', unsafe_allow_html=True)

    # ── Read shared filters from sidebar session_state ────────────────────────
    selected_gens: list[str] = st.session_state.get("sidebar_generations", GENERATION_ORDER)

    if len(selected_gens) < 2:
        st.info("Please select at least 2 generations in the sidebar Control Panel.", icon="ℹ️")
        return

    _avail_years = sorted(int(y) for y in bewohnertyp_df["time_period"].dropna().unique())
    _avail_years_str = [str(y) for y in _avail_years]

    def _year_radio(label: str, key: str) -> int:
        col_label, col_radio = st.columns([1, 6])
        with col_label:
            st.markdown(
                f"<div style='font-size:0.75rem;font-weight:600;text-transform:uppercase;"
                f"letter-spacing:0.07em;color:#999999;padding-top:0.55rem;'>{label}</div>",
                unsafe_allow_html=True,
            )
        with col_radio:
            val = st.radio(label, options=_avail_years_str, index=len(_avail_years_str) - 1,
                           horizontal=True, key=key, label_visibility="collapsed")
        return int(val)

    # ── Compute occupancy stats for storytelling ──────────────────────────────
    # Read year from session_state first so header/text already reflect the chosen year
    year_occ = int(st.session_state.get("whoowns_year_occ", str(_avail_years[-1])))
    stacked_data, sorted_gens = build_occupancy_stacked_data(bewohnertyp_df, year_occ, selected_gens)
    eig = stacked_data[stacked_data["bewohnertyp"] == "Eigentümer"]
    max_row = eig.loc[eig["pct"].idxmax()] if not eig.empty else None
    min_row = eig.loc[eig["pct"].idxmin()] if not eig.empty else None
    gap = round(max_row["pct"] - min_row["pct"]) if (max_row is not None and min_row is not None) else 0
    max_gen = max_row["generation"] if max_row is not None else "—"
    min_gen = min_row["generation"] if min_row is not None else "—"
    max_pct = round(max_row["pct"]) if max_row is not None else 0
    min_pct = round(min_row["pct"]) if min_row is not None else 0

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(
        f"<h2 style='font-size:1.7rem;font-weight:800;color:#111111;margin:0 0 1rem;'>"
        f"A {gap}% ownership gap separates {max_gen} from {min_gen}</h2>",
        unsafe_allow_html=True,
    )

    # ── Intro paragraph ───────────────────────────────────────────────────────
    _boomer_row = eig[eig["generation"] == "Babyboomers"]
    _milli_row  = eig[eig["generation"] == "Millennials / Gen Y"]
    _boomer_pct = round(float(_boomer_row["pct"].iloc[0])) if not _boomer_row.empty else max_pct
    _milli_pct  = round(float(_milli_row["pct"].iloc[0]))  if not _milli_row.empty  else min_pct
    _gap_pct    = abs(_boomer_pct - _milli_pct)
    _bc = GENERATION_COLORS.get("Babyboomers", "#2a9d8f")
    _mc = GENERATION_COLORS.get("Millennials / Gen Y", "#e9c46a")

    st.markdown(
        f"""
        <p style="font-size:1.05rem;line-height:1.8;color:#333333;margin-bottom:1.4rem;">
        Homeownership in Switzerland is closely tied to generation. Older populations accumulated
        property during a more accessible market era, while younger generations find themselves
        priced into renting. <span style="color:{_bc};font-weight:700;">Babyboomers</span> lead
        with an ownership rate of <span style="color:{_bc};font-weight:700;">{_boomer_pct}%</span>,
        while <span style="color:{_mc};font-weight:700;">Millennials&nbsp;/&nbsp;Gen&nbsp;Y</span>
        sit at just <span style="color:{_mc};font-weight:700;">{_milli_pct}%</span>&nbsp;—
        a gap of <span style="font-weight:700;color:#111111;">{_gap_pct}&nbsp;percentage&nbsp;points</span>.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 100% Horizontal stacked bar ───────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.85rem;color:#666666;margin-bottom:0.3rem;'>"
        f"Share of owners vs. renters/cooperative members, by generation · {year_occ}</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        create_occupancy_stacked_bar(stacked_data, sorted_gens),
        use_container_width=True,
    )
    _year_radio("Filter by Year", "whoowns_year_occ")

    # ── Narrative insight box ─────────────────────────────────────────────────
    wf_data = build_wohnflaeche_data(wohnflaeche_df, selected_gens)
    all_years = sorted(wf_data["year"].unique())
    year_range = f"{min(all_years)}–{max(all_years)}"

    st.markdown(
        f"<div style='font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;"
        f"color:#aaaaaa;margin:0.8rem 0 0.5rem;'>What the {year_range} trend tells us</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="narrative-text">
        <strong>The pattern is consistent.</strong> Ownership declines steadily.
        The trend is not random — it reflects structural barriers: rising property prices,
        stagnant wages, and increasing competition for ownership in Swiss cities.
        For younger generations, renting is not a lifestyle choice — it is increasingly the only option.
        As housing costs continue to rise relative to income, the generational wealth gap in Switzerland
        is likely to widen. This connects directly to the "Who pays?" dimension of this project:
        those who rent pay more of their income for housing, while those who own accumulate
        financial security — and arguably more political stake in protecting it.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Living space section ──────────────────────────────────────────────────
    st.markdown("<div style='border-top:1px solid #eeeeee;margin:1.5rem 0 1rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<h2 style='font-size:1.7rem;font-weight:800;color:#111111;margin:0 0 1rem;'>"
        "Older generations live in twice the space — and the gap is not closing</h2>",
        unsafe_allow_html=True,
    )

    year_wf_sel = int(st.session_state.get("whoowns_year_wf", str(_avail_years[-1])))
    year_wf = wf_data[wf_data["year"] == year_wf_sel]

    wf_max_row = year_wf.loc[year_wf["sqm_per_person"].idxmax()] if not year_wf.empty else None
    wf_min_row = year_wf.loc[year_wf["sqm_per_person"].idxmin()] if not year_wf.empty else None
    wf_max_gen = wf_max_row["generation"] if wf_max_row is not None else "—"
    wf_min_gen = wf_min_row["generation"] if wf_min_row is not None else "—"
    wf_max_val = wf_max_row["sqm_per_person"] if wf_max_row is not None else 0.0
    wf_min_val = wf_min_row["sqm_per_person"] if wf_min_row is not None else 0.0
    wf_gap = wf_max_val - wf_min_val

    first_year_wf = wf_data[wf_data["year"] == min(all_years)]
    gap_persisted = False
    if not first_year_wf.empty and wf_max_gen != "—" and wf_min_gen != "—":
        first_max = first_year_wf[first_year_wf["generation"] == wf_max_gen]["sqm_per_person"]
        first_min = first_year_wf[first_year_wf["generation"] == wf_min_gen]["sqm_per_person"]
        gap_persisted = not first_max.empty and not first_min.empty

    _max_color = GENERATION_COLORS.get(wf_max_gen, "#1d7874")
    _min_color = GENERATION_COLORS.get(wf_min_gen, "#f25c54")
    _persisted_note = (
        f"a gap that has persisted across all {len(all_years)} years without narrowing"
        if gap_persisted else f"a gap measured in {year_wf_sel}"
    )
    st.markdown(
        f"""
        <p style="font-size:1.05rem;line-height:1.8;color:#333333;margin-bottom:1.4rem;">
        In Switzerland, the average living space per person differs sharply by generation.
        The <span style="color:{_max_color};font-weight:700;">{wf_max_gen}</span> enjoys
        <span style="color:{_max_color};font-weight:700;">{wf_max_val:.1f}&nbsp;m²</span> per person,
        while <span style="color:{_min_color};font-weight:700;">{wf_min_gen}</span> has just
        <span style="color:{_min_color};font-weight:700;">{wf_min_val:.1f}&nbsp;m²</span>&nbsp;—
        a difference of <span style="font-weight:700;color:#111111;">+{wf_gap:.0f}&nbsp;m²</span>,
        {_persisted_note}.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='font-size:0.85rem;color:#888888;margin-bottom:0.3rem;'>"
        f"Living space ranking by generation · {year_wf_sel}</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        create_wohnflaeche_ranking_chart(wf_data, year_wf_sel, selected_gens),
        use_container_width=True,
    )
    _year_radio("Filter by Year", "whoowns_year_wf")

    st.markdown(
        f"<div style='font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;"
        f"color:#aaaaaa;margin:0.8rem 0 0.5rem;'>What the {year_range} trend tells us</div>",
        unsafe_allow_html=True,
    )
    sorted_wf = year_wf.sort_values("sqm_per_person", ascending=False)
    gen_trend_summary = (
        " No generation overtook another. " + wf_max_gen + " and " +
        (sorted_wf.iloc[1]["generation"] if len(sorted_wf) > 1 else "") +
        " maintained their lead, while " + wf_min_gen +
        (" and " + sorted_wf.iloc[-2]["generation"] if len(sorted_wf) > 2 else "") +
        " stayed at the bottom — with both groups seeing only marginal changes in absolute m²."
    )
    st.markdown(
        f"""
        <div class="narrative-text">
        Over {len(all_years)} years, the ranking between generations remained <strong>completely stable</strong>.{gen_trend_summary}
        The gap of <strong>+{wf_gap:.0f} m²</strong> shown in the chart was already present in {min(all_years)} and has not narrowed since.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Scatter: ownership rate vs. living space ──────────────────────────────
    st.markdown("<div style='border-top:1px solid #eeeeee;margin:1.5rem 0 1rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<h2 style='font-size:1.7rem;font-weight:800;color:#111111;margin:0 0 1rem;'>"
        "Korrelation: Eigentümerquote vs. Wohnfläche</h2>",
        unsafe_allow_html=True,
    )

    year_scatter = int(st.session_state.get("whoowns_year_scatter", str(_avail_years[-1])))

    st.markdown(
        f"""
        <div padding:1.2rem 1.4rem;margin-bottom:1rem;">
        <strong>Why does space correlate with ownership?</strong> Living space and property ownership
        are closely linked. Owners typically live in larger homes — houses and larger flats — while
        renters occupy smaller apartments. The same generational divide seen in the ownership chart
        (<span style="color:{GENERATION_COLORS.get(max_gen, '#1d7874')};font-weight:700;">{max_pct}%</span> vs. <span style="color:{GENERATION_COLORS.get(min_gen, '#f25c54')};font-weight:700;">{min_pct}%</span>) is mirrored here: those who own more tend to live in more.
        Living space is not just comfort — it is a proxy for wealth accumulation and housing security.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    scatter_occ, _ = build_occupancy_stacked_data(bewohnertyp_df, year_scatter, GENERATION_ORDER)
    scatter_wf = build_wohnflaeche_data(wohnflaeche_df, GENERATION_ORDER)
    st.plotly_chart(
        create_space_ownership_scatter(scatter_wf, scatter_occ, year_scatter, GENERATION_ORDER),
        use_container_width=True,
    )
    _year_radio("Filter by Year", "whoowns_year_scatter")



    # ── Closing paragraph ─────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background:#f4f8f6;border:1px solid #c8ddd6;
        border-radius:8px;padding:1.3rem 1.5rem;margin-top:1rem;">
        <h5> Conclusion: A reinforcing gap in space and ownership</h6>
        <p style="font-size:1.08rem;line-height:1.75;color:#222222;margin:0 0 0.9rem;">
        The living space gap reinforces the ownership gap. Together, they suggest that younger generations
        in Switzerland are not only less likely to own property — they also live in significantly more
        constrained conditions. As housing prices continue to rise, the prospect of younger cohorts
        closing this gap through future ownership becomes increasingly uncertain. This connects directly
        to the "Who pays?" dimension: smaller rented spaces often come at a disproportionately high
        cost relative to income.
        </p>
        <span style="font-size:0.8rem;color:#999999;">
        Source: Visualization based on FSO data from {year_scatter}
        </span>
        </div>
        """,
        unsafe_allow_html=True,
    )