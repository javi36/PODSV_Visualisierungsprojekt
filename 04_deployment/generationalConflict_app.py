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
    # ── Hero ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero">
            <h1>Generational Conflict</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Intro text ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="narrative-text">
        Switzerland's population is divided into five distinct generations — each with different political weight,
        financial power, and access to housing. While older generations accumulated wealth during decades of low
        interest rates and affordable property, younger cohorts face record rents, rising costs of living, and
        shrinking prospects of ownership. This story follows the numbers: who decides the rules, who bears the
        costs, and who holds the assets.
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

    # Toggle absolute/relative
    view_mode = st.radio(
        "View",
        options=["Absolute", "Relative (%)"],
        horizontal=True,
        key="area_view_mode",
        label_visibility="collapsed",
    )

    try:
        demographic_df = load_demographic_data(DEMOGRAPHIC_DATA_PATH)
        pyramid_data = build_generation_pyramid_data(demographic_df)
    except Exception as exc:
        st.error("Could not load demographic data.")
        st.exception(exc)
        st.stop()

    relative = st.session_state.get("area_view_mode", "Absolute") == "Relative (%)"
    area_from, area_to = DEMOGRAPHIC_YEARS[0], DEMOGRAPHIC_YEARS[-1]

    st.markdown(
        f"<div class='pyramid-subtitle'>{area_from}–{area_to}</div>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        create_generation_area_chart(pyramid_data, area_from, area_to, relative),
        use_container_width=True,
    )

    # ── Navigation buttons ────────────────────────────────────────────────────
    st.markdown(
        "<div class='nav-section-title'>Dive Deeper</div>"
        "<div class='nav-section-subtitle'>Explore each dimension of the generational conflict</div>",
        unsafe_allow_html=True,
    )

    nav_col1, nav_col2, nav_col3 = st.columns(3, gap="large")

    with nav_col1:
        st.markdown(
            """
            <div class="nav-card" style="border-top: 4px solid #0f4c5c;">
                <div class="nav-card-icon">🗳️</div>
                <div class="nav-card-title">Who Decides</div>
                <div class="nav-card-desc">Political power and voting influence across generations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Explore Who Decides →", use_container_width=True, key="btn_decides"):
            st.switch_page("pages/who_decides.py")

    with nav_col2:
        st.markdown(
            """
            <div class="nav-card" style="border-top: 4px solid #f4a259;">
                <div class="nav-card-icon">💸</div>
                <div class="nav-card-title">Who Pays</div>
                <div class="nav-card-desc">Housing cost burden and rent pressure by generation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Explore Who Pays →", use_container_width=True, key="btn_pays"):
            st.switch_page("pages/who_pays.py")

    with nav_col3:
        st.markdown(
            """
            <div class="nav-card" style="border-top: 4px solid #f25c54;">
                <div class="nav-card-icon">🏠</div>
                <div class="nav-card-title">Who Owns</div>
                <div class="nav-card-desc">Homeownership rates and asset distribution in 2024</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Explore Who Owns →", use_container_width=True, key="btn_owns"):
            st.switch_page("pages/who_owns.py")

    st.markdown("<br><br>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
