from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import chi2_contingency, f_oneway

from app_config import GENERATION_COLORS as GEN_COLORS, GENERATION_ORDER

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[1]

SELECTS_2015_PATH = BASE_DIR / "data" / "whodecide" / "raw" / "726_Selects2015_PES_Data_v1.03.dta"
SELECTS_2015_PATH_CSV = BASE_DIR / "data" / "whodecide" / "processed" / "selects_2015_clean.csv"
SELECTS_2019_PATH = BASE_DIR / "data" / "whodecide" / "processed" / "selects_2019_clean.csv"
SELECTS_2023_PATH = BASE_DIR / "data" / "whodecide" / "processed" / "selects_2023_clean.csv"

# ─────────────────────────────────────────────
# Shared chart style helpers
# ─────────────────────────────────────────────

_FONT = dict(family="Inter, Arial, sans-serif", size=12, color="#111111")
_AXIS = dict(tickfont=dict(size=11, color="#555555"), gridcolor="#eeeeee", linecolor="#dddddd")

def _base_layout(**kwargs) -> dict:
    return dict(
        font=_FONT,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=11, color="#333333"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        margin=dict(t=40, b=40, l=50, r=20),
        height=340,
        **kwargs,
    )

CHART_NARRATIVE = {
    "turnout": {
        "title": "Who Shows Up at the Ballot Box?",
        "intro": (
            "Voter turnout reveals which generations actively shape political outcomes. "
            "While older generations vote consistently, younger cohorts have shown a worrying decline — "
            "especially after 2019."
        ),
        "insight": (
            "Babyboomers & Generation X remain stable across all three election years. "
            "Millennials / Gen Y and Generation Z show a significant drop from 2019 to 2023. "
            "The Silent Generation also declined — likely due to demographic factors."
        ),
    },
    "interest": {
        "title": "Does Political Interest Drive Participation?",
        "intro": (
            "Political interest has been rising across almost all generations since 2019. "
            "Yet this increased interest has not translated into higher voter turnout — a striking paradox."
        ),
        "insight": (
            "Interest surged strongly for Silent Generation through Millennials between 2019 and 2023. "
            "Generation Z shows no clear trend. "
            "This disconnect between rising interest and falling turnout points to deeper structural factors."
        ),
    },
    "trust": {
        "title": "Does Institutional Trust Explain the Gap?",
        "intro": (
            "Democratic satisfaction across three elections (2015, 2019, 2023) — "
            "a line going up means more satisfied, down means less. "
            "The badge shows the net change from 2015 to 2023."
        ),
        "insight": (
            "No consistent trend across generations — most dip in 2019 before diverging by 2023. "
            "Millennials are the only generation with rising satisfaction over the full period. "
            "Gen Z and Silent Generation lost the most ground."
        ),
    },
    "lr": {
        "title": "Same Views, Different Turnout?",
        "intro": (
            "If generations vote differently, is it because they think differently? "
            "We compare political orientation across generations — from left (1) to right (5)."
        ),
        "insight": (
            "All generations cluster between 2.3 and 2.6 — barely distinguishable on the spectrum. "
            "Political orientation does not explain the turnout gap. "
            "Young and old share similar views, yet older generations show up to vote far more consistently."
        ),
    },
}


# ─────────────────────────────────────────────
# Data loading & preparation
# ─────────────────────────────────────────────

