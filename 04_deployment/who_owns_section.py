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
            range=[-14, 100],
            tickvals=[0, 20, 40, 60, 80, 100],
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
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0, y=-0.1,
        xanchor="left", yanchor="top",
        text="Source: BFS — Strukturerhebung (Bewohnertyp), 2024",
        showarrow=False,
        font=dict(size=9, color="#aaaaaa"),
    )

    # Subtle bracket on the LEFT, flush with the y-axis labels — connects Gen X and Gen Z rows
    if "Generation X" in y_order and "Generation Z" in y_order:
        gx_y = y_order.index("Generation X")
        gz_y = y_order.index("Generation Z")
        bracket_x = -1.5      # vertical line position (just left of the bars)
        tick_end = -0.3       # tick ends extend right toward the bars
        bracket_color = "#888888"
        for shape in [
            dict(type="line", x0=bracket_x, x1=bracket_x, y0=gx_y, y1=gz_y),
            dict(type="line", x0=bracket_x, x1=tick_end, y0=gx_y, y1=gx_y),
            dict(type="line", x0=bracket_x, x1=tick_end, y0=gz_y, y1=gz_y),
        ]:
            fig.add_shape(**shape, line=dict(color=bracket_color, width=1.4), layer="above")
        fig.add_annotation(
            x=-2.5,
            y=(gx_y + gz_y) / 2,
            text="often share<br>a household",
            showarrow=False,
            font=dict(size=13, color="#555555"),
            xanchor="right",
            yanchor="middle",
            align="right",
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

    annotations.append(dict(
        xref="paper", yref="paper",
        x=0, y=-0.15,
        xanchor="left", yanchor="top",
        text="Source: BFS — Strukturerhebung (Wohnfläche), 2024",
        showarrow=False,
        font=dict(size=9, color="#aaaaaa"),
    ))
    fig.update_layout(
        height=340,
        margin=dict(t=10, l=10, r=155, b=42),
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
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.01, y=0.005,
        xanchor="left", yanchor="bottom",
        text="Source: BFS — Strukturerhebung (Wohnfläche), 2024",
        showarrow=False,
        font=dict(size=10, color="#777777"),
        bgcolor="rgba(255,255,255,0.85)",
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
            cliponaxis=False,
            hovertemplate=(
                f"<b>{GENERATION_YEAR_LABELS.get(gen, gen)}</b><br>"
                f"Ownership: <b>{row['pct']:.1f}%</b><br>"
                f"Living space: <b>{row['sqm_per_person']:.1f} m² per person</b>"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Inline label on the trend line at ~70% along x range
    x_label = x.min() + (x.max() - x.min()) * 0.68
    y_label = float(np.polyval(coeffs, x_label))
    fig.add_annotation(
        x=x_label, y=y_label,
        text=f"Higher ownership → more space<br><span style='font-size:11px;color:#999999'>r = {r:.2f} (strong positive correlation)</span>",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        yshift=8,
        font=dict(size=12, color="#555555", family="sans-serif"),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="rgba(0,0,0,0.08)",
        borderwidth=1,
        borderpad=5,
    )

    fig.update_layout(
        height=320,
        margin=dict(t=40, l=10, r=20, b=52),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            title=dict(text="Ownership Rate (%)", font=dict(size=14, color="#111111")),
            ticksuffix="%",
            tickfont=dict(size=13, color="#111111"),
            gridcolor="#e8e8e8",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="m² per Person", font=dict(size=14, color="#111111")),
            ticksuffix=" m²",
            tickfont=dict(size=13, color="#111111"),
            gridcolor="#e8e8e8",
            zeroline=False,
            range=[20, 90],
        ),
        showlegend=False,
    )
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0, y=-0.14,
        xanchor="left", yanchor="top",
        text="Source: BFS — Strukturerhebung (Bewohnertyp & Wohnfläche), 2024",
        showarrow=False,
        font=dict(size=9, color="#aaaaaa"),
    )
    return fig


