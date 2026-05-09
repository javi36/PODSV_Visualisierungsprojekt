from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─── Local constants ──────────────────────────────────────────────────────────

GEN_DISPLAY_MAP = {
    "Generation Alpha": "Generation Alpha",
    "Generation Z":     "Generation Z",
    "Millennials":      "Millennials",
    "Generation X":     "Generation X",
    "Babyboomers":      "Babyboomers",
    "Silent Generation": "Silent Generation",
}

GENS_ORDERED = [
    "Silent Generation",
    "Babyboomers",
    "Generation X",
    "Millennials",
    "Generation Z",
]

GEN_COLORS = {
    "Silent Generation": "#0f4c5c",
    "Babyboomers":       "#1d7874",
    "Generation X":      "#679289",
    "Millennials":       "#f4a259",
    "Generation Z":      "#f25c54",
    "Generation Alpha":  "#a8a8a8",
}

_GEN_SHORT = {
    "Silent Generation": "Silent Gen.",
    "Babyboomers":       "Babyboomers",
    "Generation X":      "Gen X",
    "Millennials":       "Millennials",
    "Generation Z":      "Gen Z",
}

AHV_SATZ = 0.087
BEZUEGER_GENS = ["Babyboomers", "Silent Generation"]
COMMON_YEARS_START = 2012

# ─── Helper functions (validated in EDA) ──────────────────────────────────────

def get_okp_val(okp, variable, metric, gen, jahr):
    val = okp[
        (okp["variable_name"] == variable) &
        (okp["metric"] == metric) &
        (okp["project_age_group"] == gen) &
        (okp["year"] == jahr)
    ]["value"].mean()
    return (val / 12) if not pd.isna(val) else 0


def get_pv_per_versicherter(okp, gen, jahr):
    pv_total = okp[
        (okp["variable_name"] == "praemienverbilligung") &
        (okp["metric"] == "total_mio_chf") &
        (okp["project_age_group"] == gen) &
        (okp["year"] == jahr)
    ]["value"].sum()
    pv_count = okp[
        (okp["variable_name"] == "praemienverbilligung") &
        (okp["metric"] == "beneficiaries_count") &
        (okp["project_age_group"] == gen) &
        (okp["year"] == jahr)
    ]["value"].sum()
    pv_rate = okp[
        (okp["variable_name"] == "praemienverbilligung") &
        (okp["metric"] == "beneficiary_rate") &
        (okp["project_age_group"] == gen) &
        (okp["year"] == jahr)
    ]["value"].mean()
    if pd.isna(pv_rate) or pv_rate == 0 or pd.isna(pv_count) or pv_count == 0:
        return 0
    n_versicherte = pv_count / (pv_rate / 100)
    return (pv_total * 1_000_000) / n_versicherte / 12


def get_ahv_beitrag(ahv_ein, gen, jahr):
    n = ahv_ein[
        (ahv_ein["metric"] == "n_personen") &
        (ahv_ein["project_age_group"] == gen) &
        (ahv_ein["year"] == jahr)
    ]["value"].sum()
    s = ahv_ein[
        (ahv_ein["metric"] == "sum_beitrag_ahv") &
        (ahv_ein["project_age_group"] == gen) &
        (ahv_ein["year"] == jahr)
    ]["value"].sum()
    return (s / n / 12) if n > 0 else 0


def get_ahv_rente(ahv_aus, gen, jahr):
    if gen not in BEZUEGER_GENS:
        return 0
    aus_n = ahv_aus[
        (ahv_aus["metric"] == "anzahl_renten") &
        (ahv_aus["project_age_group"] == gen) &
        (ahv_aus["year"] == jahr)
    ][["age", "value"]].rename(columns={"value": "n"})
    aus_mw = ahv_aus[
        (ahv_aus["metric"] == "renten_mittelwert_chf") &
        (ahv_aus["project_age_group"] == gen) &
        (ahv_aus["year"] == jahr)
    ][["age", "value"]].rename(columns={"value": "mw"})
    merged = aus_n.merge(aus_mw, on="age")
    if merged.empty or merged["n"].sum() == 0:
        return 0
    return (merged["mw"] * merged["n"]).sum() / merged["n"].sum()