def _assign_generation(year: float) -> str:
    if pd.isna(year):
        return "Unknown"
    if year <= 1945:
        return "Silent Generation"
    if year <= 1964:
        return "Babyboomers"
    if year <= 1980:
        return "Generation X"
    if year <= 1996:
        return "Millennials / Gen Y"
    return "Generation Z"


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df[pd.to_numeric(df["f11100rec"], errors="coerce") >= 0].copy()
    df["generation"] = df["birthyear"].apply(_assign_generation)
    df["voted"] = pd.to_numeric(df["f11100rec"], errors="coerce")
    df["political_interest"] = pd.to_numeric(df["f10100"], errors="coerce").replace([-99, -98, 9], np.nan)
    for col in ["f11301", "f11302", "f11305"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").replace([-99, -98], np.nan)
    df["trust_avg"] = df[["f11301", "f11302", "f11305"]].mean(axis=1)
    df["demo_satisfaction"] = (
        pd.to_numeric(df["f12010"], errors="coerce")
        .replace([-99, -98, 8, 9], np.nan)
        .map({1: 1, 2: 0})
    )
    lr_col = "f12900rec" if "f12900rec" in df.columns else "f12900"
    if "f12900rec" in df.columns:
    # 2019/2023: Werte 10,20,30,40,50 → 1–5
        raw = pd.to_numeric(df["f12900rec"], errors="coerce").replace([-99, -98], np.nan)
        df["lr_scale"] = raw.where(raw.isin([10, 20, 30, 40, 50])).div(10)
    elif "f12900main7" in df.columns:
    # 2015: Werte 1–7 → auf 1–5 mappen
        raw = pd.to_numeric(df["f12900main7"], errors="coerce").replace([-99, -98, 8, 9], np.nan)
        df["lr_scale"] = raw.where(raw.between(1, 7)).map(
        {1: 1.0, 2: 1.5, 3: 2.5, 4: 3.0, 5: 3.5, 6: 4.5, 7: 5.0}
    )
    else:
        df["lr_scale"] = np.nan
    return df


@st.cache_data
def _load_frames() -> dict[int, pd.DataFrame]:
    frames = {}

    # 2015 — Stata
    # 2015 — processed CSV
    df15 = pd.read_csv(SELECTS_2015_PATH_CSV, sep=None, engine="python")
    df15.columns = df15.columns.str.lower().str.strip()
    df15["f11100rec"] = pd.to_numeric(df15["f11100r"], errors="coerce").map({1.0: 1, 0.0: 0})
    frames[2015] = _prepare(df15)

    # 2019 — processed CSV
    df19 = pd.read_csv(SELECTS_2019_PATH, sep=None, engine="python")
    df19.columns = df19.columns.str.lower().str.strip()
    frames[2019] = _prepare(df19)

    # 2023 — processed CSV
    df23 = pd.read_csv(SELECTS_2023_PATH, sep=None, engine="python")
    df23.columns = df23.columns.str.lower().str.strip()
    frames[2023] = _prepare(df23)

    return frames


def _agg(frames: dict, metric: str, gen: str) -> dict:
    result = {}
    for year, df in frames.items():
        subset = df[df["generation"] == gen][metric].dropna()
        if len(subset) > 0:
            result[year] = subset.mean()
    return result


# ─────────────────────────────────────────────
# Chart 1 — Dot + Range
# ─────────────────────────────────────────────

def _chart_dot_range(frames: dict, selected_gens: list[str]) -> go.Figure:
    fig = go.Figure()
    for gen in selected_gens:
        color = GEN_COLORS[gen]
        vals = _agg(frames, "voted", gen)
        years = sorted(vals.keys())
        y_vals = [vals[y] * 100 for y in years]

        fig.add_trace(go.Scatter(
            x=years, y=y_vals, mode="lines",
            line=dict(color=color, width=1.5), opacity=0.35,
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=years, y=y_vals, mode="markers+text",
            name=gen, marker=dict(color=color, size=10),
            text=[f"{v:.1f}%" for v in y_vals],
            textposition="top center",
            textfont=dict(size=10, color=color),
        ))

    fig.update_layout(**_base_layout(
        yaxis=dict(range=[30, 105], title="Share voted (%)", **_AXIS),
        xaxis=dict(tickvals=[2015, 2019, 2023], **_AXIS),
    ))
    return fig


# ─────────────────────────────────────────────
# Chart 1b — Parliament / Semicircle Chart
# ─────────────────────────────────────────────

def _chart_parliament(frames: dict, selected_gens: list[str], year: int) -> go.Figure:
    import math

    # Left = youngest (Gen Z), right = oldest (Silent) — reversed GENERATION_ORDER
    display_order = [g for g in reversed(GENERATION_ORDER) if g in selected_gens]

    df = frames[year]
    voters = df[df["voted"] == 1]

    counts = {g: int((voters["generation"] == g).sum()) for g in display_order}
    total = sum(counts.values()) or 1

    TOTAL_SEATS = 200
    seats: dict[str, int] = {}
    assigned = 0
    for i, g in enumerate(display_order):
        if i == len(display_order) - 1:
            seats[g] = max(1, TOTAL_SEATS - assigned)
        else:
            s = max(1, round(counts[g] / total * TOTAL_SEATS))
            seats[g] = s
            assigned += s

    ROW_FRACTIONS = [0.10, 0.13, 0.16, 0.18, 0.20, 0.23]
    total_frac = sum(ROW_FRACTIONS)
    seats_per_row = [max(8, round(f / total_frac * TOTAL_SEATS)) for f in ROW_FRACTIONS]
    seats_per_row[-1] += TOTAL_SEATS - sum(seats_per_row)

    seat_x, seat_y, seat_colors, seat_labels = [], [], [], []

    for row_i, n_seats in enumerate(seats_per_row):
        r = 0.35 + row_i * 0.11
        # Distribute gens proportionally across this row
        row_seats: list[str] = []
        row_assigned = 0
        for k, g in enumerate(display_order):
            if k == len(display_order) - 1:
                cnt = max(0, n_seats - row_assigned)
            else:
                cnt = max(0, round(seats[g] / TOTAL_SEATS * n_seats))
                row_assigned += cnt
            row_seats.extend([g] * cnt)

        for s, g in enumerate(row_seats):
            angle = math.pi - math.pi * s / max(len(row_seats) - 1, 1)
            seat_x.append(r * math.cos(angle))
            seat_y.append(r * math.sin(angle))
            seat_colors.append(GEN_COLORS.get(g, "#cccccc"))
            seat_labels.append(g)

    fig = go.Figure()
    added: set[str] = set()
    for i, g in enumerate(seat_labels):
        fig.add_trace(go.Scatter(
            x=[seat_x[i]], y=[seat_y[i]],
            mode="markers",
            name=g,
            legendgroup=g,
            showlegend=(g not in added),
            marker=dict(
                color=seat_colors[i], size=12, symbol="square",
                line=dict(color="#ffffff", width=1.5),
            ),
            hovertemplate=(
                f"<b>{g}</b><br>"
                f"{seats.get(g, 0)} seats<br>"
                f"{counts.get(g, 0):,} voters ({counts.get(g,0)/total*100:.1f}%)"
                "<extra></extra>"
            ),
        ))
        added.add(g)

    # % labels along the bottom arc
    for k, g in enumerate(display_order):
        pct = counts[g] / total * 100
        angle = math.pi - math.pi * (
            sum(seats[dg] for dg in display_order[:k]) + seats[g] / 2
        ) / TOTAL_SEATS
        lx = 1.08 * math.cos(angle)
        ly = 1.08 * math.sin(angle)
        short = {"Silent Generation": "Silent", "Babyboomers": "Boomers",
                 "Generation X": "Gen X", "Millennials / Gen Y": "Millennials",
                 "Generation Z": "Gen Z"}.get(g, g)
        fig.add_annotation(
            x=lx, y=ly,
            text=f"<b>{short}</b><br>{pct:.1f}%",
            showarrow=False,
            font=dict(size=10, color=GEN_COLORS.get(g, "#333333"), family="Inter, Arial, sans-serif"),
            xanchor="center",
        )

    fig.update_layout(
        height=420,
        margin=dict(t=10, b=20, l=10, r=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(visible=False, range=[-1.25, 1.25]),
        yaxis=dict(visible=False, range=[-0.25, 1.15], scaleanchor="x", scaleratio=1),
        showlegend=False,
        legend=dict(
            orientation="h", yanchor="top", y=-0.02,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#333333", family="Inter, Arial, sans-serif"),
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
        ),
    )
    return fig


# ─────────────────────────────────────────────
# Chart 2 — Line Chart
# ─────────────────────────────────────────────

def _chart_line(frames: dict, selected_gens: list[str]) -> go.Figure:
    import math

    # Compute ranks per year
    years = [2015, 2019, 2023]
    vals_all = {}
    for gen in selected_gens:
        v = _agg(frames, "political_interest", gen)
        vals_all[gen] = v

    ranks = {}
    for y in years:
        scores = {g: vals_all[g].get(y, 0) for g in selected_gens}
        sorted_gens = sorted(scores, key=lambda g: scores[g], reverse=True)
        for g in selected_gens:
            if g not in ranks:
                ranks[g] = {}
            ranks[g][y] = sorted_gens.index(g) + 1

    n = len(selected_gens)
    fig = go.Figure()

    short = {
        "Silent Generation": "Silent",
        "Babyboomers": "Boomers",
        "Generation X": "Gen X",
        "Millennials / Gen Y": "Millennials",
        "Generation Z": "Gen Z",
    }

    for gen in selected_gens:
        color = GEN_COLORS[gen]
        x_vals = years
        y_vals = [ranks[gen][y] for y in years]

        # Smooth cubic bezier via many points
        smooth_x, smooth_y = [], []
        for i in range(len(x_vals) - 1):
            for t in [k / 30 for k in range(31)]:
                mx = (x_vals[i] + x_vals[i+1]) / 2
                bx = x_vals[i] + t * (x_vals[i+1] - x_vals[i])
                by = y_vals[i] + (3*t**2 - 2*t**3) * (y_vals[i+1] - y_vals[i])
                smooth_x.append(bx)
                smooth_y.append(by)

        fig.add_trace(go.Scatter(
            x=smooth_x, y=smooth_y,
            mode="lines",
            name=gen,
            line=dict(color=color, width=2.5),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Dots with rank number
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="markers+text",
            name=gen,
            marker=dict(color=color, size=22, symbol="circle",
                        line=dict(color="white", width=2)),
            text=[str(r) for r in y_vals],
            textposition="middle center",
            textfont=dict(size=10, color="white", family="Inter, Arial, sans-serif"),
            hovertemplate=f"<b>{gen}</b><br>Rang %{{y}} · %{{x}}<extra></extra>",
        ))

        # Left label
        fig.add_annotation(
            x=2015, y=ranks[gen][2015],
            text=f"<b>{short.get(gen, gen)}</b>",
            xanchor="right", xshift=-18,
            showarrow=False,
            font=dict(size=11, color=color, family="Inter, Arial, sans-serif"),
        )
        # Right label
        fig.add_annotation(
            x=2023, y=ranks[gen][2023],
            text=f"<b>{short.get(gen, gen)}</b>",
            xanchor="left", xshift=18,
            showarrow=False,
            font=dict(size=11, color=color, family="Inter, Arial, sans-serif"),
        )

    fig.update_layout(**_base_layout(
        yaxis=dict(
            range=[n + 0.6, 0.4],
            tickvals=list(range(1, n + 1)),
            ticktext=[f"#{i}" for i in range(1, n + 1)],
            title="1 = highest Interest",
            **_AXIS,
        ),
        xaxis=dict(tickvals=[2015, 2019, 2023], **_AXIS),
        showlegend=False,
    ))
    return fig


# ─────────────────────────────────────────────
# Chart 3 — Slope Chart (2015 vs 2023)
# ─────────────────────────────────────────────

def _chart_slope(frames: dict, selected_gens: list[str]) -> list:
    """Returns list of (gen, fig, v2023, diff) for small multiples."""
    results = []
    for gen in selected_gens:
        color = GEN_COLORS[gen]
        vals = _agg(frames, "demo_satisfaction", gen)
        if 2015 not in vals or 2023 not in vals:
            continue
        years = [y for y in [2015, 2019, 2023] if y in vals]
        y_vals = [vals[y] * 100 for y in years]
        v15 = vals[2015] * 100
        v23 = vals[2023] * 100
        diff = v23 - v15

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=y_vals,
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(color=color, size=6),
            fill="tozeroy",
            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
            hovertemplate=f"%{{x}}: %{{y:.1f}}%<extra></extra>",
            showlegend=False,
        ))
        fig.update_layout(
            height=130,
            margin=dict(t=8, b=24, l=8, r=16),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(tickvals=years, ticktext=[str(y) for y in years],
                tickfont=dict(size=9, color="#aaa"), gridcolor="#f0f0f0",
                linecolor="#eeeeee", showgrid=False, range=[2014, 2024.5],),
            yaxis=dict(range=[35, 65], showticklabels=False,
                       gridcolor="#f5f5f5", linecolor="#eeeeee"),
        )
        results.append((gen, fig, v23, diff))
    return results


