# =========================================
# Load and prepare AHV income data for WhoPays analysis.
# Source: ahv_einnahmen_zhaw.xlsx – employee records only (Arbeitnehmende).
# =========================================

from pathlib import Path
import pandas as pd
import re
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# -----------------------------------------
# 1. Define Paths and Constants
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

RAW_AHV_PATH        = BASE_PATH / "data" / "whopays" / "raw_whopays" / "ahv_einnahmen_zhaw.xlsx"
RAW_POPULATION_PATH = BASE_PATH / "data" / "raw" / "px-x-0102020000_103_20260424-164251.xlsx"

PROCESSED_WHOPAYS_PATH = BASE_PATH / "data" / "whopays" / "processed_whopays"

PROCESSED_WHOPAYS_PATH.mkdir(parents=True, exist_ok=True)

# Generation definitions: (birth_year_min, birth_year_max, label, order)
_GENERATIONS: list[tuple[int, int, str, int]] = [
    (0,    1945, "Silent Generation", 1),
    (1946, 1964, "Babyboomers",       2),
    (1965, 1980, "Generation X",      3),
    (1981, 1996, "Millennials",       4),
    (1997, 2012, "Generation Z",      5),
    (2013, 9999, "Generation Alpha",  6),
]

# Tabelle 1 column → (metric, scale, unit)
_COL_SPECS: list[tuple[str, str, str, str]] = [
    ("n_personen",      "n_personen",      "count", "Anzahl"),
    ("sum_einkommen",   "sum_einkommen",   "chf",   "CHF"),
    ("sum_beitrag_ahv", "sum_beitrag_ahv", "chf",   "CHF"),
]

# Methodological note: data covers employees only
_NOTE = "nur_arbeitnehmende"


# -----------------------------------------
# 2. Helper Functions
# -----------------------------------------

def _sep() -> None:
    """Print section separator."""
    print("\n" + "=" * 50)


def map_generation(birth_year: int) -> tuple[str, int]:
    """
    Map a birth year to its generation label and sort order.

    Args:
        birth_year: Four-digit birth year.

    Returns:
        Tuple of (generation_label, order).
    """
    for by_min, by_max, label, order in _GENERATIONS:
        if by_min <= birth_year <= by_max:
            return label, order
    return "Unknown", 0


def parse_ahv_age_group(label: str) -> tuple[int | None, int | None]:
    """
    Parse an AHV age-group label into (age_min, age_max).

    Recognised patterns:
    - "<20"   → (0, 19)
    - "X-Y"   → (X, Y)   e.g. "20-24", "65-69"
    - "X+"    → (X, 100) e.g. "75+"

    Returns (None, None) for "Total", "Fehlend" or unrecognised strings.

    Args:
        label: Raw altersgruppe value from Tabelle 1.

    Returns:
        (age_min, age_max) as ints, or (None, None) if the row should be skipped.
    """
    if not isinstance(label, str):
        return None, None
    label = label.strip()

    if label.lower() in ("total", "fehlend", ""):
        return None, None

    # "<20"
    m = re.match(r"^<\s*(\d+)$", label)
    if m:
        return 0, int(m.group(1)) - 1

    # "X+" open upper bound
    m = re.match(r"^(\d+)\+$", label)
    if m:
        return int(m.group(1)), 100

    # "X-Y" range
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", label)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None, None


# -----------------------------------------
# 3. Population Data Loader
# -----------------------------------------