def get_bruttolohn(ahv_ein, gen, jahr):
    n = ahv_ein[
        (ahv_ein["metric"] == "n_personen") &
        (ahv_ein["project_age_group"] == gen) &
        (ahv_ein["year"] == jahr)
    ]["value"].sum()
    s = ahv_ein[
        (ahv_ein["metric"] == "sum_beitrag_ahv") &
        (ahv_ein["project_age_group"] == gen) &
        (ahv_ein["year"] == jahr)
    ]["value"].sum()
    if n == 0:
        return 0
    return (s / n) / AHV_SATZ / 12


# ─── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data
def load_whopays_data():
    base = Path(__file__).resolve().parents[1]
    processed = base / "data" / "whopays" / "processed_whopays"
    okp     = pd.read_csv(processed / "okp_by_birth_year.csv")
    ahv_ein = pd.read_csv(processed / "ahv_einnahmen_by_birth_year.csv")
    ahv_aus = pd.read_csv(processed / "ahv_ausgaben_by_age.csv")
    jahre = sorted(
        set(okp["year"].unique()) &
        set(ahv_ein["year"].unique()) &
        set(ahv_aus["year"].unique())
    )
    jahre = [j for j in jahre if j >= COMMON_YEARS_START]
    return okp, ahv_ein, ahv_aus, jahre


# ─── Internal layout helpers ──────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _apply_base_layout(fig: go.Figure, height: int = 400, **kwargs) -> go.Figure:
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="sans-serif", size=12, color="#111111"),
        margin=dict(t=60, l=50, r=30, b=50),
        hoverlabel=dict(font_size=13),
        height=height,
        **kwargs,
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#f0f0f0", tickfont=dict(size=11))
    return fig


# ─── BAUSTEIN 2: AHV Dependency Ratio ────────────────────────────────────────

def _chart_ahv_ratio(
    ahv_ein: pd.DataFrame, ahv_aus: pd.DataFrame, jahre: list
) -> go.Figure:
    records = []
    for jahr in jahre:
        n_ein = ahv_ein[
            (ahv_ein["metric"] == "n_personen") & (ahv_ein["year"] == jahr)
        ]["value"].sum()
        n_aus = ahv_aus[
            (ahv_aus["metric"] == "anzahl_renten") & (ahv_aus["year"] == jahr)
        ]["value"].sum()
        if n_aus > 0:
            records.append({"year": int(jahr), "ratio": n_ein / n_aus})

    df = pd.DataFrame(records)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df["ratio"],
        mode="lines+markers",
        line=dict(color="#1d7874", width=2.5),
        marker=dict(
            color="#1d7874", size=7, symbol="circle",
            line=dict(color="white", width=1.5),
        ),
        name="Contributors per retiree",
        hovertemplate="%{x}: %{y:.2f}<extra></extra>",
    ))

    # Reference line 3:1 (historical)
    fig.add_hline(
        y=3.0,
        line_dash="solid", line_color="#aaaaaa", line_width=1,
        annotation_text="Historical ratio (3:1)",
        annotation_position="right",
        annotation_font=dict(size=11, color="#888888"),
    )

    # Reference line 2:1 (projected 2030), dashed red
    fig.add_hline(
        y=2.0,
        line_dash="dash", line_color="#f25c54", line_width=1.5,
        annotation_text="Projected 2030 (2:1)",
        annotation_position="right",
        annotation_font=dict(size=11, color="#f25c54"),
    )

    # Annotate last data point
    last = df.iloc[-1]
    fig.add_annotation(
        x=last["year"], y=last["ratio"],
        text=f"<b>{last['ratio']:.2f}</b>",
        showarrow=True, arrowhead=2, arrowcolor="#1d7874",
        ax=30, ay=-30,
        font=dict(size=12, color="#1d7874"),
        bgcolor="rgba(255,255,255,0.8)",
    )

    _apply_base_layout(
        fig, height=380,
        yaxis=dict(
            range=[1.5, 4.5],
            title="Contributors per retiree",
            gridcolor="#f0f0f0",
            tickfont=dict(size=11),
        ),
        xaxis=dict(
            tickvals=[int(j) for j in jahre],
            ticktext=[str(int(j)) for j in jahre],
            showgrid=False,
            tickfont=dict(size=11),
        ),
        showlegend=False,
    )
    return fig


# ─── BAUSTEIN 3a: OKP Area Chart ─────────────────────────────────────────────