# ─────────────────────────────────────────────
# Chart 4 — Grouped Bar (L-R orientation)
# ─────────────────────────────────────────────
def _chart_bar_lr(frames: dict, selected_gens: list[str]) -> go.Figure:
    import math
    fig = go.Figure()

    short = {
        "Silent Generation":   "Silent",
        "Babyboomers":         "Boomers",
        "Generation X":        "Gen X",
        "Millennials / Gen Y": "Millennials",
        "Generation Z":        "Gen Z",
    }

    for gen in selected_gens:
        color = GEN_COLORS[gen]
        vals = _agg(frames, "lr_scale", gen)
        if 2015 not in vals or 2023 not in vals:
            continue

        v15 = vals[2015]
        v19 = vals.get(2019)
        v23 = vals[2023]
        diff = v23 - v15

        # ── Arrow line 2015 → 2023 ──
        fig.add_trace(go.Scatter(
            x=[v15, v23], y=[gen, gen],
            mode="lines",
            line=dict(color=color, width=2),
            showlegend=False,
            hoverinfo="skip",
        ))

        # ── 2015 open circle ──
        fig.add_trace(go.Scatter(
            x=[v15], y=[gen],
            mode="markers",
            name=gen,
            marker=dict(
                color="white", size=10, symbol="circle",
                line=dict(color=color, width=2),
            ),
            hovertemplate=f"<b>{gen}</b><br>2015: {v15:.2f}<extra></extra>",
            showlegend=True,
        ))

        # ── 2019 mid dot ──
        if v19 is not None:
            fig.add_trace(go.Scatter(
                x=[v19], y=[gen],
                mode="markers",
                marker=dict(color=color, size=7, opacity=0.5),
                showlegend=False,
                hovertemplate=f"<b>{gen}</b><br>2019: {v19:.2f}<extra></extra>",
            ))

        # ── 2023 filled circle (arrowhead effect) ──
        fig.add_trace(go.Scatter(
            x=[v23], y=[gen],
            mode="markers+text",
            marker=dict(color=color, size=14,
                        line=dict(color="white", width=2)),
            text=[f"{v23:.1f}"],
            textposition="middle right",
            textfont=dict(size=10, color=color),
            showlegend=False,
            hovertemplate=f"<b>{gen}</b><br>2023: {v23:.2f}<br>Δ {diff:+.2f}<extra></extra>",
        ))

        # ── Delta annotation on the right ──
        fig.add_annotation(
            x=8.2, y=gen,
            text=f"{'→ +' if diff > 0.05 else '→ '}{abs(diff):.1f}",
            showarrow=False,
            font=dict(size=10, color=color),
            bgcolor=f"rgba({','.join(str(int(int(color.lstrip('#')[i:i+2],16))) for i in (0,2,4))},0.12)",
            borderpad=3,
            xanchor="left",
        )

    # Centre line
    fig.add_vline(x=3, line_dash="dot", line_color="#cccccc",
        annotation_text="Mitte (3)", annotation_position="top")

    fig.update_layout(**_base_layout(
        xaxis=dict(range=[1, 5], title="Ø L–R Skala (1=links, 5=rechts)", **_AXIS),
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(reversed(selected_gens)),
            **_AXIS,
        ),
        showlegend=False,
    ))
    return fig


