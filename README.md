# Generational Conflict – Interactive Data Dashboard

An interactive Streamlit dashboard exploring intergenerational inequality in Switzerland across three dimensions:

- **Who Decides the Rules** — political power and voting influence across generations
- **Who Bears the Costs** — AHV/pension contributions and returns by generation
- **Who Holds the Assets** — homeownership rates and living space by generation

Built as part of the course *Project-oriented Digital Storystelling and Visualisation* (PODSV), FS 2026.

---

## Quick Start: Run the App

```bash
# 1. Install dependencies (once)
uv sync

# 2. Start the Streamlit app
uv run streamlit run 04_deployment/app.py
```

The app opens at `http://localhost:8501`.

---

## Project Structure

```
.
├── 01_data_acquisition/        # Scripts to load and prepare raw data
│   ├── load_sources.py
│   └── load_whopays_final.py
├── 02_eda/                     # Exploratory data analysis notebooks
│   ├── eda_whopays.ipynb
│   ├── eda_whoowns.ipynb
│   └── eda_whodecide.ipynb
├── 03_viz_design/              # Design sketches and visual mapping decisions
├── 04_deployment/              # Streamlit app (main entry point: app.py)
│   ├── app.py                  ← start here
│   ├── app_config.py           # Paths, colours, generation config
│   ├── generationalConflict_app.py  # Home/intro section
│   ├── demographic_section.py
│   ├── who_decides_section.py
│   ├── who_pays_section.py
│   ├── who_owns_section.py
│   └── references.py
├── data/                       # All datasets (raw + processed)
│   ├── demografischeBilanz.csv
│   ├── whodecide/
│   ├── whoOwns/
│   └── raw/
└── docs/                       # Quarto documentation website
    ├── 00_project_charta.qmd
    ├── 01_data_report.qmd
    ├── 03_viz_design_report.qmd
    ├── 04_deployment.qmd
    └── 05_evaluation.qmd
```

---

## Python Environment (uv)

Make sure [uv](https://docs.astral.sh/uv/getting-started/installation/) is installed, then:

```bash
uv sync          # create/update the virtual environment
uv add <pkg>     # add a new dependency
uv remove <pkg>  # remove a dependency
```

Always prefix Python commands with `uv run`, e.g.:

```bash
uv run python script.py
uv run jupyter notebook
uv run streamlit run 04_deployment/app.py
```

Or activate once per session:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

---

## Environment Variables

Secrets and local config go in a `.env` file (never committed). Copy the template:

```bash
cp .env.template .env   # then edit as needed
```

Usage in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()
value = os.environ['MY_VAR']
```

---

## Documentation Website (Quarto)

The `docs/` folder is a Quarto website covering all project phases.

```bash
cd docs

# Preview locally (live reload)
uv run quarto preview

# Build static site → docs/build/
uv run quarto render
```

Open `docs/build/index.html` in a browser to check the result.

### Deploy to GitHub Pages

Every push to `main` triggers `.github/workflows/publish.yml`, which renders and deploys automatically.

Before the first push, render locally so `docs/_freeze` is populated:

```bash
cd docs && uv run quarto render
git add docs/_freeze && git commit -m "add freeze cache"
git push
```

Then enable GitHub Pages in **Settings > Pages > Source: GitHub Actions**.

---

## Process Model

| Phase | Folder | Docs file |
|:------|:-------|:----------|
| Project Understanding | — | `docs/00_project_charta.qmd` |
| Data Acquisition & EDA | `01_data_acquisition/`, `02_eda/` | `docs/01_data_report.qmd` |
| Visual Encoding & Design | `03_viz_design/` | `docs/03_viz_design_report.qmd` |
| Deployment | `04_deployment/` | `docs/04_deployment.qmd` |
| Evaluation | — | `docs/05_evaluation.qmd` |