def _chart_okp_area(okp: pd.DataFrame, okp_jahre: list) -> go.Figure:
    data: dict[str, dict] = {}
    for gen in GENS_ORDERED:
        netto_list, brutto_list = [], []
        for jahr in okp_jahre:
            prem = get_okp_val(okp, "okp_premium", "per_capita_chf", gen, jahr)
            pv   = get_pv_per_versicherter(okp, gen, jahr)
            brut = get_okp_val(okp, "okp_bruttoleistungen", "per_capita_chf", gen, jahr)
            netto_list.append(max(prem - pv, 0))
            brutto_list.append(brut)
        data[gen] = {"netto": netto_list, "brutto": brutto_list}

    n_gens = len(GENS_ORDERED)
    fig = make_subplots(
        rows=1, cols=n_gens,
        shared_yaxes=True,
        subplot_titles=[_GEN_SHORT[g] for g in GENS_ORDERED],
        horizontal_spacing=0.02,
    )

    first = True
    for col_i, gen in enumerate(GENS_ORDERED, start=1):
        color = GEN_COLORS[gen]
        netto_vals  = data[gen]["netto"]
        brutto_vals = data[gen]["brutto"]

        # Benefits received — lighter, drawn first (background)
        fig.add_trace(go.Scatter(
            x=okp_jahre, y=brutto_vals,
            mode="lines",
            fill="tozeroy",
            line=dict(color=color, width=1),
            fillcolor=_hex_to_rgba(color, 0.25),
            name="Benefits received",
            legendgroup="benefits",
            showlegend=first,
            hovertemplate=f"%{{x}}: CHF %{{y:.0f}}/mt<extra>{gen} – Benefits</extra>",
        ), row=1, col=col_i)

        # Net premium paid — darker, drawn on top
        fig.add_trace(go.Scatter(
            x=okp_jahre, y=netto_vals,
            mode="lines",
            fill="tozeroy",
            line=dict(color=color, width=2),
            fillcolor=_hex_to_rgba(color, 0.6),
            name="Net premium paid",
            legendgroup="premium",
            showlegend=first,
            hovertemplate=f"%{{x}}: CHF %{{y:.0f}}/mt<extra>{gen} – Net premium</extra>",
        ), row=1, col=col_i)

        first = False

        # 2024 delta annotation
        delta = brutto_vals[-1] - netto_vals[-1]
        sign  = "+" if delta >= 0 else "−"
        ann_color = "#1d7874" if delta >= 0 else "#f25c54"
        fig.add_annotation(
            x=okp_jahre[-1],
            y=max(brutto_vals[-1], netto_vals[-1]),
            text=f"<b>{sign}{abs(delta):.0f}<br>CHF/mt</b>",
            showarrow=False,
            yshift=14,
            font=dict(size=9, color=ann_color),
            row=1, col=col_i,
        )

        # Invisible delta traces for unified hover (positive=green, negative=red)
        delta_vals = [b - nv for b, nv in zip(brutto_vals, netto_vals)]
        pos_delta = [v if v >= 0 else None for v in delta_vals]
        neg_delta = [abs(v) if v < 0 else None for v in delta_vals]

        fig.add_trace(go.Scatter(
            x=okp_jahre, y=pos_delta,
            mode="markers",
            marker=dict(opacity=0, size=12, color="#1d7874"),
            showlegend=False,
            name="",
            hovertemplate="+CHF %{y:.0f}/mt<extra>Net delta</extra>",
        ), row=1, col=col_i)

        fig.add_trace(go.Scatter(
            x=okp_jahre, y=neg_delta,
            mode="markers",
            marker=dict(opacity=0, size=12, color="#f25c54"),
            showlegend=False,
            name="",
            hovertemplate="−CHF %{y:.0f}/mt<extra>Net delta</extra>",
        ), row=1, col=col_i)

    _apply_base_layout(
        fig, height=350,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.3,
            xanchor="center", x=0.5,
            font=dict(size=11),
        ),
    )
    # Show first and last year on every facet; hide inner y-axis labels
    fig.update_xaxes(
        tickmode="array",
        tickvals=[okp_jahre[0], okp_jahre[-1]],
        ticktext=[str(int(okp_jahre[0])), str(int(okp_jahre[-1]))],
        tickangle=0,
        tickfont=dict(size=9),
    )
    for col_i in range(2, n_gens + 1):
        fig.update_yaxes(showticklabels=False, row=1, col=col_i)

    return fig