# ─────────────────────────────────────────────
# Statistical helpers
# ─────────────────────────────────────────────

def _significance_badge(p: float) -> str:
    if p < 0.001:
        return "🔴 p < 0.001"
    if p < 0.01:
        return "🟠 p < 0.01"
    if p < 0.05:
        return "🟡 p < 0.05"
    return "⚪ not significant"


def _stat_turnout(frames: dict, selected_gens: list[str]) -> str:
    rows = []
    years = [2015, 2019, 2023]
    for gen in selected_gens:
        groups = [frames[y][frames[y]["generation"] == gen]["voted"].dropna() for y in years]
        if any(len(g) < 5 for g in groups):
            continue
        combined = pd.concat([pd.Series(g.values) for g in groups])
        labels = pd.concat([pd.Series([str(y)] * len(g)) for y, g in zip(years, groups)])
        ct = pd.crosstab(combined.reset_index(drop=True), labels.reset_index(drop=True))
        if ct.shape[1] < 2:
            continue
        _, p, _, _ = chi2_contingency(ct)
        rows.append(f"**{gen}** {_significance_badge(p)}")
    return "   |   ".join(rows)


def _stat_continuous(frames: dict, metric: str, selected_gens: list[str], years: list[int]) -> str:
    rows = []
    for gen in selected_gens:
        groups = [frames[y][frames[y]["generation"] == gen][metric].dropna() for y in years]
        if any(len(g) < 5 for g in groups):
            continue
        _, p = f_oneway(*groups)
        rows.append(f"**{gen}** {_significance_badge(p)}")
    return "   |   ".join(rows)


