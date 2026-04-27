from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import chi2_contingency, f_oneway

# ─────────────────────────────────────────────
# Constants — müssen mit app_config.py übereinstimmen
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[1]

SELECTS_2015_PATH = BASE_DIR / "data" / "whodecide" / "raw" / "726_Selects2015_PES_Data_v1.03.dta"
SELECTS_2019_PATH = BASE_DIR / "data" / "whodecide" / "processed" / "selects_2019_clean.csv"
SELECTS_2023_PATH = BASE_DIR / "data" / "whodecide" / "processed" / "selects_2023_clean.csv"

GENERATION_ORDER = [
    "Silent Generation",
    "Babyboomers",
    "Generation X",
    "Millennials / Gen Y",
    "Generation Z",
]

GEN_COLORS = {
    "Silent Generation":  "#4C72B0",
    "Babyboomers":        "#DD8452",
    "Generation X":       "#55A868",
    "Millennials / Gen Y":"#9467BD",
    "Generation Z":       "#E377C2",
}

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
            "Democratic satisfaction from 2015 to 2023 — a slope up means more satisfied, "
            "a slope down means less. The badge shows the net change."
        ),
        "insight": (
            "No consistent trend across generations. "
            "Neither trust nor democratic satisfaction fully explains the turnout decline. "
            "Millennials and Gen Z remain consistently more sceptical throughout."
        ),
    },
    "lr": {
        "title": "Is There a Generational Political Shift?",
        "intro": (
            "Beyond participation, we examine whether generations have shifted their political orientation "
            "over time — from left to right on the ideological spectrum (1 = left, 11 = right)."
        ),
        "insight": (
            "Silent Generation and Babyboomers shifted measurably rightward between 2015 and 2019, "
            "and the shift consolidated by 2023. Millennials followed with a slower, gradual drift. "
            "Generation X and Z remained stable. Combined with lower youth turnout, "
            "older and increasingly right-leaning generations are dominating electoral outcomes."
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
    df["lr_scale"] = pd.to_numeric(df[lr_col], errors="coerce").replace([-99, -98], np.nan) / 10
    df["lr_scale"] = df["lr_scale"].where(df["lr_scale"].between(1, 11))
    return df


@st.cache_data
def _load_frames() -> dict[int, pd.DataFrame]:
    frames = {}

    # 2015 — Stata
    df15 = pd.read_stata(SELECTS_2015_PATH, convert_categoricals=False)
    df15.columns = df15.columns.str.lower().str.strip()
    df15["f11100rec"] = df15["f11100r"].map({1.0: 1, 0.0: 0})
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

    fig.update_layout(
        yaxis=dict(range=[30, 105], title="Share voted (%)", gridcolor="#eeeeee"),
        xaxis=dict(tickvals=[2015, 2019, 2023], tickfont=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=40, b=40, l=50, r=20), height=340,
    )
    return fig


# ─────────────────────────────────────────────
# Chart 2 — Line Chart
# ─────────────────────────────────────────────

def _chart_line(frames: dict, selected_gens: list[str]) -> go.Figure:
    fig = go.Figure()
    for gen in selected_gens:
        color = GEN_COLORS[gen]
        vals = _agg(frames, "political_interest", gen)
        years = sorted(vals.keys())
        y_vals = [vals[y] for y in years]

        fig.add_trace(go.Scatter(
            x=years, y=y_vals, mode="lines+markers+text",
            name=gen, line=dict(color=color, width=2),
            marker=dict(color=color, size=8),
            text=[f"{v:.2f}" for v in y_vals],
            textposition="top center",
            textfont=dict(size=10, color=color),
        ))

    fig.update_layout(
        yaxis=dict(range=[1, 4.5], title="Avg. interest (1=low, 4=high)", gridcolor="#eeeeee"),
        xaxis=dict(tickvals=[2015, 2019, 2023], tickfont=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=40, b=40, l=50, r=20), height=340,
    )
    return fig


# ─────────────────────────────────────────────
# Chart 3 — Slope Chart (2015 vs 2023)
# ─────────────────────────────────────────────

def _chart_slope(frames: dict, selected_gens: list[str]) -> go.Figure:
    fig = go.Figure()
    for gen in selected_gens:
        color = GEN_COLORS[gen]
        vals = _agg(frames, "demo_satisfaction", gen)
        if 2015 not in vals or 2023 not in vals:
            continue
        v15 = vals[2015] * 100
        v23 = vals[2023] * 100
        diff = v23 - v15
        badge_color = "#55A868" if diff > 0 else "#DD8452"

        fig.add_trace(go.Scatter(
            x=[2015, 2023], y=[v15, v23],
            mode="lines+markers", name=gen,
            line=dict(color=color, width=2),
            marker=dict(color=color, size=9),
            hovertemplate=f"{gen}<br>2015: {v15:.1f}%<br>2023: {v23:.1f}%<br>Δ {diff:+.1f}%<extra></extra>",
        ))
        fig.add_annotation(x=2015, y=v15, text=f"{v15:.1f}%",
            showarrow=False, xanchor="right", xshift=-8,
            font=dict(size=10, color=color))
        fig.add_annotation(x=2023, y=v23, text=f"{v23:.1f}%",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=10, color=color))
        fig.add_annotation(
            x=2019, y=(v15 + v23) / 2,
            text=f"{diff:+.1f}%", showarrow=False,
            font=dict(size=9, color=badge_color),
            bgcolor="rgba(221,132,82,0.13)" if badge_color == "#DD8452" else "rgba(85,168,104,0.13)", borderpad=3,
        )

    fig.update_layout(
        yaxis=dict(range=[25, 75], title="Share satisfied (%)", gridcolor="#eeeeee"),
        xaxis=dict(tickvals=[2015, 2023], tickfont=dict(size=12), range=[2013, 2025]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=40, b=40, l=50, r=20), height=340,
    )
    return fig


# ─────────────────────────────────────────────
# Chart 4 — Grouped Bar (L-R orientation)
# ─────────────────────────────────────────────

def _chart_bar_lr(frames: dict, selected_gens: list[str]) -> go.Figure:
    fig = go.Figure()
    for gen in selected_gens:
        color = GEN_COLORS[gen]
        vals = _agg(frames, "lr_scale", gen)
        years = sorted(vals.keys())
        y_vals = [vals[y] for y in years]

        fig.add_trace(go.Bar(
            name=gen, x=years, y=y_vals,
            marker_color=color, opacity=0.88,
            text=[f"{v:.2f}" for v in y_vals],
            textposition="outside",
            textfont=dict(size=10),
        ))

    fig.add_hline(y=6, line_dash="dot", line_color="#aaaaaa",
        annotation_text="Centre (6)", annotation_position="top right")

    fig.update_layout(
        barmode="group",
        yaxis=dict(range=[1, 11], title="Avg. L–R scale (1=left, 11=right)", gridcolor="#eeeeee"),
        xaxis=dict(tickvals=[2015, 2019, 2023], tickfont=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=40, b=40, l=50, r=20), height=340,
    )
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
    st.markdown("<div class='section-title'>1. Who Decides</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='narrative-text'>
        Political participation is not evenly distributed across generations.
        This section traces voter turnout, political interest, institutional trust,
        and ideological orientation from 2015 to 2023 — revealing who truly shapes
        Switzerland's political landscape.
        </div>
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

    # ── Generation filter ───────────────────────────────────────────
    st.markdown(
        "<div class='filter-panel'><div class='filter-title'>Compare generations</div></div>",
        unsafe_allow_html=True,
    )
    gen_cols = st.columns(len(GENERATION_ORDER))
    selected_gens = []
    for i, gen in enumerate(GENERATION_ORDER):
        with gen_cols[i]:
            if st.checkbox(gen, value=True, key=f"wd_gen_{i}"):
                selected_gens.append(gen)

    if not selected_gens:
        st.warning("Select at least one generation.")
        return

    # ── Chart 1: Dot + Range — Voter Turnout ────────────────────────
    st.markdown("---")
    col_text, col_chart = st.columns([1, 2])
    with col_text:
        st.markdown(f"### {CHART_NARRATIVE['turnout']['title']}")
        st.markdown(
            f"<div class='narrative-text'>{CHART_NARRATIVE['turnout']['intro']}</div>",
            unsafe_allow_html=True,
        )
    with col_chart:
        st.plotly_chart(_chart_dot_range(frames, selected_gens), use_container_width=True)

    with st.expander("📊 Statistical significance (Chi²-test, 2015–2023)"):
        st.markdown(_stat_turnout(frames, selected_gens) or "—")
        st.caption("Red = highly significant. White = no significant difference.")
    st.markdown(
        f"<div class='narrative-text'>{CHART_NARRATIVE['turnout']['insight']}</div>",
        unsafe_allow_html=True,
    )

    # ── Chart 2: Line — Political Interest ──────────────────────────
    st.markdown("---")
    col_chart2, col_text2 = st.columns([2, 1])
    with col_text2:
        st.markdown(f"### {CHART_NARRATIVE['interest']['title']}")
        st.markdown(
            f"<div class='narrative-text'>{CHART_NARRATIVE['interest']['intro']}</div>",
            unsafe_allow_html=True,
        )
    with col_chart2:
        st.plotly_chart(_chart_line(frames, selected_gens), use_container_width=True)

    with st.expander("📊 Statistical significance (ANOVA, 2015–2023)"):
        st.markdown(_stat_continuous(frames, "political_interest", selected_gens, [2015, 2019, 2023]) or "—")
    st.markdown(
        f"<div class='narrative-text'>{CHART_NARRATIVE['interest']['insight']}</div>",
        unsafe_allow_html=True,
    )

    # ── Chart 3: Slope — Democratic Satisfaction ────────────────────
    st.markdown("---")
    col_text3, col_chart3 = st.columns([1, 2])
    with col_text3:
        st.markdown(f"### {CHART_NARRATIVE['trust']['title']}")
        st.markdown(
            f"<div class='narrative-text'>{CHART_NARRATIVE['trust']['intro']}</div>",
            unsafe_allow_html=True,
        )
    with col_chart3:
        st.plotly_chart(_chart_slope(frames, selected_gens), use_container_width=True)

    with st.expander("📊 Statistical significance (Chi²-test, 2015 vs 2023)"):
        st.markdown(_stat_continuous(frames, "demo_satisfaction", selected_gens, [2015, 2023]) or "—")
    st.markdown(
        f"<div class='narrative-text'>{CHART_NARRATIVE['trust']['insight']}</div>",
        unsafe_allow_html=True,
    )

    # ── Chart 4: Bar — Political Orientation ────────────────────────
    st.markdown("---")
    col_chart4, col_text4 = st.columns([2, 1])
    with col_text4:
        st.markdown(f"### {CHART_NARRATIVE['lr']['title']}")
        st.markdown(
            f"<div class='narrative-text'>{CHART_NARRATIVE['lr']['intro']}</div>",
            unsafe_allow_html=True,
        )
    with col_chart4:
        st.plotly_chart(_chart_bar_lr(frames, selected_gens), use_container_width=True)

    with st.expander("📊 Statistical significance (ANOVA, 2015–2023)"):
        st.markdown(_stat_continuous(frames, "lr_scale", selected_gens, [2015, 2019, 2023]) or "—")
    st.markdown(
        f"<div class='narrative-text'>{CHART_NARRATIVE['lr']['insight']}</div>",
        unsafe_allow_html=True,
    )

    # ── Summary callout ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        """
        <div class='template-box' style='border-left: 4px solid #DD8452; padding: 1rem 1.5rem;'>
        <strong>Key takeaway:</strong> Younger generations are increasingly disengaged from the ballot box —
        even as their political interest rises. Institutional trust and democratic satisfaction do not explain
        the gap. Older, increasingly right-leaning generations continue to dominate electoral outcomes.
        </div>
        """,
        unsafe_allow_html=True,
    )