# ─── BAUSTEIN 3b: OKP Bar Chart ──────────────────────────────────────────────

def _chart_okp_bar(okp: pd.DataFrame, okp_jahre: list) -> go.Figure:
    n = len(okp_jahre)
    sel_idx   = [0, n // 3, 2 * n // 3, -1]
    sel_jahre = [okp_jahre[i] for i in sel_idx]

    n_gens = len(GENS_ORDERED)
    fig = make_subplots(
        rows=1, cols=n_gens,
        shared_yaxes=True,
        subplot_titles=[_GEN_SHORT[g] for g in GENS_ORDERED],
        horizontal_spacing=0.02,
        specs=[[{"secondary_y": True}] * n_gens],
    )

    first = True
    for col_i, gen in enumerate(GENS_ORDERED, start=1):
        color = GEN_COLORS[gen]
        netto_vals, brutto_vals = [], []
        for jahr in sel_jahre:
            prem = get_okp_val(okp, "okp_premium", "per_capita_chf", gen, jahr)
            pv   = get_pv_per_versicherter(okp, gen, jahr)
            brut = get_okp_val(okp, "okp_bruttoleistungen", "per_capita_chf", gen, jahr)
            netto_vals.append(max(prem - pv, 0))
            brutto_vals.append(brut)

        x_labels = [str(int(j)) for j in sel_jahre]

        fig.add_trace(go.Bar(
            x=x_labels, y=netto_vals,
            name="Net premium",
            legendgroup="premium",
            showlegend=first,
            marker_color=color,
            opacity=1.0,
            text=[f"{v:.0f}" for v in netto_vals],
            textposition="outside",
            textfont=dict(size=8),
            hovertemplate="%{x}: CHF %{y:.0f}/mt<extra>Net premium</extra>",
        ), row=1, col=col_i, secondary_y=False)

        fig.add_trace(go.Bar(
            x=x_labels, y=brutto_vals,
            name="Benefits received",
            legendgroup="benefits",
            showlegend=first,
            marker_color=_hex_to_rgba(color, 0.5),
            opacity=1.0,
            text=[f"{v:.0f}" for v in brutto_vals],
            textposition="outside",
            textfont=dict(size=8),
            hovertemplate="%{x}: CHF %{y:.0f}/mt<extra>Benefits</extra>",
        ), row=1, col=col_i, secondary_y=False)

        # Net balance trend line on secondary y-axis
        net_balance = [b - nv for b, nv in zip(brutto_vals, netto_vals)]
        last_nb = net_balance[-1]
        sign_str = "+" if last_nb >= 0 else "−"

        pos_nb = [v if v >= 0 else None for v in net_balance]
        neg_nb = [v if v < 0 else None for v in net_balance]

        pos_text = [None] * len(sel_jahre)
        neg_text = [None] * len(sel_jahre)
        if last_nb >= 0:
            pos_text[-1] = f"{sign_str}{abs(last_nb):.0f}"
        else:
            neg_text[-1] = f"{sign_str}{abs(last_nb):.0f}"

        if any(v is not None for v in pos_nb):
            fig.add_trace(go.Scatter(
                x=x_labels, y=pos_nb,
                mode="lines+markers+text",
                line=dict(color="#1d7874", width=2),
                marker=dict(color="#1d7874", size=6),
                text=pos_text,
                textposition="top right",
                textfont=dict(size=9, color="#1d7874"),
                name="Net balance (+)",
                legendgroup="net_balance",
                showlegend=first,
                hovertemplate="%{x}: CHF %{y:+.0f}/mt<extra>Net balance</extra>",
            ), row=1, col=col_i, secondary_y=True)

        if any(v is not None for v in neg_nb):
            fig.add_trace(go.Scatter(
                x=x_labels, y=neg_nb,
                mode="lines+markers+text",
                line=dict(color="#f25c54", width=2),
                marker=dict(color="#f25c54", size=6),
                text=neg_text,
                textposition="top right",
                textfont=dict(size=9, color="#f25c54"),
                name="Net balance (−)",
                legendgroup="net_balance_neg",
                showlegend=first,
                hovertemplate="%{x}: CHF %{y:+.0f}/mt<extra>Net balance</extra>",
            ), row=1, col=col_i, secondary_y=True)

        first = False

    _apply_base_layout(
        fig, height=380,
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.3,
            xanchor="center", x=0.5,
            font=dict(size=11),
        ),
    )
    fig.update_xaxes(tickfont=dict(size=10))
    for col_i in range(2, n_gens + 1):
        fig.update_yaxes(showticklabels=False, row=1, col=col_i, secondary_y=False)
    for col_i in range(1, n_gens + 1):
        fig.update_yaxes(
            zeroline=True, zerolinecolor="#111111", zerolinewidth=2,
            showgrid=False,
            secondary_y=True,
            row=1, col=col_i,
        )
    fig.update_yaxes(
        title_text="Net balance (CHF/month)",
        secondary_y=True,
        row=1, col=n_gens,
    )

    return fig