# ─────────────────────────────────────────────
# Section renderer — gleiche Signatur wie vorher!
# ─────────────────────────────────────────────

def render_who_decides_section() -> None:
    st.markdown('<div id="who-decides"></div>', unsafe_allow_html=True)

    st.markdown(
    """
    <p style="font-size:1.05rem;line-height:1.7;color:#333333;margin-bottom:1.4rem;">
    Democracy assumes every voice counts equally. 
    But in Switzerland, age tilts the scales. 
    Older generations show up — younger ones stay home. 
    And as the population ages, that gap only widens. 
    From voter turnout to ideological drift,
    the numbers tell a story of who really decides — and who gets left out.
    </p>
    """,
    unsafe_allow_html=True,
)

    # ── Load data ───────────────────────────────────────────────────
    try:
        frames = _load_frames()
    except Exception as exc:
        st.error("Could not load Who Decides data. Check that the processed CSV files exist.")
        st.exception(exc)
        return

    # ── Read shared generation filter from sidebar ──────────────────
    selected_gens: list[str] = st.session_state.get("sidebar_generations", GENERATION_ORDER)

    if len(selected_gens) < 1:
        st.info("Please select at least one generation in the sidebar Control Panel.")
        return

    _CONCLUSION_STYLE = (
        "background:#f5f7f6;border-radius:8px;padding:1.1rem 1.4rem;"
        "margin-top:0.8rem;font-size:1.05rem;line-height:1.75;color:#333333;"
    )


    # ── Chart 1: Parliament — Voter Turnout ─────────────────────────
    st.markdown("---")
    st.markdown(f"### {CHART_NARRATIVE['turnout']['title']}")
    st.markdown(
        f"<p style='font-size:1rem;line-height:1.7;color:#444;'>{CHART_NARRATIVE['turnout']['intro']}</p>",
    unsafe_allow_html=True,
    )
    selected_parl_year = st.session_state.get("wd_parl_year", 2023)
    st.markdown(
        f"<div style='font-size:0.85rem;color:#666666;margin-bottom:0.3rem;'>"
        f"Simulated parliament seats by generation · Federal elections {selected_parl_year}</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _chart_parliament(frames, selected_gens, selected_parl_year),
        use_container_width=True,
    )
    st.radio(
    "Election year",
    options=[2015, 2019, 2023],
    index=[2015, 2019, 2023].index(selected_parl_year),
    horizontal=True,
    key="wd_parl_year",
)
    st.markdown(
        f"<div style='{_CONCLUSION_STYLE}'>"
        "<strong>Who shows up — and who doesn't.</strong> In the 2023 elections, older generations "
        "still dominated the ballot box. Babyboomers and the Silent Generation collectively held the "
        "majority of active votes — not because they are the largest population group, but because "
        "they turn out. Gen Z and Millennials, though growing in numbers, remain structurally "
        "underrepresented at the ballot. Democracy counts votes, not people — and right now, "
        "age decides who gets counted."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Chart 2: Line — Political Interest ──────────────────────────
    st.markdown("---")
    st.markdown(f"### {CHART_NARRATIVE['interest']['title']}")
    st.markdown(
        f"<p style='font-size:1rem;line-height:1.7;color:#444;'>{CHART_NARRATIVE['interest']['intro']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
    "<div style='font-size:0.85rem;color:#666666;margin-bottom:0.3rem;'>"
    "Ranking by average political interest · Elections 2015, 2019, 2023</div>",
    unsafe_allow_html=True,
    )

    st.plotly_chart(_chart_line(frames, selected_gens), use_container_width=True)
    st.markdown(
        f"<div style='{_CONCLUSION_STYLE}'>"
        "<strong>Interested — but absent.</strong> Political interest has risen across nearly every "
        "generation since 2019. Yet at the same ballot, turnout fell. This paradox points to something "
        "deeper than apathy: younger generations care about politics, but something stops them from "
        "converting that interest into a vote. Structural barriers, distrust in the process, or simply "
        "the feeling that it won't make a difference — the data can't tell us which. But the gap between "
        "caring and acting is real, and it widens with every election."
        "</div>",
        unsafe_allow_html=True,
    )

# ── Chart 3: Slope — Democratic Satisfaction ────────────────────
    st.markdown("---")
    st.markdown(f"### {CHART_NARRATIVE['trust']['title']}")
    st.markdown(
        f"<p style='font-size:1rem;line-height:1.7;color:#444;'>{CHART_NARRATIVE['trust']['intro']}</p>",
        unsafe_allow_html=True,
    )
    short_names = {
        "Silent Generation": "Silent", "Babyboomers": "Boomers",
        "Generation X": "Gen X", "Millennials / Gen Y": "Millennials",
        "Generation Z": "Gen Z",
    }
    slope_data = _chart_slope(frames, selected_gens)
    st.markdown(
        "<div style='font-size:0.85rem;color:#666666;margin-bottom:0.3rem;'>"
        "Share satisfied with democracy (%), by generation · Elections 2015, 2019, 2023</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(slope_data))
    for i, (gen, fig, v23, diff) in enumerate(slope_data):
        color = GEN_COLORS[gen]
        arrow = "↑" if diff > 0 else "↓"
        with cols[i]:
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<div style='font-size:13px;font-weight:500;color:{color};'>"
                f"{short_names.get(gen, gen)}</div>"
                f"<div style='font-size:22px;font-weight:500;color:#111;'>"
                f"{v23:.1f}%</div>"
                f"<div style='font-size:13px;color:#111111;margin-bottom:4px;'>"
                f"{arrow} {abs(diff):.1f}% since 2015</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f"<div style='{_CONCLUSION_STYLE}'>"
        "<strong>Trust doesn't explain the gap either.</strong> Democratic satisfaction has moved in "
        "different directions across generations — with no clear generational pattern. Millennials "
        "are the only group whose satisfaction consistently grew over the full period. Gen Z and the "
        "Silent Generation lost the most ground. But crucially: satisfaction levels don't align with "
        "turnout. Generations that trust less don't necessarily vote less. The missing piece lies elsewhere."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Chart 4: Bar — Political Orientation ────────────────────────
    st.markdown("---")
    st.markdown(f"### {CHART_NARRATIVE['lr']['title']}")
    st.markdown(
        f"<p style='font-size:1rem;line-height:1.7;color:#444;'>{CHART_NARRATIVE['lr']['intro']}</p>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(_chart_bar_lr(frames, selected_gens), use_container_width=True)
    st.markdown(
        f"<div style='{_CONCLUSION_STYLE}'>"
        "<strong>Same views, unequal voice.</strong> Across all generations, political orientation "
        "clusters in a surprisingly narrow band — no generation sits firmly left or right. Young and "
        "old think more alike than the political debate suggests. And yet older generations dominate "
        "the ballot box. The turnout gap is not a values gap. It is a participation gap — and in a "
        "direct democracy like Switzerland, that difference shapes every vote, every referendum, "
        "every policy that follows."
        "</div>",
        unsafe_allow_html=True,
    )
