####### NEU: Starten über app.py und nicht diese py-Datei direkt! #######
import streamlit as st

from app_config import (
    DEMOGRAPHIC_DATA_PATH,
    DEMOGRAPHIC_YEARS,
    load_demographic_data,
)
from demographic_section import (
    build_generation_pyramid_data,
    create_generation_area_chart,
)

GENERATION_META: dict[str, dict] = {
    "Silent Generation": {
        "years": "born ≤ 1945",
        "age": "79+ years",
        "facts": [
            "Witnessed WWII & reconstruction",
            "Smallest generation in CH",
            "Fully reliant on AHV pension",
            "Built Swiss prosperity",
        ],
        "color": "#0f4c5c",
    },
    "Babyboomers": {
        "years": "born 1946–1964",
        "age": "60–78 years",
        "facts": [
            "Post-war economic boom",
            "Highest homeownership rate",
            "Dominate political power",
            "At or near retirement",
        ],
        "color": "#1d7874",
    },
    "Generation X": {
        "years": "born 1965–1980",
        "age": "44–59 years",
        "facts": [
            "Grew up without internet",
            "Peak earning years",
            "Caring for aging parents",
            "Often called forgotten gen",
        ],
        "color": "#679289",
    },
    "Millennials / Gen Y": {
        "years": "born 1981–1996",
        "age": "28–43 years",
        "facts": [
            "Shaped by 2008 crisis",
            "Most educated generation",
            "Renting, not buying",
            "True digital natives",
        ],
        "color": "#f4a259",
    },
    "Generation Z": {
        "years": "born 1997–2012",
        "age": "12–27 years",
        "facts": [
            "Born with smartphones",
            "Climate-focused generation",
            "Growing voting power",
            "Facing housing shortage",
        ],
        "color": "#f25c54",
    },
}


def main() -> None:
    st.markdown('<div id="home"></div>', unsafe_allow_html=True)

    # ── Hero ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero">
            <h1>Generational Conflict</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div style='text-align:center; margin: 2rem 0 1.5rem;'>
            <p style='font-size:1.1rem; font-style:italic; color:#333333;'>
            «Im Bewusstsein der gemeinsamen Errungenschaften und der Verantwortung
            gegenüber den künftigen Generationen»
            </p>
            <p style='font-size:0.85rem; font-style:italic; color:#aaaaaa; margin-top:0.2rem;'>
            "Aware of our common achievements and of our responsibility
            towards future generations."
            </p>
            <p style='font-size:0.8rem; color:#aaaaaa; margin-top:0.3rem;'>
            — Präambel, Bundesverfassung der Schweizerischen Eidgenossenschaft (SR 101, 1999)
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Intro text ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="narrative-text">
        The Preamble of the Swiss Federal Constitution is unusually honest about what a society owes its future. 
        It commits the Swiss people to act in awareness of their responsibility towards future generations — not as an aspiration, 
        but as a founding principle alongside freedom, democracy, and solidarity. 
        Yet the same Preamble reminds us that the strength of a people is measured by the wellbeing of its weakest members. 
        This dashboard asks a harder version of that question: is Switzerland honouring that commitment — or quietly shifting 
        the burden onto those who had no voice when the rules were written? <b>Who decides the rules? Who bears the costs? Who holds the assets?</b><br><br>
        To understand the conflict, you first need to know the players — five generations that share the same country but inherit very different 
        versions of it, shaped by the decade they were born into, the economy they entered, and the social system they found waiting for them.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Generation fact cards ─────────────────────────────────────────────────
    gen_cols = st.columns(5, gap="small")
    for col, (gen_name, meta) in zip(gen_cols, GENERATION_META.items()):
        facts_html = "".join(f"<li>{f}</li>" for f in meta["facts"])
        with col:
            st.markdown(
                f"""
                <div class="gen-card" style="border-top: 5px solid {meta['color']}; min-height: 380px;">
                    <div class="gen-card-name">{gen_name}</div>
                    <div class="gen-card-years">{meta['years']}</div>
                    <div class="gen-card-age">{meta['age']}</div>
                    <ul class="gen-card-facts">{facts_html}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Demographic balance (stacked area) ───────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div class='pyramid-title'>Demographic Balance of Switzerland</div>", unsafe_allow_html=True)

    try:
        demographic_df = load_demographic_data(DEMOGRAPHIC_DATA_PATH)
        pyramid_data = build_generation_pyramid_data(demographic_df)
    except Exception as exc:
        st.error("Could not load demographic data.")
        st.exception(exc)
        st.stop()

    area_from, area_to = DEMOGRAPHIC_YEARS[0], DEMOGRAPHIC_YEARS[-1]

    st.markdown(
        f"<div class='pyramid-subtitle'>{area_from}–{area_to}</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        create_generation_area_chart(pyramid_data, area_from, area_to),
        use_container_width=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

   