def load_population_data(path: Path) -> pd.DataFrame:
    """
    Load BFS population data from the px-x xlsx Cube file.

    Year is forward-filled from column 0 (4-digit integers).
    Age is read from column 4.
    pop_jan1 = column 5; pop_dec31 = column 17.
    pop_avg = (pop_jan1 + pop_dec31) / 2.

    Falls back to BASE_PATH/data/<filename> if the primary path is missing.

    Args:
        path: Expected path to the xlsx population file.

    Returns:
        DataFrame with columns: year (int), age (int), pop_avg (float).

    Raises:
        FileNotFoundError: If the file cannot be located.
        ValueError: If no year rows are detected in column 0.
    """
    _sep()
    print("LOADING POPULATION DATA")
    print("=" * 50)

    if not path.exists():
        alt = BASE_PATH / "data" / path.name
        if alt.exists():
            path = alt
            print(f"⚠️  Fallback population path used: {path}")
        else:
            print(f"❌ Population file not found: {path}")
            raise FileNotFoundError(f"Population file not found: {path}")

    print(f"📂 Loading from: {path}")

    df_raw = pd.read_excel(path, header=None, dtype=object)

    col0_num = pd.to_numeric(df_raw.iloc[:, 0], errors="coerce")
    df_raw["_year_ff"] = col0_num.where(col0_num.between(1990, 2030)).ffill()
    df_data = df_raw[df_raw["_year_ff"].notna()].copy()

    if df_data.empty:
        raise ValueError(
            "Could not detect year rows in population file. "
            "Column 0 must contain 4-digit year integers (1990–2030)."
        )

    df_data["year"]     = df_data["_year_ff"].astype(int)
    df_data["age"]      = pd.to_numeric(
        df_data.iloc[:, 4].astype(str).str.extract(r"^(\d+)")[0],
        errors="coerce",
    )
    df_data["pop_jan1"] = pd.to_numeric(df_data.iloc[:, 5],  errors="coerce")
    df_data["pop_dec31"]= pd.to_numeric(df_data.iloc[:, 17], errors="coerce")
    df_data["pop_avg"]  = (df_data["pop_jan1"] + df_data["pop_dec31"]) / 2

    result = (
        df_data[["year", "age", "pop_avg"]]
        .dropna(subset=["year", "age", "pop_avg"])
        .copy()
    )
    result["age"]  = result["age"].astype(int)
    result["year"] = result["year"].astype(int)
    result = result.reset_index(drop=True)

    print(
        f"✓ Population loaded: years {result['year'].min()}–{result['year'].max()}, "
        f"ages {result['age'].min()}–{result['age'].max()}, "
        f"{len(result):,} rows"
    )
    return result


# -----------------------------------------
# 4. AHV Data Loaders
# -----------------------------------------

def load_tabelle1(path: Path) -> pd.DataFrame:
    """
    Load Tabelle 1 from the AHV xlsx: beitragspflichtige Personen by age and year.

    Keeps only rows where geschlecht == "Total" and excludes altersgruppe
    values "Total" and "Fehlend".

    Args:
        path: Path to ahv_einnahmen_zhaw.xlsx.

    Returns:
        Filtered DataFrame with columns:
        jahr, altersgruppe, n_personen, sum_einkommen, sum_beitrag_ahv.
    """
    _sep()
    print("LOADING AHV TABELLE 1")
    print("=" * 50)

    df = pd.read_excel(path, sheet_name="Tabelle 1")
    print(f"📂 Raw rows: {len(df)}")

    df = df[df["geschlecht"] == "Total"].copy()
    df = df[~df["altersgruppe"].isin(["Total", "Fehlend"])].copy()

    df = df[["jahr", "altersgruppe", "n_personen", "sum_einkommen", "sum_beitrag_ahv"]].copy()
    df.rename(columns={"jahr": "year"}, inplace=True)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)

    print(f"✓ Filtered: {len(df)} rows | years {df['year'].min()}–{df['year'].max()}")
    return df.reset_index(drop=True)


