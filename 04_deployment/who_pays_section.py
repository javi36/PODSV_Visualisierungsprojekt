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

    y_min   = df["ratio"].min()
    y_max   = df["ratio"].max()
    y_floor = round(y_min - 0.05, 2)
    y_ceil  = round(y_max + 0.10, 2)

    first_ratio = df.iloc[0]["ratio"]
    last_ratio  = df.iloc[-1]["ratio"]
    delta_abs   = last_ratio - first_ratio
    delta_pct   = (delta_abs / first_ratio) * 100
    last_year   = int(df.iloc[-1]["year"])

    fig = go.Figure()

    # 1. Invisible baseline for fill
    fig.add_trace(go.Scatter(
        x=df["year"],
        y=[y_floor] * len(df),
        mode="lines",
        line=dict(color="rgba(0,0,0,0)", width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # 2. Main line with teal fill to baseline
    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df["ratio"],
        mode="lines+markers",
        fill="tonexty",
        fillcolor="rgba(29,120,116,0.12)",
        line=dict(color="#1d7874", width=2.5),
        marker=dict(
            color="white", size=7, symbol="circle",
            line=dict(color="#1d7874", width=2),
        ),
        name="Contributors per retiree",
        hovertemplate="%{x}: %{y:.2f}<extra></extra>",
    ))

    # 3. First & last value annotations
    fig.add_annotation(
        x=df.iloc[0]["year"], y=df.iloc[0]["ratio"],
        text=f"<b>{df.iloc[0]['ratio']:.2f}</b>",
        showarrow=False, xshift=10, yshift=10,
        font=dict(size=11, color="#1d7874"),
    )
    fig.add_annotation(
        x=last_year, y=last_ratio,
        text=f"<b>{last_ratio:.2f}</b>",
        showarrow=False, xshift=-10, yshift=12,
        font=dict(size=11, color="#1d7874"),
    )

    # 4. Delta badge — rechts AUSSERHALB des Charts (paper coordinates)
    ratio_start_rounded = round(first_ratio * 2) / 2
    ratio_end_rounded   = round(last_ratio * 2) / 2

    def fmt_half(v):
        return f"{int(v)}½" if v % 1 == 0.5 else f"{int(v)}"

    fig.add_annotation(
        xref="paper", yref="paper",
        x=1.01, y=0.98,
        xanchor="left", yanchor="top",
        text=(
            f"<b>{fmt_half(ratio_start_rounded)}</b> workers<br>"
            f"funded 1 retiree<br>"
            f"in {int(df.iloc[0]['year'])}<br>"
            f"<br>"
            f"<b>{fmt_half(ratio_end_rounded)}</b> workers<br>"
            f"funded 1 retiree<br>"
            f"in {last_year}<br>"
            f"<br>"
            f"<span style='color:#1d7874'>▼ {abs(delta_pct):.1f}%<br>"
            f"fewer shoulders to carry<br>"
            f"the financial burden of retirement</span>"
        ),
        showarrow=False,
        font=dict(size=12, color="#444444"),
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#1d7874",
        borderwidth=1.5,
        borderpad=8,
    )

    # 5. Source caption
    fig.add_annotation(
        x=0, y=0,
        xref="paper", yref="paper",
        xanchor="left", yanchor="top",
        text="Source: AHV-Statistik BSV / BFS. Basis: aktiv Erwerbstätige mit Lohnbeiträgen vs. Altersrentenbezüger:innen.",
        showarrow=False,
        font=dict(size=9, color="#888888"),
        yshift=-42,
    )

    _apply_base_layout(
        fig, height=420,
        yaxis=dict(
            range=[y_floor - 0.02, y_ceil],
            title="Contributors per retiree",
            gridcolor="#f0f0f0",
            tickfont=dict(size=11),
        ),
        xaxis=dict(
            range=[int(df.iloc[0]["year"]) - 0.5, last_year + 0.5],
            tickvals=[int(j) for j in jahre],
            ticktext=[str(int(j)) for j in jahre],
            showgrid=False,
            tickfont=dict(size=11),
            title="Jahr",
        ),
        showlegend=False,
    )
    fig.update_layout(margin=dict(t=60, l=60, r=220, b=70))

    return fig



# ─── BAUSTEIN 3: OKP Area Chart ─────────────────────────────────────────────

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

# ─── BAUSTEIN 4: Cashflow OKP + AHV ─────────────────────────────────────────

def _chart_cashflow_pct(
    okp: pd.DataFrame, ahv_ein: pd.DataFrame, ahv_aus: pd.DataFrame, jahre: list
) -> go.Figure:

    # ── Daten berechnen ───────────────────────────────────────────────────────
    all_pct:  dict[str, list] = {}
    all_netto: dict[str, list] = {}
    all_lohn:  dict[str, list] = {}

    for gen in GENS_ORDERED:
        pct_list, netto_list, lohn_list = [], [], []
        for jahr in jahre:
            prem  = get_okp_val(okp, "okp_premium", "per_capita_chf", gen, jahr)
            pv    = get_pv_per_versicherter(okp, gen, jahr)
            kost  = get_okp_val(okp, "okp_kostenbeteiligung", "per_capita_chf", gen, jahr)
            leist = get_okp_val(okp, "okp_bruttoleistungen", "per_capita_chf", gen, jahr)
            ahv_b = get_ahv_beitrag(ahv_ein, gen, jahr)
            ahv_r = get_ahv_rente(ahv_aus, gen, jahr)
            lohn  = get_bruttolohn(ahv_ein, gen, jahr)

            einzahlung = max(prem - pv, 0) + kost + ahv_b
            bezug      = leist + ahv_r
            netto      = bezug - einzahlung

            pct = (netto / lohn * 100) if lohn > 0 else 0
            pct_list.append(pct)
            netto_list.append(netto)
            lohn_list.append(lohn)

        all_pct[gen]   = pct_list
        all_netto[gen] = netto_list
        all_lohn[gen]  = lohn_list

    # ── Arbeitstage berechnen (letztes Jahr, nur Nettozahler) ─────────────────
    WORK_DAYS_PER_YEAR = 220
    working_days: dict[str, float] = {}
    for gen in GENS_ORDERED:
        last_pct = all_pct[gen][-1]
        if last_pct < 0:
            working_days[gen] = round(abs(last_pct) / 100 * WORK_DAYS_PER_YEAR)

    # ── Chart aufbauen ────────────────────────────────────────────────────────
    n_gens = len(GENS_ORDERED)
    fig = make_subplots(
        rows=1, cols=n_gens,
        shared_yaxes=False,
        subplot_titles=[_GEN_SHORT[g] for g in GENS_ORDERED],
        horizontal_spacing=0.03,
    )

    jahre_int = [int(j) for j in jahre]

    for col_i, gen in enumerate(GENS_ORDERED, start=1):
        color     = GEN_COLORS[gen]
        pct_vals  = all_pct[gen]
        netto_vals = all_netto[gen]
        lohn_vals  = all_lohn[gen]
        is_receiver = all_pct[gen][-1] >= 0

        fill_color = _hex_to_rgba(color, 0.15)

        # 1. Invisible baseline for fill
        fig.add_trace(go.Scatter(
            x=jahre_int,
            y=[0] * len(jahre_int),
            mode="lines",
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False,
            hoverinfo="skip",
        ), row=1, col=col_i)

        # 2. Main line with fill to zero
        fig.add_trace(go.Scatter(
            x=jahre_int,
            y=pct_vals,
            mode="lines+markers",
            fill="tonexty",
            fillcolor=fill_color,
            line=dict(color=color, width=2.5),
            marker=dict(
                color="white", size=5, symbol="circle",
                line=dict(color=color, width=1.8),
            ),
            name=gen,
            showlegend=False,
            customdata=list(zip(
                [round(v) for v in netto_vals],
                [round(v) for v in lohn_vals],
            )),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "%{y:.1f}% of gross salary<br>"
                "CHF %{customdata[0]:+.0f}/mt net<br>"
                "Gross salary: CHF %{customdata[1]:,.0f}/mt"
                "<extra>" + _GEN_SHORT[gen] + "</extra>"
            ),
        ), row=1, col=col_i)

        # 3. Zero reference line
        fig.add_hline(
            y=0,
            line_color="#111111", line_width=1.2,
            row=1, col=col_i,
        )

        # 4. Annotation 2012 (erster Wert)
        fig.add_annotation(
            x=jahre_int[0], y=pct_vals[0],
            text=f"<b>{pct_vals[0]:+.1f}%</b>",
            showarrow=False,
            xshift=-2,
            yshift=10 if pct_vals[0] >= 0 else -10,
            yanchor="bottom" if pct_vals[0] >= 0 else "top",
            font=dict(size=9, color=color),
            row=1, col=col_i,
        )

        # 5. Annotation 2024 (letzter Wert) + Rolle
        last_pct  = pct_vals[-1]
        role      = "Net receiver" if last_pct >= 0 else "Net contributor"
        ann_color = "#1d7874" if last_pct >= 0 else "#f25c54"
        fig.add_annotation(
            x=jahre_int[-1], y=last_pct,
            text=f"<b>{last_pct:+.1f}%</b><br><i style='font-size:8px'>{role}</i>",
            showarrow=False,
            xshift=2,
            yshift=10 if last_pct >= 0 else -10,
            yanchor="bottom" if last_pct >= 0 else "top",
            font=dict(size=9, color=ann_color),
            row=1, col=col_i,
        )

    _apply_base_layout(
        fig, height=420,
        hovermode="x unified",
    )
    fig.update_xaxes(
        tickvals=[jahre_int[0], jahre_int[len(jahre_int)//2], jahre_int[-1]],
        ticktext=[str(jahre_int[0]), str(jahre_int[len(jahre_int)//2]), str(jahre_int[-1])],
        tickangle=0,
        tickfont=dict(size=10),
    )
    fig.update_yaxes(ticksuffix="%", tickfont=dict(size=10))
    for col_i in range(2, n_gens + 1):
        fig.update_yaxes(showticklabels=False, row=1, col=col_i)

    fig.update_layout(margin=dict(t=60, l=60, r=30, b=50))

    return fig, working_days


# ─── Main render function ─────────────────────────────────────────────────────

def render_who_pays_section() -> None:
    st.markdown('<div id="who-pays"></div>', unsafe_allow_html=True)
    st.markdown("<div class='section-title'>2. Who Pays</div>", unsafe_allow_html=True)

    # BAUSTEIN 1 — Narrative Bridge
    st.markdown(
        """
        <div class='narrative-text'>
        In March 2024, <strong>Switzerland voted to introduce a 13th AHV pension</strong> — approved by 58.2% of voters.
        The message was unambiguous: retirement security matters. <strong>But the question the ballot left
        unanswered is who actually pays for it.</strong> Switzerland's social contract rests on two pillars:
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
    st.markdown("### Carrying the Weight: AHV Contributors per Retiree")

    st.plotly_chart(
        _chart_ahv_ratio(ahv_ein, ahv_aus, jahre),
        use_container_width=True,
    )
    st.markdown(
        """<div class='narrative-text'>
        The ratio of active AHV contributors to retirees has been declining steadily
        since 2012. As Baby Boomers retire and the workforce grows more slowly, <strong>fewer
        workers are left to finance each pension — and the 13th AHV pension will further
        intensify this pressure.</strong> What is even more concerning is that Parliament has yet
        to agree on how to finance it. With the financial consequences representing a
        classic grey rhino scenario, raising VAT appears increasingly unavoidable, despite
        the measure's unpopularity across the political spectrum. <strong>Switzerland is on track
        to reach a 2:1 ratio by 2030, meaning that only two workers would finance each
        retiree.</strong>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div style="font-size:0.8rem; color:#888888; margin-top:0.3rem;">
        Source details → <a href="?page=references" style="color:#888888;
        text-decoration:underline;">References</a>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── BAUSTEIN 3: OKP Area Chart ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("### The Same Premium, A Very Different Deal")
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

    st.markdown(
        """
        <div class='narrative-text'>
        The OKP — Switzerland's mandatory health insurance — appears neutral on paper: 
        every resident pays the same community-rated premium regardless of age or income. 
        <strong>But the data reveals a striking imbalance.</strong>
        For older generations, benefits received far exceed premiums paid, with <strong>Silent Generation 
        members receiving over CHF 1,000 more per month than they contribute.</strong> For younger generations, 
        the reverse holds: <strong>Gen Z and Millennials consistently pay more than they receive</strong>, effectively 
        cross-subsidising a system weighted toward older cohorts. This structural gap is widening. 

        A 2025 study by the Federal Finance Administration found that <strong>healthcare expenditure per capita 
        has more than quintupled in real terms since 1960</strong> — driven primarily by income growth and rising 
        demand for services (~50% of the increase), population ageing (~15%), and Baumol's cost disease, 
        the structural tendency for labour-intensive sectors like healthcare to face rising costs without 
        equivalent productivity gains. As the Baby Boomer generation enters retirement, the Federal Statistical 
        Office projects <strong>the ageing effect will intensify significantly through the 2030s.</strong> 
        It is no coincidence that healthcare costs remain the single largest concern for the Swiss population: 
        the UBS Worry Barometer 2025 found <strong>that 45% of Swiss voters named rising premiums as their top problem</strong> 
        — a figure that has held persistently high for years, and one that falls disproportionately on younger, 
        healthier policyholders who contribute the most while drawing the least.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── BAUSTEIN 4: Total Cashflow als % Bruttolohn ────────────────────────────
    st.markdown("---")
    st.markdown("### The Generational Bill: What the System Really Costs Each Generation")
    st.markdown(
        "<div class='pyramid-subtitle'>"
        "Net cashflow (OKP + AHV) as % of average gross salary per generation. "
        "Positive = net receiver, Negative = net contributor."
        "</div>",
        unsafe_allow_html=True,
    )

    fig_cf, working_days = _chart_cashflow_pct(okp, ahv_ein, ahv_aus, jahre)
    st.plotly_chart(fig_cf, use_container_width=True)

    # ── Working Days Text ──────────────────────────────────────────────────────
    days_parts = []
    for gen in GENS_ORDERED:
        if gen in working_days:
            color = GEN_COLORS[gen]
            short = _GEN_SHORT[gen]
            days  = working_days[gen]
            days_parts.append(
                f"<span style='color:{color};font-weight:700;'>{short}</span>: "
                f"<span style='font-weight:700;'>{days} days</span>"
            )

    if days_parts:
        st.markdown(
            "<div class='narrative-text'>"
            "In 2024, every net-contributing generation worked a portion of their year "
            "purely to finance transfers to older cohorts — without receiving equivalent benefits."
            "<br><br>"
            "<div style='text-align:center; line-height:2.0;'>"
            + "<br>".join(days_parts) +
            "</div>"
            "<br>"
            "<span style='text-align:left; display:block;'>"
            "— measured in working days per year funded for others."
            "</span>"
            "</div>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    render_who_pays_section()
