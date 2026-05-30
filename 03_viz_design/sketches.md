# Sketches & Prototypes

Initial concept sketches were done by hand (Kenan). See the presentation concept document for the original mockups:
`docs/presentation_concept.docx` / `docs/presentation_concept_group3.pdf`

---

## Sketch → Implementation Mapping

| Sketch idea | Implemented as | Notes |
|:------------|:---------------|:------|
| Bar chart showing voting weight by generation | Parliament (semicircle) chart | Changed from bar to semicircle for stronger political metaphor |
| Line chart for interest / trust over time | Bump chart (rank-based) + grouped bar | Raw values replaced by ranks for interest; grouped bar kept for satisfaction |
| Stacked area for housing ownership | 100% horizontal stacked bar | Orientation flipped to horizontal for readability of generation labels |
| Scatter for housing space vs. generation | Scatter: ownership rate × m²/person | Added trend line and r annotation to make the correlation explicit |

---

## Dashboard Layout (final)

Single-page scrollable Streamlit app with four content sections:

1. **Home / Intro** — hero image, generation cards with key facts
2. **Who Decides the Rules** — 4 charts + narrative boxes
3. **Who Bears the Costs** — AHV section
4. **Who Holds the Assets** — 3 charts + narrative boxes

Navigation via sidebar anchor links. Separate references page accessible via `?page=references` query param.

The sidebar also contains a **Control Panel** with a shared generation multiselect — filtering is applied across all sections simultaneously.