# ─── BAUSTEIN 4: Cashflow OKP + AHV ─────────────────────────────────────────

def _chart_cashflow(
    okp: pd.DataFrame, ahv_ein: pd.DataFrame, ahv_aus: pd.DataFrame, jahre: list
) -> go.Figure:
    all_data: dict[str, list] = {}
    for gen in GENS_ORDERED:
        netto_list = []
        for jahr in jahre:
            prem  = get_okp_val(okp, "okp_premium", "per_capita_chf", gen, jahr)
            pv    = get_pv_per_versicherter(okp, gen, jahr)
            kost  = get_okp_val(okp, "okp_kostenbeteiligung", "per_capita_chf", gen, jahr)
            leist = get_okp_val(okp, "okp_bruttoleistungen", "per_capita_chf", gen, jahr)
            ahv_b = get_ahv_beitrag(ahv_ein, gen, jahr)
            ahv_r = get_ahv_rente(ahv_aus, gen, jahr)

            einzahlung = max(prem - pv, 0) + kost + ahv_b
            bezug      = leist + ahv_r
            netto_list.append(bezug - einzahlung)
        all_data[gen] = netto_list

    n_gens = len(GENS_ORDERED)
    fig = make_subplots(
        rows=1, cols=n_gens,
        shared_yaxes=False,
        subplot_titles=[_GEN_SHORT[g] for g in GENS_ORDERED],
        horizontal_spacing=0.04,
    )

    for col_i, gen in enumerate(GENS_ORDERED, start=1):
        color      = GEN_COLORS[gen]
        netto_vals = all_data[gen]

        bar_colors = [
            color if v >= 0 else _hex_to_rgba(color, 0.4)
            for v in netto_vals
        ]

        fig.add_trace(go.Bar(
            x=[int(j) for j in jahre],
            y=netto_vals,
            marker_color=bar_colors,
            name=gen,
            showlegend=False,
            hovertemplate="%{x}: CHF %{y:+.0f}/mt<extra>" + gen + "</extra>",
        ), row=1, col=col_i)

        # Prominent zero line
        fig.add_hline(y=0, line_color="#111111", line_width=1.5, row=1, col=col_i)

        # Annotate 2024 value + label
        last_val  = netto_vals[-1]
        sign      = "+" if last_val >= 0 else "−"
        ann_color = "#1d7874" if last_val >= 0 else "#f25c54"
        role      = "Net receiver" if last_val >= 0 else "Net contributor"
        fig.add_annotation(
            x=int(jahre[-1]),
            y=last_val,
            text=f"<b>{sign}{abs(last_val):.0f}</b><br><i style='font-size:8px'>{role}</i>",
            showarrow=False,
            yshift=14 if last_val >= 0 else -14,
            yanchor="bottom" if last_val >= 0 else "top",
            font=dict(size=10, color=ann_color),
            row=1, col=col_i,
        )

    _apply_base_layout(fig, height=400, showlegend=False)
    fig.update_xaxes(tickangle=45, tickfont=dict(size=9))

    return fig


# ─── Main render function ─────────────────────────────────────────────────────

