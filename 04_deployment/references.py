"""
references.py
─────────────────────────────────────────────────────────────────────────────
References page for the Generational Conflict dashboard.

Covers all four story sections:
  • Generational Conflict (intro / demographic data)
  • Who Decides     (political participation, SELECTS)
  • Who Pays        (housing costs — add sources here once ready)
  • Who Owns        (homeownership data)
  • Data Visualisation & Methodology

How to add a new source:
  1. Append a dict to REFERENCES following the existing schema.
  2. Set "used_in" to one or more section keys from SECTION_ORDER.
  3. Done — the page rebuilds automatically.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st

# ─────────────────────────────────────────────
# Section display order & metadata
# ─────────────────────────────────────────────

SECTION_ORDER: list[dict] = [
    {
        "key":   "Generational Conflict",
        "icon":  "🏠",
        "color": "#0f4c5c",
        "desc":  "Demographic data and generation definitions used in the overview section.",
    },
    {
        "key":   "Who Decides",
        "icon":  "🗳️",
        "color": "#0f4c5c",
        "desc":  "Political participation, voter turnout, and democratic representation.",
    },
    {
        "key":   "Who Pays",
        "icon":  "💸",
        "color": "#f4a259",
        "desc":  "Housing cost burden, rent pressure, and affordability by generation.",
    },
    {
        "key":   "Who Owns",
        "icon":  "🏡",
        "color": "#f25c54",
        "desc":  "Homeownership rates and asset distribution across generations.",
    },
    {
        "key":   "Data Visualisation & Methodology",
        "icon":  "📊",
        "color": "#679289",
        "desc":  "Theoretical framework for narrative data visualisation and storytelling.",
    },
]

# ─────────────────────────────────────────────
# Reference data  (APA 7th edition)
#
# Schema per entry:
#   key       str   — short in-text citation key, e.g. "Lijphart1997"
#   citation  str   — full APA reference (HTML allowed for <em> etc.)
#   used_in   list  — one or more keys from SECTION_ORDER
#   note      str   — one sentence: why is this source relevant?
# ─────────────────────────────────────────────

REFERENCES: list[dict] = [

    # ══════════════════════════════════════════
    # GENERATIONAL CONFLICT — demographic data
    # ══════════════════════════════════════════
    {
        "key": "BFS_DemoBilanz",
        "citation": (
            "Bundesamt für Statistik (BFS). (2024). "
            "<em>Demografische Bilanz der Schweiz</em>. "
            "Neuchâtel: BFS. "
            "Retrieved from https://www.bfs.admin.ch"
        ),
        "used_in": ["Generational Conflict"],
        "note": (
            "Primary source for Swiss population data by birth year used to build "
            "the generational area chart and population pyramid on the Home page."
        ),
    },

    # ══════════════════════════════════════════
    # WHO DECIDES — political participation
    # ══════════════════════════════════════════
    {
        "key": "SELECTS2015",
        "citation": (
            "Lutz, G., &amp; Selects Team. (2016). "
            "<em>Swiss Electoral Study SELECTS 2015</em>. "
            "FORS, Université de Lausanne. "
            "DOI: 10.23662/FORS-DS-726-3"
        ),
        "used_in": ["Who Decides"],
        "note": (
            "Post-election survey (N ≈ 5 337). Used for voter turnout, political interest, "
            "democratic satisfaction, and left–right orientation (2015 baseline)."
        ),
    },
    {
        "key": "SELECTS2019",
        "citation": (
            "Lutz, G., &amp; Selects Team. (2020). "
            "<em>Swiss Electoral Study SELECTS 2019</em>. "
            "FORS, Université de Lausanne. "
            "DOI: 10.23662/FORS-DS-1077-2"
        ),
        "used_in": ["Who Decides"],
        "note": (
            "Post-election survey (N ≈ 6 664). Used as the mid-period observation "
            "point for all four Who Decides charts."
        ),
    },
    {
        "key": "SELECTS2023",
        "citation": (
            "Lutz, G. (2024). "
            "<em>Swiss Electoral Study SELECTS 2023</em>. "
            "FORS, Université de Lausanne. "
            "DOI: 10.23662/FORS-DS-1512-1"
        ),
        "used_in": ["Who Decides"],
        "note": (
            "Post-election survey (N ≈ 5 033). Most recent observation point "
            "for all four Who Decides charts."
        ),
    },
    {
        "key": "Lijphart1997",
        "citation": (
            "Lijphart, A. (1997). "
            "Unequal Participation: Democracy's Unresolved Dilemma. "
            "<em>American Political Science Review</em>, 91(1), 1–14. "
            "DOI: 10.2307/2952255"
        ),
        "used_in": ["Who Decides"],
        "note": (
            "Classic argument that unequal voter turnout systematically distorts "
            "democratic representation toward older citizens — not through manipulation, "
            "but through silence."
        ),
    },
    {
        "key": "Dalton2008",
        "citation": (
            "Dalton, R. J. (2008). "
            "<em>Citizen Politics: Public Opinion and Political Parties "
            "in Advanced Industrial Democracies</em> (5th ed.). "
            "CQ Press."
        ),
        "used_in": ["Who Decides"],
        "note": (
            "Introduces 'cognitive mobilisation': citizens become more politically aware "
            "but disengage from conventional participation such as voting — directly "
            "explaining the interest-turnout paradox in the SELECTS data."
        ),
    },
    {
        "key": "BuehlmannFreitag2006",
        "citation": (
            "Bühlmann, M., &amp; Freitag, M. (2006). "
            "Individual and Contextual Determinants of Electoral Participation. "
            "<em>Swiss Political Science Review</em>, 12(4), 13–47. "
            "DOI: 10.1002/j.1662-6370.2006.tb00059.x"
        ),
        "used_in": ["Who Decides"],
        "note": (
            "Switzerland-specific analysis of abstention, highlighting the complexity of "
            "direct democracy and the absence of automatic voter registration as structural "
            "barriers — particularly for younger citizens."
        ),
    },

    # ══════════════════════════════════════════
    # WHO PAYS — housing costs
    # Add sources here once the Who Pays analysis is complete.
    # ══════════════════════════════════════════
    #
    # Example:
    # {
    #     "key": "BFS_Mietpreise2023",
    #     "citation": (
    #         "Bundesamt für Statistik (BFS). (2023). "
    #         "<em>Mietpreiserhebung 2023</em>. Neuchâtel: BFS."
    #     ),
    #     "used_in": ["Who Pays"],
    #     "note": "Official Swiss rental price survey used as primary data source.",
    # },

    # ══════════════════════════════════════════
    # WHO OWNS — homeownership data
    # ══════════════════════════════════════════
    {
        "key": "BFS_Bewohnertyp",
        "citation": (
            "Bundesamt für Statistik (BFS). (2024). "
            "<em>Bewohnertyp nach Kanton und Gemeindegrösse</em>. "
            "Neuchâtel: BFS. "
            "Retrieved from https://www.bfs.admin.ch"
        ),
        "used_in": ["Who Owns"],
        "note": (
            "Official statistics on residential occupancy type (owner, tenant, cooperative) "
            "used as primary data source for the Who Owns section."
        ),
    },
    {
        "key": "BFS_Wohnflaeche",
        "citation": (
            "Bundesamt für Statistik (BFS). (2024). "
            "<em>Wohnfläche pro Person nach Kanton</em>. "
            "Neuchâtel: BFS. "
            "Retrieved from https://www.bfs.admin.ch"
        ),
        "used_in": ["Who Owns"],
        "note": (
            "Official statistics on living space per person by canton, used to "
            "contextualise ownership patterns in the Who Owns section."
        ),
    },

    # ══════════════════════════════════════════
    # DATA VISUALISATION & METHODOLOGY
    # ══════════════════════════════════════════
    {
        "key": "Weber2020",
        "citation": (
            "Weber, W. (2020). "
            "Exploring narrativity in data visualization in journalism. "
            "In M. Engebretsen &amp; H. Kennedy (Eds.), "
            "<em>Data Visualization in Society</em> (pp. 293–312). "
            "Amsterdam University Press. "
            "DOI: 10.5117/9789463722902_ch18"
        ),
        "used_in": ["Data Visualisation & Methodology"],
        "note": (
            "Defines the four narrative constituents — narrator presence, sequentiality, "
            "temporal dimension, and tellability — that shaped the dashboard's "
            "storytelling structure."
        ),
    },
    {
        "key": "SegelHeer2010",
        "citation": (
            "Segel, E., &amp; Heer, J. (2010). "
            "Narrative Visualization: Telling Stories with Data. "
            "<em>IEEE Transactions on Visualization and Computer Graphics</em>, "
            "16(6), 1139–1148. "
            "DOI: 10.1109/TVCG.2010.179"
        ),
        "used_in": ["Data Visualisation & Methodology"],
        "note": (
            "Introduces the Martini-Glass narrative structure (author-driven opening "
            "followed by reader-driven exploration) applied in the layout of each section."
        ),
    },
    {
        "key": "Kirk2016",
        "citation": (
            "Kirk, A. (2016). "
            "<em>Data Visualisation: A Handbook for Data Driven Design</em>. "
            "SAGE Publications."
        ),
        "used_in": ["Data Visualisation & Methodology"],
        "note": (
            "Practical reference for chart type selection, colour, and annotation "
            "conventions used throughout the dashboard."
        ),
    },
]


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _refs_for_section(section_key: str) -> list[dict]:
    return [r for r in REFERENCES if section_key in r["used_in"]]


def _render_ref_card(ref: dict, border_color: str = "#1d7874") -> None:
    card_style = (
        f"background:#f9fafb;border-radius:8px;padding:1rem 1.3rem;"
        f"margin-bottom:0.85rem;border-left:3px solid {border_color};"
    )
    key_style = (
        "font-size:0.76rem;font-weight:700;color:#555555;"
        "letter-spacing:0.05em;margin-bottom:0.3rem;text-transform:uppercase;"
    )
    cit_style = "font-size:0.95rem;line-height:1.65;color:#222222;margin-bottom:0.35rem;"
    note_style = "font-size:0.82rem;line-height:1.5;color:#777777;font-style:italic;"

    st.markdown(
        f"<div style='{card_style}'>"
        f"<div style='{key_style}'>{ref['key']}</div>"
        f"<div style='{cit_style}'>{ref['citation']}</div>"
        f"<div style='{note_style}'>{ref['note']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Page entry point
# ─────────────────────────────────────────────

def render_references_section() -> None:
    # inject_global_styles() wird bereits in app.py aufgerufen — hier weglassen

    # ── Anchor ───────────────────────────────────────────────────────
    st.markdown('<div id="references"></div>', unsafe_allow_html=True)

    # ── Intro text ───────────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:1.05rem;line-height:1.7;color:#555555;"
        "max-width:680px;margin:0 auto 2.2rem;text-align:center;'>"
        "All data sources, academic literature, and methodological references cited "
        "in this dashboard — organised by section and listed alphabetically below."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Section-by-section view ──────────────────────────────────────
    for section in SECTION_ORDER:
        refs = _refs_for_section(section["key"])

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.6rem;"
            f"border-top:3px solid {section['color']};padding-top:1rem;"
            f"margin-top:2rem;margin-bottom:0.3rem;'>"
            f"<span style='font-size:1.35rem;'>{section['icon']}</span>"
            f"<span style='font-size:1.2rem;font-weight:700;color:#111111;'>"
            f"{section['key']}</span>"
            f"</div>"
            f"<p style='font-size:0.88rem;color:#777777;margin-bottom:0.9rem;'>"
            f"{section['desc']}</p>",
            unsafe_allow_html=True,
        )

        if refs:
            for ref in refs:
                _render_ref_card(ref, border_color=section["color"])
        else:
            # Placeholder — shown when a section has no sources yet
            st.markdown(
                "<div style='background:#fffbf0;border-radius:8px;"
                "padding:0.85rem 1.2rem;margin-bottom:0.9rem;"
                "border-left:3px solid #f4a259;font-size:0.88rem;color:#888888;'>"
                "📌 No references added yet for this section. "
                "Append an entry to <code>REFERENCES</code> in "
                "<code>references.py</code> with "
                f"<code>\"used_in\": [\"{section['key']}\"]</code>."
                "</div>",
                unsafe_allow_html=True,
            )

    # ── Full alphabetical list ───────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        "<h3 style='margin-top:1.2rem;margin-bottom:0.8rem;'>"
        "Complete Reference List (A–Z)</h3>",
        unsafe_allow_html=True,
    )

    for ref in sorted(REFERENCES, key=lambda r: r["key"].lower()):
        _render_ref_card(ref)
        st.markdown(
            f"<div style='font-size:0.74rem;color:#bbbbbb;"
            f"margin-top:-0.65rem;margin-bottom:1rem;padding-left:0.2rem;'>"
            f"Cited in: {' · '.join(ref['used_in'])}"
            f"</div>",
            unsafe_allow_html=True,
        )