def load_tabelle2(path: Path) -> pd.DataFrame:
    """
    Load Tabelle 2: macro AHV contribution totals from the Betriebsrechnung.

    Args:
        path: Path to ahv_einnahmen_zhaw.xlsx.

    Returns:
        DataFrame with columns: year, variable_name, metric, value, unit, scale.
    """
    _sep()
    print("LOADING AHV TABELLE 2 (Makro)")
    print("=" * 50)

    df = pd.read_excel(path, sheet_name="Tabelle 2")
    df.rename(columns={"jahr": "year"}, inplace=True)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)

    records = []
    for _, row in df.iterrows():
        val = pd.to_numeric(row["sum_beitrag_ahv_betriebsrechnung"], errors="coerce")
        if pd.isna(val):
            continue
        records.append(
            {
                "year":          int(row["year"]),
                "variable_name": "ahv_makro",
                "metric":        "sum_beitrag_ahv_betriebsrechnung",
                "value":         float(val),
                "unit":          "CHF",
                "scale":         "chf",
            }
        )

    df_out = pd.DataFrame(records)
    print(f"✓ Makro: {len(df_out)} rows | years {df_out['year'].min()}–{df_out['year'].max()}")
    return df_out


# -----------------------------------------
# 5. Cohort Conversion (wide → long)
# -----------------------------------------