def render_who_pays_section() -> None:
    st.markdown('<div id="who-pays"></div>', unsafe_allow_html=True)
    st.markdown("<div class='section-title'>2. Who Pays</div>", unsafe_allow_html=True)

    # BAUSTEIN 1 — Narrative Bridge
    st.markdown(
        """
        <div class='narrative-text'>
        In March 2024, Switzerland voted to introduce a 13th AHV pension — approved by 58.2% of voters.
        The message was unambiguous: retirement security matters. But the question the ballot left
        unanswered is who actually pays for it. Switzerland's social contract rests on two pillars:
        the AHV (old-age insurance), funded by today's workers for today's retirees, and the OKP
        (mandatory health insurance), where every resident pays premiums regardless of age or income.
        Together, these two systems define the generational transfer of money — and they tell a striking
        story about who contributes, who benefits, and which generations carry the tab.
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        okp, ahv_ein, ahv_aus, jahre = load_whopays_data()
    except Exception as exc:
        st.error("Could not load Who Pays data. Check that the processed CSV files exist.")
        st.exception(exc)
        return

    # OKP years restricted to those that have per_capita_chf data
    okp_jahre = sorted(
        set(okp[(okp["variable_name"] == "okp_premium") & (okp["metric"] == "per_capita_chf")]["year"].unique()) &
        set(okp[(okp["variable_name"] == "okp_bruttoleistungen") & (okp["metric"] == "per_capita_chf")]["year"].unique())
    )
    okp_jahre = [j for j in okp_jahre if j >= COMMON_YEARS_START]

    # ── BAUSTEIN 2: AHV Dependency Ratio ──────────────────────────────────────
    st.markdown("---")
    st.markdown("### The Shrinking Support Base: AHV Contributors per Retiree")

    st.plotly_chart(
        _chart_ahv_ratio(ahv_ein, ahv_aus, jahre),
        use_container_width=True,
    )
    st.markdown(
        """<div class='narrative-text'>
        The ratio of active AHV contributors to retirees has been declining steadily
        since 2012. As Baby Boomers retire and the workforce grows more slowly, fewer
        workers are left to finance each pension — and the 13th AHV pension will further
        intensify this pressure. What is even more concerning is that Parliament has yet
        to agree on how to finance it. With the financial consequences representing a
        classic grey rhino scenario, raising VAT appears increasingly unavoidable, despite
        the measure's unpopularity across the political spectrum. Switzerland is on track
        to reach a 2:1 ratio by 2030, meaning that only two workers would finance each
        retiree.
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div style="font-size:0.8rem; color:#888888; margin-top:0.3rem;">
        Source: Eling (2013), "Der Generationenvertrag in Gefahr",
        Universität St. Gallen, I.VW-HSG; based on BFS population projections (2012).
        </div>""",
        unsafe_allow_html=True,
    )

    # ── BAUSTEIN 3a: OKP Area Chart ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("### OKP: What Each Generation Pays vs. Receives (Area Chart)")
    st.markdown(
        "<div class='pyramid-subtitle'>"
        "Monthly average per person, CHF. "
        "Net premium = gross premium minus subsidy (Prämienverbilligung). "
        "Shaded area: net premium paid (dark) vs. benefits received (light). "
        "Annotation shows 2024 net delta."
        "</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _chart_okp_area(okp, okp_jahre),
        use_container_width=True,
    )

    # ── BAUSTEIN 3b: OKP Bar Chart ────────────────────────────────────────────
    st.markdown("### OKP: What Each Generation Pays vs. Receives (Bar Chart)")
    st.markdown(
        "<div class='pyramid-subtitle'>"
        "Monthly average per person, CHF. "
        "Net premium = gross premium minus subsidy (Prämienverbilligung)."
        "</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _chart_okp_bar(okp, okp_jahre),
        use_container_width=True,
    )

    # ── BAUSTEIN 4: Total Cashflow OKP + AHV ──────────────────────────────────
    st.markdown("---")
    st.markdown("### Net Cashflow per Generation: OKP + AHV Combined")
    st.markdown(
        "<div class='pyramid-subtitle'>"
        "Monthly average per person, CHF. "
        "Positive = net receiver, Negative = net contributor. "
        "Einzahlung = net OKP premium + cost-sharing + AHV contribution. "
        "Bezug = OKP benefits + AHV pension (retiree generations only)."
        "</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _chart_cashflow(okp, ahv_ein, ahv_aus, jahre),
        use_container_width=True,
    )


if __name__ == "__main__":
    render_who_pays_section()