def render_who_owns_section(
    bewohnertyp_df: pd.DataFrame,
    wohnflaeche_df: pd.DataFrame,
) -> None:
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
    max_gen = max_row["generation"] if max_row is not None else "—"
    min_gen = min_row["generation"] if min_row is not None else "—"
    max_pct = round(max_row["pct"]) if max_row is not None else 0
    min_pct = round(min_row["pct"]) if min_row is not None else 0
    # Compute gap from the rounded values so it stays consistent with the displayed percentages
    gap = max_pct - min_pct

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(f"### A {gap}% Ownership Gap: {max_gen} vs. {min_gen}")

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

    # Per-generation ownership % for the explanatory narrative (fallback to typical 2024 values)
    _silent_row = eig[eig["generation"] == "Silent Generation"]
    _genz_row   = eig[eig["generation"] == "Generation Z"]
    _silent_pct = round(float(_silent_row["pct"].iloc[0])) if not _silent_row.empty else 55
    _genz_pct   = round(float(_genz_row["pct"].iloc[0]))   if not _genz_row.empty   else 39

    # Generation colors for inline highlights (consistent with intro paragraph)
    _sc  = GENERATION_COLORS.get("Silent Generation",   "#0f4c5c")
    _gxc = GENERATION_COLORS.get("Generation X",        "#679289")
    _gzc = GENERATION_COLORS.get("Generation Z",        "#f25c54")

    st.markdown(
        f"""
        <div class="narrative-text">
        <p style="margin:0 0 0.9rem;">
        Ownership in Switzerland declines steadily across younger generations — but the ranking
        holds two surprises worth flagging.
        <span style="color:{_bc};font-weight:700;">Babyboomers</span>
        (<span style="color:{_bc};font-weight:700;">{_boomer_pct}%</span>) actually edge out the
        <span style="color:{_sc};font-weight:700;">Silent Generation</span>
        (<span style="color:{_sc};font-weight:700;">{_silent_pct}%</span>), partly because many
        over-79s have already transferred property to their children, and partly because a
        significant share live in care homes or other collective households — which the Structural
        Survey excludes by design — leaving the
        <span style="color:{_sc};font-weight:700;">Silent Generation's</span> true ownership rate
        likely understated. At the other end,
        <span style="color:{_mc};font-weight:700;">Millennials</span>
        (<span style="color:{_mc};font-weight:700;">{_milli_pct}%</span>) sit lowest of all, caught
        in a structural sandwich: too old to still benefit from parental housing, too young to have
        accumulated capital, and entering the market precisely when prices peaked. Rising property
        prices, stagnating entry-level wages, and intensifying competition in Swiss city housing
        markets have made renting not a lifestyle choice, but increasingly the only option for
        younger people. As housing costs continue to grow faster than incomes, the generational
        wealth gap is set to widen further.
        </p>
        <p style="margin:0 0 0.9rem;">
        This dynamic plays out at the household level too.
        <span style="color:{_gzc};font-weight:700;">Generation Z</span> adults are staying in their
        parents' homes — typically
        <span style="color:{_gxc};font-weight:700;">Generation X</span> households — far longer
        than previous generations did. That also explains the chart's other puzzle:
        <span style="color:{_gzc};font-weight:700;">Gen Z</span>
        (<span style="color:{_gzc};font-weight:700;">{_genz_pct}%</span>) appears to "own" more
        than <span style="color:{_mc};font-weight:700;">Millennials</span>
        (<span style="color:{_mc};font-weight:700;">{_milli_pct}%</span>), but only because the
        survey records household-level tenure, not individual ownership — a young adult still
        living in an owner-occupied parental home is counted within an owner household, inflating
        <span style="color:{_gzc};font-weight:700;">Gen Z's</span> apparent rate. According to the
        Federal Housing Office (BWO) and Wüest Partner, advertised rents rose by over 15% between
        2019 and 2024 while real wages for new entrants stagnated.
        </p>
        <p style="margin:0 0 0.9rem;">
        FSO Structural Survey data confirms that the share of 18–30-year-olds in parental households
        rose continuously between 2010 and 2022 — and those who do leave often end up in shared
        apartments well into their thirties. This reflects structural exclusion from the housing
        market, not personal preference — and it connects directly to the "Who pays?" question at
        the heart of this project: those who rent pay a growing share of their income for housing,
        while those who own accumulate wealth and, arguably, political leverage.
        </p>
        <p style="margin:0;font-size:0.9rem;color:#777777;font-style:italic;
        border-left:3px solid #d9e3e0;padding:0.4rem 0.8rem;">
        Note: These figures reflect household-level tenure status, not individual ownership —
        results for the youngest and oldest generations should be interpreted with this in mind.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Living space section ──────────────────────────────────────────────────
    st.markdown("<div style='border-top:1px solid #eeeeee;margin:1.5rem 0 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("### Older Generations Live in Twice the Space — The Gap Is Not Closing")

    year_wf_sel = int(st.session_state.get("whoowns_year_wf", str(_avail_years[-1])))
    year_wf = wf_data[wf_data["year"] == year_wf_sel]

    wf_max_row = year_wf.loc[year_wf["sqm_per_person"].idxmax()] if not year_wf.empty else None
    wf_min_row = year_wf.loc[year_wf["sqm_per_person"].idxmin()] if not year_wf.empty else None
    wf_max_gen = wf_max_row["generation"] if wf_max_row is not None else "—"
    wf_min_gen = wf_min_row["generation"] if wf_min_row is not None else "—"
    wf_max_val = wf_max_row["sqm_per_person"] if wf_max_row is not None else 0.0
    wf_min_val = wf_min_row["sqm_per_person"] if wf_min_row is not None else 0.0
    wf_gap = wf_max_val - wf_min_val

    # Per-generation m²/person for the explanatory narrative (fallback to typical 2024 values)
    def _wf_lookup(gen: str, fallback: float) -> float:
        row = year_wf[year_wf["generation"] == gen]
        return float(row["sqm_per_person"].iloc[0]) if not row.empty else fallback

    _silent_m2 = _wf_lookup("Silent Generation",   65.8)
    _boomer_m2 = _wf_lookup("Babyboomers",         56.8)
    _genx_m2   = _wf_lookup("Generation X",        47.0)
    _milli_m2  = _wf_lookup("Millennials / Gen Y", 34.8)
    _genz_m2   = _wf_lookup("Generation Z",        32.6)

    st.markdown(
        f"""
        <p style="font-size:1.05rem;line-height:1.8;color:#333333;margin-bottom:1.4rem;">
        Space, like ownership, is not distributed equally across generations in Switzerland. The
        same structural forces that push younger generations into renting also compress the amount
        of living space they can afford. The
        <span style="color:{_sc};font-weight:700;">Silent Generation</span> enjoys an average of
        <span style="color:{_sc};font-weight:700;">{_silent_m2:.1f}&nbsp;m²</span> per person,
        while <span style="color:{_gzc};font-weight:700;">Generation Z</span> has just
        <span style="color:{_gzc};font-weight:700;">{_genz_m2:.1f}&nbsp;m²</span>&nbsp;— barely
        half. And unlike many inequalities, this gap has not narrowed at all over the past six years.
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
    st.markdown(
        f"""
        <div class="narrative-text">
        <p style="margin:0 0 0.9rem;">
        The ranking has held completely stable across all {len(all_years)} years — no generation
        overtook another, and the gap between top and bottom remained fixed at roughly
        <strong>+{wf_gap:.0f}&nbsp;m²</strong>. But the chart contains two patterns that deserve
        explanation.
        </p>
        <p style="margin:0 0 0.9rem;">
        Why does the <span style="color:{_sc};font-weight:700;">Silent Generation</span>
        (<span style="color:{_sc};font-weight:700;">{_silent_m2:.1f}&nbsp;m²</span>) rank above
        <span style="color:{_bc};font-weight:700;">Babyboomers</span>
        (<span style="color:{_bc};font-weight:700;">{_boomer_m2:.1f}&nbsp;m²</span>), despite being
        older? Many people aged 79+ continue living in the same owner-occupied home they bought
        decades ago — a home that may have housed a full family, but now shelters one or two
        people. As children leave and floor space stays constant, m² per person rises. This is the
        "empty nest" effect at its most visible. There is also a methodological dimension: those
        who move into care homes or assisted living are excluded from the Structural Survey
        entirely, leaving only those still in large private dwellings — which systematically skews
        the <span style="color:{_sc};font-weight:700;">Silent Generation's</span> average upward.
        </p>
        <p style="margin:0 0 0.9rem;">
        Why does <span style="color:{_gzc};font-weight:700;">Generation Z</span>
        (<span style="color:{_gzc};font-weight:700;">{_genz_m2:.1f}&nbsp;m²</span>) rank below
        <span style="color:{_mc};font-weight:700;">Millennials</span>
        (<span style="color:{_mc};font-weight:700;">{_milli_m2:.1f}&nbsp;m²</span>), despite often
        living in parental homes? Large parental homes are shared among more people — two parents
        plus one or more adult children. The m² per person figure therefore shrinks even in
        spacious owner-occupied properties. This mirrors the ownership distortion seen in the
        previous chart: <span style="color:{_gzc};font-weight:700;">Gen Z's</span> housing
        situation looks better than it is in ownership terms, and worse than it is in space
        terms — both as artefacts of the same household-level measurement.
        </p>
        <p style="margin:0 0 0.9rem;">
        The connection to the ownership section is direct: renters — disproportionately
        <span style="color:{_mc};font-weight:700;">Millennials</span> and
        <span style="color:{_gzc};font-weight:700;">Gen Z</span> — occupy smaller dwellings by
        necessity, not choice. Rental apartments in Swiss cities average significantly less floor
        space than owner-occupied homes, and competition for larger units is intense. As long as
        the ownership gap persists, so will the space gap.
        </p>
        <p style="margin:0;font-size:0.9rem;color:#777777;font-style:italic;
        border-left:3px solid #d9e3e0;padding:0.4rem 0.8rem;">
        Note: These figures reflect household-level averages from the FSO Structural Survey, which
        covers only persons in private households aged 15+. Persons in collective households
        (e.g. care homes) are excluded — results for the
        <span style="font-style:normal;color:{_sc};font-weight:700;">Silent Generation</span> in
        particular should be interpreted with this in mind.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Scatter: ownership rate vs. living space ──────────────────────────────
    st.markdown("<div style='border-top:1px solid #eeeeee;margin:1.5rem 0 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("### Ownership Rate vs. Living Space: A Persistent Correlation")

    year_scatter = int(st.session_state.get("whoowns_year_scatter", str(_avail_years[-1])))

    # Pre-load scatter data once + compute live Pearson r for the narrative text
    scatter_occ, _ = build_occupancy_stacked_data(bewohnertyp_df, year_scatter, GENERATION_ORDER)
    scatter_wf = build_wohnflaeche_data(wohnflaeche_df, GENERATION_ORDER)
    _yr_wf  = scatter_wf[scatter_wf["year"] == year_scatter][["generation", "sqm_per_person"]]
    _yr_occ = scatter_occ[scatter_occ["bewohnertyp"] == "Eigentümer"][["generation", "pct"]]
    _scatter_merged = _yr_wf.merge(_yr_occ, on="generation")
    if len(_scatter_merged) >= 2:
        _r_val = float(np.corrcoef(
            _scatter_merged["pct"].values, _scatter_merged["sqm_per_person"].values
        )[0, 1])
    else:
        _r_val = 0.82
    _r2_val = _r_val ** 2
    _r2_pct = round(_r2_val * 100)

    st.markdown(
        f"""
        <p style="font-size:1.05rem;line-height:1.8;color:#333333;margin-bottom:1.4rem;">
        This chart brings together the two patterns explored above: ownership rate and living space
        per person, plotted for each generation. The correlation is striking —
        <strong>r&nbsp;=&nbsp;{_r_val:.2f} (r²&nbsp;=&nbsp;{_r2_val:.2f})</strong> — meaning that
        roughly <strong>{_r2_pct}%</strong> of the variation in living space across generations can
        be statistically explained by differences in ownership rate alone
        (r² = coefficient of determination).
        <span style="color:{_bc};font-weight:700;">Generations that own more, live in more space.</span>
        This is not coincidental: owner-occupied homes in Switzerland are on average significantly
        larger than rental apartments, and access to ownership is itself shaped by income, wealth,
        and the era in which a generation entered the housing market.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.plotly_chart(
        create_space_ownership_scatter(scatter_wf, scatter_occ, year_scatter, GENERATION_ORDER),
        use_container_width=True,
    )
    _year_radio("Filter by Year", "whoowns_year_scatter")

    # ── Closing block: Conclusion (styled like the trend-text boxes) ─────────
    st.markdown(
        "<div style='font-size:0.85rem;text-transform:uppercase;letter-spacing:0.1em;"
        "color:#aaaaaa;margin:0.8rem 0 0.5rem;'>Conclusion: A self-reinforcing divide</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="narrative-text">
        <p style="margin:0 0 0.9rem;">
        Taken together, the three charts in this section tell a coherent story. Older generations —
        <span style="color:{_bc};font-weight:700;">Babyboomers</span> and the
        <span style="color:{_sc};font-weight:700;">Silent Generation</span> — entered the housing
        market during an era of accessible prices and have since accumulated both property and
        space. Younger generations —
        <span style="color:{_mc};font-weight:700;">Millennials</span> and
        <span style="color:{_gzc};font-weight:700;">Generation Z</span> — face structural barriers
        that make ownership increasingly out of reach, and they live in correspondingly smaller,
        more expensive conditions relative to their income.
        </p>
        <p style="margin:0 0 0.9rem;">
        <span style="color:{_gzc};font-weight:700;">Gen&nbsp;Z's</span> ownership rate appears
        relatively high (<span style="color:{_gzc};font-weight:700;">{_genz_pct}%</span>) because
        many still live in owner-occupied parental homes — but with more people sharing the same
        space, their m² per person remains the lowest after
        <span style="color:{_mc};font-weight:700;">Millennials</span>. This is the same
        household-level measurement artefact visible across all three charts in this section.
        </p>
        <p style="margin:0 0 0.9rem;">
        The correlation between ownership and living space
        (<strong>r&nbsp;=&nbsp;{_r_val:.2f}</strong>) shows these are not independent inequalities —
        they reinforce each other. Those who own accumulate wealth through rising property values;
        those who rent pay a growing share of their income for less space and build no equity. The
        gap is not narrowing. And as Swiss housing prices continue to rise faster than wages, the
        prospect of younger cohorts closing it through future ownership becomes increasingly
        uncertain.
        </p>
        <p style="margin:0;font-size:0.9rem;color:#777777;font-style:italic;
        border-left:3px solid #d9e3e0;padding:0.4rem 0.8rem;">
        Note: All figures are based on FSO Structural Survey data (2019–2024), which covers
        persons aged 15+ in private households only. Persons in collective households — including
        care homes — are excluded. Ownership figures reflect household-level tenure status, not
        individual ownership.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Data & Methodological Limitations (collapsible) ──────────────────────
    st.markdown(
        """
        <style>
            details.limitations > summary { list-style: none; cursor: pointer; }
            details.limitations > summary::-webkit-details-marker { display: none; }
            details.limitations > summary::marker { display: none; }
        </style>
        <details class="limitations" style="border-bottom:1px solid #eeeeee;margin-bottom:1.6rem;
        padding-top:0.9rem;">
            <summary style="font-size:0.85rem;font-weight:600;color:#666666;
            letter-spacing:0.02em;outline:none;">
                Data Limitations ▾
            </summary>
            <div style="font-size:0.78rem;line-height:1.6;color:#888888;
            margin-top:0.7rem;">
                The structural survey covers persons aged 15 and older living in private households
                within the permanent resident population. Not included are persons living in
                collective households, diplomats, international officials, and their dependants.
                The resident type refers to the household occupying the dwelling. "Other situation"
                includes dwellings provided free of charge by a relative or employer
                (e.g. caretaker apartments) and tenants of agricultural land.             
            </div>
        </details>
        """,
        unsafe_allow_html=True,
    )