def build_cohort(df_t1: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Tabelle 1 to long-format cohort records.

    One row per (year, altersgruppe, metric). Age bounds are parsed from the
    altersgruppe label. All rows carry notes = "nur_arbeitnehmende".

    Args:
        df_t1: Filtered Tabelle 1 DataFrame from load_tabelle1().

    Returns:
        Long-format DataFrame with columns:
        year, variable_name, age_group_label, age_min, age_max,
        metric, value, unit, scale, notes.
    """
    _sep()
    print("BUILDING COHORT LONG FORMAT")
    print("=" * 50)

    records: list[dict] = []
    skipped = 0

    for _, row in df_t1.iterrows():
        label = str(row["altersgruppe"]).strip()
        age_min, age_max = parse_ahv_age_group(label)
        if age_min is None:
            skipped += 1
            continue

        for col, metric, scale, unit in _COL_SPECS:
            val = pd.to_numeric(row[col], errors="coerce")
            if pd.isna(val):
                continue
            records.append(
                {
                    "year":            int(row["year"]),
                    "variable_name":   "ahv_einnahmen",
                    "age_group_label": label,
                    "age_min":         age_min,
                    "age_max":         age_max,
                    "metric":          metric,
                    "value":           float(val),
                    "unit":            unit,
                    "scale":           scale,
                    "notes":           _NOTE,
                }
            )

    df_out = pd.DataFrame(records)
    print(
        f"✓ Cohort: {len(df_out)} rows | {df_out['year'].nunique()} years | "
        f"{skipped} rows skipped (unparseable age label)"
    )
    return df_out


# -----------------------------------------
# 6. Disaggregation
# -----------------------------------------

def _make_disagg_record(
    base: dict, year: int, age: int, value: float, method: str
) -> dict:
    """
    Build a single disaggregated birth-year record from a cohort row.

    Args:
        base:   Source cohort record dict.
        year:   Reference year.
        age:    Single age (years).
        value:  Disaggregated metric value.
        method: "pop_weighted" or "equal_distribution".

    Returns:
        Record dict enriched with age, birth_year, generation fields, and method.
    """
    birth_year = year - age
    gen_label, gen_order = map_generation(birth_year)
    r = base.copy()
    r.update(
        {
            "age":               age,
            "birth_year":        birth_year,
            "project_age_group": gen_label,
            "project_age_order": gen_order,
            "method":            method,
            "value":             value,
        }
    )
    return r


def disaggregate_to_single_age(
    df_cohort: pd.DataFrame,
    pop_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Disaggregate cohort-level AHV data to single-age / birth-year rows.

    Both "chf" and "count" scales use population-weighted disaggregation.
    Falls back to equal distribution when population data are unavailable.

    Adds columns: age, birth_year, project_age_group, project_age_order, method.

    Args:
        df_cohort: Cohort-level long-format DataFrame.
        pop_df:    Population reference DataFrame (year, age, pop_avg).

    Returns:
        Single-age long-format DataFrame.
    """
    _sep()
    print("DISAGGREGATING TO SINGLE AGE / BIRTH YEAR")
    print("=" * 50)

    pop_lookup: dict[tuple[int, int], float] = {
        (int(r.year), int(r.age)): float(r.pop_avg)
        for r in pop_df.itertuples(index=False)
    }

    records: list[dict] = []

    for _, row in df_cohort.iterrows():
        year    = int(row["year"])
        age_min = int(row["age_min"])
        age_max = int(row["age_max"])
        value   = float(row["value"])

        ages = list(range(age_min, min(age_max, 100) + 1))
        if not ages:
            continue

        base = row.to_dict()

        weights = {a: pop_lookup.get((year, a)) for a in ages}
        valid   = {a: w for a, w in weights.items() if w is not None}
        total_w = sum(valid.values())

        if total_w > 0:
            method = "pop_weighted"
            for age in ages:
                w    = valid.get(age, 0.0)
                frac = w / total_w
                records.append(_make_disagg_record(base, year, age, value * frac, method))
        else:
            method = "equal_distribution"
            share = value / len(ages)
            for age in ages:
                records.append(_make_disagg_record(base, year, age, share, method))

    df_out = pd.DataFrame(records)
    print(
        f"✓ Disaggregated: {len(df_cohort):,} cohort rows → "
        f"{len(df_out):,} single-age rows"
    )
    return df_out


# -----------------------------------------
# 7. Plausibility Checks
# -----------------------------------------

def run_plausibility_check(
    df_cohort: pd.DataFrame,
    df_birth_year: pd.DataFrame,
    df_makro: pd.DataFrame,
) -> None:
    """
    Run two plausibility checks:

    1. Disaggregation totals: for each (year, metric) with scale == "chf",
       verify that the sum of single-age rows matches the cohort total within
       0.01% tolerance.

    2. Macro comparison: compare the aggregated sum_beitrag_ahv from the
       cohort (Tabelle 1, employees only) against the Betriebsrechnung total
       from Tabelle 2. The expected gap reflects excluded self-employed and
       non-working persons.

    Args:
        df_cohort:    Cohort-level long-format DataFrame.
        df_birth_year: Disaggregated single-age DataFrame.
        df_makro:     Macro control values from Tabelle 2.
    """
    _sep()
    print("PLAUSIBILITY CHECKS")
    print("=" * 50)

    # Check 1: disaggregation totals
    chf_cohort = df_cohort[df_cohort["scale"] == "chf"]
    chf_disagg = df_birth_year[df_birth_year["scale"] == "chf"]

    grp = ["year", "metric"]
    cohort_sums = chf_cohort.groupby(grp)["value"].sum()
    disagg_sums = chf_disagg.groupby(grp)["value"].sum()

    mismatches = 0
    for key, expected in cohort_sums.items():
        if key not in disagg_sums.index:
            print(f"   ⚠️  Missing in disaggregated output: {key}")
            mismatches += 1
            continue
        actual  = disagg_sums[key]
        rel_err = abs(actual - expected) / abs(expected) if expected != 0 else 0.0
        if rel_err > 0.0001:
            print(
                f"   ⚠️  {key}: expected {expected:.2f}, got {actual:.2f} "
                f"(rel. error {rel_err:.4%})"
            )
            mismatches += 1

    total_checks = len(cohort_sums)
    if mismatches == 0:
        print(f"   ✓ Disaggregation: all {total_checks} checks passed (< 0.01 %)")
    else:
        print(f"   ⚠️  Disaggregation: {mismatches}/{total_checks} check(s) exceeded tolerance")

    # Check 2: Tabelle 1 vs Tabelle 2 macro comparison
    print()
    t1_beitrag = (
        df_cohort[df_cohort["metric"] == "sum_beitrag_ahv"]
        .groupby("year")["value"]
        .sum()
    )
    t2_beitrag = df_makro.set_index("year")["value"]

    common_years = sorted(set(t1_beitrag.index) & set(t2_beitrag.index))
    if not common_years:
        print("   ⚠️  No overlapping years between Tabelle 1 and Tabelle 2")
        return

    print("   Tabelle 1 vs Tabelle 2 – sum_beitrag_ahv (expected gap: employees only):")
    for yr in common_years:
        t1_val = t1_beitrag[yr]
        t2_val = t2_beitrag[yr]
        pct    = (t1_val / t2_val - 1) * 100 if t2_val != 0 else float("nan")
        print(
            f"   {yr}: T1={t1_val/1e9:.3f} Mrd | T2={t2_val/1e9:.3f} Mrd | "
            f"Diff={pct:+.1f}%"
        )


# -----------------------------------------
# 8. Main Pipeline
# -----------------------------------------

def run_ahv_einnahmen_pipeline() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Execute the full AHV Einnahmen pipeline.

    Steps:
    1. Ensure output directory exists.
    2. Load BFS population reference data.
    3. Load and filter Tabelle 1 (employee AHV records by age group).
    4. Load Tabelle 2 (macro Betriebsrechnung totals).
    5. Convert Tabelle 1 to long-format cohort.
    6. Save ahv_einnahmen_cohort.csv.
    7. Disaggregate cohort to single age / birth year.
    8. Save ahv_einnahmen_by_birth_year.csv.
    9. Save ahv_makro.csv.
    10. Run plausibility checks.

    Returns:
        Tuple of (df_cohort, df_birth_year, df_makro).
    """
    PROCESSED_WHOPAYS_PATH.mkdir(parents=True, exist_ok=True)

    _sep()
    print("AHV EINNAHMEN PIPELINE START")
    print("=" * 50)

    if not RAW_AHV_PATH.exists():
        print(f"❌ AHV input file not found: {RAW_AHV_PATH}")
        raise FileNotFoundError(f"AHV input file not found: {RAW_AHV_PATH}")

    # Population reference
    pop_df = load_population_data(RAW_POPULATION_PATH)

    # Source tables
    df_t1    = load_tabelle1(RAW_AHV_PATH)
    df_makro = load_tabelle2(RAW_AHV_PATH)

    # Cohort output
    df_cohort = build_cohort(df_t1)
    cohort_path = PROCESSED_WHOPAYS_PATH / "ahv_einnahmen_cohort.csv"
    df_cohort.to_csv(cohort_path, index=False)

    _sep()
    print(f"✓ ahv_einnahmen_cohort.csv saved: {cohort_path}")
    print(
        f"   {len(df_cohort):,} rows | "
        f"{df_cohort['year'].nunique()} years | "
        f"{df_cohort['metric'].nunique()} metrics"
    )

    # Single-age / birth-year output
    df_birth_year = disaggregate_to_single_age(df_cohort, pop_df)
    birth_year_path = PROCESSED_WHOPAYS_PATH / "ahv_einnahmen_by_birth_year.csv"
    df_birth_year.to_csv(birth_year_path, index=False)

    _sep()
    print(f"✓ ahv_einnahmen_by_birth_year.csv saved: {birth_year_path}")
    print(f"   {len(df_birth_year):,} rows")

    # Macro output
    makro_path = PROCESSED_WHOPAYS_PATH / "ahv_makro.csv"
    df_makro.to_csv(makro_path, index=False)
    print(f"✓ ahv_makro.csv saved: {makro_path}")

    # Quality checks
    run_plausibility_check(df_cohort, df_birth_year, df_makro)

    _sep()
    print("AHV EINNAHMEN PIPELINE COMPLETE ✓")
    print("=" * 50)

    return df_cohort, df_birth_year, df_makro


# -----------------------------------------
# 9. Entry Point
# -----------------------------------------

if __name__ == "__main__":
    try:
        df_c, df_b, df_m = run_ahv_einnahmen_pipeline()
        print(
            f"\n✓ Done: {len(df_c):,} cohort rows, "
            f"{len(df_b):,} birth-year rows, "
            f"{len(df_m):,} macro rows"
        )
    except Exception as exc:
        print(f"\n❌ Pipeline failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
