"""
references.py
─────────────────────────────────────────────────────────────────────────────
References page for the Generational Conflict dashboard.

How to add a new source:
  1. Append a dict to REFERENCES following the existing schema.
  2. Done — the list rebuilds automatically in A–Z order.
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st

# ─────────────────────────────────────────────
# Reference data  (APA 7th edition)
#
# Schema:
#   key       str  — short in-text citation key, e.g. "Lijphart1997"
#   citation  str  — full APA reference (HTML allowed for <em>)
#   note      str  — one sentence: why is this source relevant?
# ─────────────────────────────────────────────

REFERENCES: list[dict] = [
    {
        "key": "BuehlmannFreitag2006",
        "citation": (
            "Bühlmann, M., &amp; Freitag, M. (2006). "
            "Individual and Contextual Determinants of Electoral Participation. "
            "<em>Swiss Political Science Review</em>, 12(4), 13–47. "
            "DOI: 10.1002/j.1662-6370.2006.tb00059.x"
        ),
        "note": (
            "Switzerland-specific analysis of abstention, highlighting growing "
            "disillusionment with parties as a structural barrier to youth participation."
        ),
    },
    {
        "key": "Kirk2016",
        "citation": (
            "Kirk, A. (2016). "
            "<em>Data Visualisation: A Handbook for Data Driven Design</em>. "
            "SAGE Publications."
        ),
        "note": (
            "Practical reference for chart type selection, colour, and annotation "
            "conventions used throughout the dashboard."
        ),
    },
    {
        "key": "LerchColombierBraendle2025",
        "citation": (
            "Lerch, B., Colombier, C., &amp; Brändle, T. (2025). "
            "<em>Determinants of Healthcare Expenditure: "
            "Evidence from Switzerland between 1960–2022</em>. "
            "Federal Finance Administration Working Paper No. 27. "
            "Berne: FFA. "
            "Retrieved from https://www.efv.admin.ch"
        ),
        "note": (
            "Time-series analysis (1960–2022) identifying income growth (~50%), "
            "population ageing (~15%), and Baumol's cost disease as the main drivers "
            "of healthcare expenditure growth in Switzerland — cited to contextualise "
            "rising OKP premium burdens and the growing generational transfer imbalance "
            "in the Who Pays section."
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
        "note": (
            "Classic argument that unequal voter turnout systematically distorts "
            "democratic representation toward older citizens — not through manipulation, "
            "but through silence."
        ),
    },
    {
        "key": "Obsan2023",
        "citation": (
            "Peter, C., Tuch, A., &amp; Schuler, D. (2023). "
            "<em>Psychische Gesundheit in der Schweiz: Obsan Bericht 03/2023</em>. "
            "Schweizerisches Gesundheitsobservatorium (Obsan). "
            "Retrieved from https://www.obsan.admin.ch/sites/default/files/2023-05/Obsan_03_2023_BERICHT.pdf"
        ),
        "note": (
            "National health survey documenting a significant deterioration in mental health "
            "since 2017, with 15–24 year-olds among the hardest hit — used to contextualise "
            "the rise in political disengagement among younger generations."
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
        "note": (
            "Introduces the Martini-Glass narrative structure applied in the "
            "layout of each dashboard section."
        ),
    },
    {
        "key": "UBSSorgenbarometer2025",
        "citation": (
            "gfs.bern. (2025). "
            "<em>UBS Sorgenbarometer 2025: Die Schweiz in Zeiten internationalen Drucks</em>. "
            "Im Auftrag der UBS. Bern: gfs.bern. "
            "Retrieved from https://www.gfsbern.ch/de/news/ubs-sorgenbarometer-2025/"
        ),
        "note": (
            "Representative survey of 2,190 Swiss voters (July–August 2025) conducted by "
            "gfs.bern on behalf of UBS. Found that healthcare costs remain the top concern "
            "for 45% of the Swiss population — cited to contextualise the premium burden "
            "across generations in the Who Pays section."
        ),
    },
    {
        "key": "UNICEF2021",
        "citation": (
            "UNICEF Schweiz und Liechtenstein. (2021). "
            "<em>Psychische Gesundheit von Jugendlichen in der Schweiz und Liechtenstein</em>. "
            "Conducted by Unisanté. "
            "Retrieved from https://www.unicef.ch/de/was-wir-tun/national/wohlergehen-von-kindern/psychische-gesundheit"
        ),
        "note": (
            "Study of 1 097 adolescents aged 14–19 finding that 37% reported mental health "
            "problems and nearly half rated their psychological wellbeing as worse since the "
            "pandemic — cited in the Who Decides section to contextualise youth disengagement."
        ),
    },
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
        "note": (
            "Defines the four narrative constituents — narrator presence, sequentiality, "
            "temporal dimension, and tellability — that shaped the dashboard's "
            "storytelling structure."
        ),
    },
]


# ─────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────

def render_references_section() -> None:
    st.markdown('<div id="references"></div>', unsafe_allow_html=True)

    for ref in sorted(REFERENCES, key=lambda r: r["key"].lower()):
        st.markdown(
            f"<p style='font-size:0.95rem;line-height:1.65;color:#222222;"
            f"margin-bottom:0.2rem;'>{ref['citation']}</p>"
            f"<p style='font-size:0.82rem;line-height:1.5;color:#777777;"
            f"font-style:italic;margin-bottom:1.4rem;'>{ref['note']}</p>",
            unsafe_allow_html=True,
        )
