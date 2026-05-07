# =========================================
# Load and prepare AHV pension output data for WhoPays analysis.
# Source: px-x-1305000000_103 – Anzahl Renten, Rentensumme, Mittelwert
# Data are already at single-age level; no disaggregation required.
# =========================================

from pathlib import Path
import pandas as pd
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# -----------------------------------------
# 1. Define Paths and Constants
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

RAW_AHV_AUSGABEN_PATH = (
    BASE_PATH / "data" / "whopays" / "raw_whopays"
    / "px-x-1305000000_103_20260416-235225.xlsx"
)
PROCESSED_WHOPAYS_PATH = BASE_PATH / "data" / "whopays" / "processed_whopays"

PROCESSED_WHOPAYS_PATH.mkdir(parents=True, exist_ok=True)

# Block number in col 0 → (variable_name, metric, scale, unit)
_BLOCK_DEFS: dict[str, tuple[str, str, str, str]] = {
    "1": ("ahv_ausgaben", "anzahl_renten",           "count",       "Anzahl"),
    "2": ("ahv_ausgaben", "rentensumme_tausend_chf",  "tausend_chf", "CHF"),
    "3": ("ahv_ausgaben", "renten_mittelwert_chf",    "chf",         "CHF"),
}

# Column index of the age integer in data rows
_AGE_COL = 6

# First year column and year range to keep
_FIRST_YEAR_COL = 8       # col 8 = 2001
_FIRST_YEAR     = 2001
_KEEP_FROM_YEAR = 2012
_KEEP_TO_YEAR   = 2024

# Methodological note
_NOTE = "altersrenten_ab_65"

# Generation definitions: (birth_year_min, birth_year_max, label, order)
_GENERATIONS: list[tuple[int, int, str, int]] = [
    (0,    1945, "Silent Generation", 1),
    (1946, 1964, "Babyboomers",       2),
    (1965, 1980, "Generation X",      3),
    (1981, 1996, "Millennials",       4),
    (1997, 2012, "Generation Z",      5),
    (2013, 9999, "Generation Alpha",  6),
]


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


def _parse_age(val: object) -> int | None:
    """
    Parse a raw cell value from the age column (col 6) to an integer.

    Accepts plain integers and floats; rejects NaN, '¯99999', and strings
    that cannot be converted.

    Args:
        val: Raw cell value from col 6.

    Returns:
        Integer age, or None if the row is not a data row.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s in ("", "¯99999", "nan"):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _to_float(val: object) -> float | None:
    """
    Coerce a raw cell value to float, returning None on failure.

    Args:
        val: Raw cell value.

    Returns:
        Float or None.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# -----------------------------------------
# 3. Core Parser
# -----------------------------------------

def _find_block_rows(df: pd.DataFrame) -> dict[str, int]:
    """
    Locate block header rows by scanning col 0 for '1', '2', '3'.

    Args:
        df: Raw DataFrame (header=None, dtype=object).

    Returns:
        Dict mapping block key ('1', '2', '3') to its row index.
    """
    blocks: dict[str, int] = {}
    for row_idx in range(len(df)):
        v = str(df.iloc[row_idx, 0]).strip()
        if v in _BLOCK_DEFS:
            blocks[v] = row_idx
    return blocks


