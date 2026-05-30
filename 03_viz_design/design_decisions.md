# Design Decisions

## Chart Types per Section

### Who Decides the Rules
| Chart | Type | Why |
|:------|:-----|:----|
| Voter share by generation | Parliament (semicircle) | Familiar metaphor for political representation; makes the dominance of older generations immediately legible |
| Political interest over time | Bump / rank chart | Rank changes are more readable than raw values for cross-generation comparison |
| Democratic satisfaction | Grouped horizontal bar + delta annotation | 3-year comparison with explicit Δ 2015→2023 reduces cognitive load; horizontal layout fits long generation labels |
| Left–right orientation | Dumbbell / arrow plot | Shows movement and endpoint simultaneously; avoids clutter of a full grouped bar |

### Who Pays
| Chart | Type | Why |
|:------|:-----|:----|
| AHV contributions & returns | Bar / area | Magnitude comparison; generations as categories |

### Who Holds the Assets
| Chart | Type | Why |
|:------|:-----|:----|
| Owner vs. renter share | 100% horizontal stacked bar | Proportion is the message; sorting by owner rate left→right makes the gradient visible |
| Living space ranking | Horizontal bar with background track | Absolute values (m²) + generation ordering; background track gives instant sense of scale |
| Ownership vs. living space | Scatter + trend line | Shows the correlation between two continuous variables; r annotation makes the finding quantitative |

---

## General Principles

**One colour per generation, always.** The palette is defined once in `app_config.py` and reused everywhere. No chart uses a second colour scheme.

**Direct labels over legends.** Where possible, generation names are annotated directly on chart elements (line ends, bar labels, scatter points). Legends are only shown when space doesn't allow inline placement.

**Narrative text boxes.** Every chart is followed by a styled insight box that draws the interpretation explicitly — so the chart and the takeaway live together, not in a separate report section.

**White, minimal background.** `plot_bgcolor = "white"`, light grey grid lines (`#eeeeee`), no border decorations. Charts sit inside a broader Streamlit page that already has visual structure.

**Tooltips for detail, annotations for key insights.** Numbers that matter to the story (e.g. Δ satisfaction 2015→2023, correlation r, ownership gap in pp) are annotated directly. Hover tooltips expose raw values on demand.

**Interactive year filter (radio).** Several charts (parliament, stacked bar, living space, scatter) let the user switch between survey/census years via a compact radio button placed directly below the chart.

**Sidebar generation filter.** A shared multiselect in the sidebar controls which generations appear across all sections simultaneously — so the reader can focus on the subset they care about.

---

## Discarded Alternatives

- **Choropleth map (by canton):** Considered for the housing section, dropped because generation is the primary dimension, not geography. Disaggregated canton data also had too many missing cells.
- **Pie / donut charts:** Considered for ownership share. Rejected in favour of the horizontal stacked bar, which allows direct comparison across generations simultaneously.
- **Animated transitions:** Considered for the living space trend. Dropped because the static ranking chart with a year filter is clearer and avoids confusion from the non-crossing lines.