def _extract_first_subblock(
    df: pd.DataFrame,
    block_start: int,
    block_end: int,
    year_col_map: dict[int, int],
    variable_name: str,
    metric: str,
    scale: str,
    unit: str,
) -> list[dict]:
    """
    Extract data rows from the first sub-block (Geschlecht - Total,
    Staatsangehörigkeit - Total) of a single block.

    Data rows are identified by a valid integer in col 6 (age).
    Collection stops at the first row where col 6 is not a valid age
    (i.e. a new sub-block header appears with col 6 = '¯99999' or NaN).

    Args:
        df:            Raw DataFrame.
        block_start:   Row index of the block header (inclusive, skipped).
        block_end:     Row index of the next block or end of data (exclusive).
        year_col_map:  {year: col_index} for the years to keep.
        variable_name: e.g. "ahv_ausgaben".
        metric:        e.g. "anzahl_renten".
        scale:         e.g. "count".
        unit:          e.g. "Anzahl".

    Returns:
        List of long-format record dicts.
    """
    records: list[dict] = []

    for row_idx in range(block_start + 1, block_end):
        age = _parse_age(df.iloc[row_idx, _AGE_COL])
        if age is None:
            # First non-data row → end of first sub-block
            break

        birth_year_base = None  # computed per year below
        gen_label = None
        gen_order = None

        for year, col_idx in year_col_map.items():
            value = _to_float(df.iloc[row_idx, col_idx])
            if value is None:
                continue

            birth_year = year - age
            if gen_label is None:
                gen_label, gen_order = map_generation(birth_year)
                birth_year_base = birth_year

            records.append(
                {
                    "year":               year,
                    "variable_name":      variable_name,
                    "age":                age,
                    "birth_year":         birth_year,
                    "project_age_group":  gen_label if year == list(year_col_map)[0]
                                          else map_generation(birth_year)[0],
                    "project_age_order":  gen_order if year == list(year_col_map)[0]
                                          else map_generation(birth_year)[1],
                    "metric":             metric,
                    "value":              value,
                    "unit":               unit,
                    "scale":              scale,
                    "notes":              _NOTE,
                }
            )

    return records


def parse_ausgaben_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the single px-x sheet into a tidy long-format DataFrame.

    Steps:
    1. Build year → column index map from row 2, filtered to 2012–2024.
    2. Locate the three block header rows (Anzahl, Rentensumme, Mittelwert).
    3. For each block, extract the first sub-block (Total × Total).
    4. Compute birth_year and generation for every (year, age) combination.

    Args:
        df: Raw sheet DataFrame read with header=None, dtype=object.

    Returns:
        Long-format DataFrame with columns:
        year, variable_name, age, birth_year, project_age_group,
        project_age_order, metric, value, unit, scale, notes.
    """
    # Build year → col_index map (row 2, cols 8–31)
    year_col_map: dict[int, int] = {}
    for col_idx in range(_FIRST_YEAR_COL, df.shape[1]):
        raw_year = df.iloc[2, col_idx]
        try:
            yr = int(float(str(raw_year).strip()))
        except (ValueError, TypeError):
            continue
        if _KEEP_FROM_YEAR <= yr <= _KEEP_TO_YEAR:
            year_col_map[yr] = col_idx

    print(f"   Years mapped: {sorted(year_col_map.keys())}")

    # Locate block headers
    block_rows = _find_block_rows(df)
    if len(block_rows) != 3:
        raise ValueError(
            f"Expected 3 block headers (col 0 in {{1,2,3}}), "
            f"found: {block_rows}"
        )
    print(f"   Block header rows: {block_rows}")

    ordered_keys = sorted(block_rows.keys())
    all_records: list[dict] = []

    for i, key in enumerate(ordered_keys):
        block_start = block_rows[key]
        # End = next block start, or end of DataFrame
        if i + 1 < len(ordered_keys):
            block_end = block_rows[ordered_keys[i + 1]]
        else:
            block_end = len(df)

        variable_name, metric, scale, unit = _BLOCK_DEFS[key]
        recs = _extract_first_subblock(
            df, block_start, block_end,
            year_col_map, variable_name, metric, scale, unit,
        )
        print(f"   ✓ Block {key} ({metric}): {len(recs)} rows extracted")
        all_records.extend(recs)

    df_out = pd.DataFrame(all_records)

    # Recompute generation per row (birth_year changes with year)
    if not df_out.empty:
        gen_cols = df_out.apply(
            lambda r: pd.Series(map_generation(int(r["birth_year"]))),
            axis=1,
        )
        df_out[["project_age_group", "project_age_order"]] = gen_cols

    return df_out


# -----------------------------------------
# 4. Plausibility Check
# -----------------------------------------

def run_plausibility_check(df: pd.DataFrame) -> None:
    """
    Verify internal consistency of the three metrics per (year, age).

    For each (year, age): rentensumme_tausend_chf × 1000 / anzahl_renten
    should approximate renten_mittelwert_chf within 1% tolerance.

    Mismatches are logged as WARNING; a summary is printed at the end.

    Args:
        df: Long-format ausgaben DataFrame (all three metrics present).
    """
    _sep()
    print("PLAUSIBILITY CHECK (Rentensumme / Anzahl ≈ Mittelwert)")
    print("=" * 50)

    pivot = df.pivot_table(
        index=["year", "age"],
        columns="metric",
        values="value",
        aggfunc="first",
    )

    required = {"anzahl_renten", "rentensumme_tausend_chf", "renten_mittelwert_chf"}
    if not required.issubset(set(pivot.columns)):
        print("   ⚠️  Not all three metrics present — check skipped.")
        return

    mismatches = 0
    total = 0

    for (year, age), row in pivot.iterrows():
        n   = row["anzahl_renten"]
        rs  = row["rentensumme_tausend_chf"]
        mw  = row["renten_mittelwert_chf"]

        if any(pd.isna(v) or v == 0 for v in (n, rs, mw)):
            continue

        total += 1
        computed_mw = rs * 1000 / n
        rel_err = abs(computed_mw - mw) / abs(mw)

        if rel_err > 0.01:
            print(
                f"   ⚠️  {year} age {age}: "
                f"computed={computed_mw:.0f} CHF, reported={mw:.0f} CHF "
                f"(rel. error {rel_err:.2%})"
            )
            mismatches += 1

    if mismatches == 0:
        print(f"   ✓ All {total} checks passed (< 1 % tolerance)")
    else:
        print(f"   ⚠️  {mismatches}/{total} check(s) exceeded 1 % tolerance")


# -----------------------------------------
# 5. Main Pipeline
# -----------------------------------------

def run_ahv_ausgaben_pipeline() -> pd.DataFrame:
    """
    Execute the full AHV Ausgaben pipeline.

    Steps:
    1. Ensure output directory exists.
    2. Load the raw px-x xlsx sheet.
    3. Parse all three blocks (Anzahl, Rentensumme, Mittelwert) into long format.
    4. Add birth_year and generation columns.
    5. Save ahv_ausgaben_by_age.csv.
    6. Run plausibility check.

    Returns:
        Long-format DataFrame saved to ahv_ausgaben_by_age.csv.

    Raises:
        FileNotFoundError: If the raw input file is absent.
    """
    PROCESSED_WHOPAYS_PATH.mkdir(parents=True, exist_ok=True)

    _sep()
    print("AHV AUSGABEN PIPELINE START")
    print("=" * 50)

    if not RAW_AHV_AUSGABEN_PATH.exists():
        print(f"❌ Input file not found: {RAW_AHV_AUSGABEN_PATH}")
        raise FileNotFoundError(f"Input file not found: {RAW_AHV_AUSGABEN_PATH}")

    print(f"📂 Loading from: {RAW_AHV_AUSGABEN_PATH.name}")
    df_raw = pd.read_excel(
        RAW_AHV_AUSGABEN_PATH, sheet_name=0, header=None, dtype=object
    )
    print(f"   Raw shape: {df_raw.shape}")

    _sep()
    print("PARSING SHEET")
    print("=" * 50)
    df_ausgaben = parse_ausgaben_sheet(df_raw)

    if df_ausgaben.empty:
        print("❌ No records extracted — check raw file structure.")
        return df_ausgaben

    _sep()
    out_path = PROCESSED_WHOPAYS_PATH / "ahv_ausgaben_by_age.csv"
    df_ausgaben.to_csv(out_path, index=False)
    print(f"✓ ahv_ausgaben_by_age.csv saved: {out_path}")
    print(
        f"   {len(df_ausgaben):,} rows | "
        f"ages {int(df_ausgaben['age'].min())}–{int(df_ausgaben['age'].max())} | "
        f"years {int(df_ausgaben['year'].min())}–{int(df_ausgaben['year'].max())} | "
        f"{df_ausgaben['metric'].nunique()} metrics"
    )

    run_plausibility_check(df_ausgaben)

    _sep()
    print("AHV AUSGABEN PIPELINE COMPLETE ✓")
    print("=" * 50)

    return df_ausgaben


# -----------------------------------------
# 6. Entry Point
# -----------------------------------------

if __name__ == "__main__":
    try:
        df = run_ahv_ausgaben_pipeline()
        print(f"\n✓ Done: {len(df):,} rows")
    except Exception as exc:
        print(f"\n❌ Pipeline failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
