# =========================================
# Load and prepare OKP health data for WhoPays analysis.
# Analyses financial flows between generations in healthcare (OKP) and AHV.
# =========================================

from pathlib import Path
import pandas as pd
import re
import sys
import subprocess
import zipfile
import shutil
import tempfile
import warnings
from typing import Optional

warnings.filterwarnings("ignore", category=UserWarning)

# -----------------------------------------
# 1. Define Paths and Constants
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

RAW_WHOPAYS_PATH       = BASE_PATH / "data" / "whopays" / "raw_whopays"
RAW_POPULATION_PATH    = BASE_PATH / "data" / "raw" / "px-x-0102020000_103_20260424-164251.xlsx"

PROCESSED_WHOPAYS_PATH = BASE_PATH / "data" / "whopays" / "processed_whopays"

PROCESSED_WHOPAYS_PATH.mkdir(parents=True, exist_ok=True)

_UNZIP_TMP = Path("/tmp/whopays_unzip")

# -----------------------------------------
# 2. File Dictionaries
# -----------------------------------------

GROUP_B_FILES: dict[int, str] = {
    2006: "statistik-oblig-kv-2006-tab-laufend.xlsx",
    2007: "statistik-okv-2007-tab-laufend.xlsx",
    2008: "statistik-okv-2008-tab-laufend.xlsx",
    2009: "statistik-oblig-kv-2009-tab-laufend.xlsx",
    2010: "statistik-oblig-kv-2010-tabellen-laufende.xlsx",
}

GROUP_C_FILES: dict[int, str] = {
    2011: "statistik-oblig-kv-2011-tabellen-laufende.xlsx",
    2012: "statistik-oblig-kv-2012-tabellen-xls-laufende.xlsx",
    2013: "statistik-oblig-kv-2013-tabellen-xls-laufende.xlsx",
    2014: "statistik-oblig-kv-2014-tabellen.xlsx",
    2015: "KV_T_2015_20170904_d_sans_liaisons.xlsx",
    2016: "_STAT KV 2016 XLSX german and french v180613.zip",
    2017: "_STAT KV 2017 XLSX german and french V190704.zip",
    2018: "STAT KV 2018 XLSX german and french v200219.zip",
    2019: "STAT KV 2019 XLSX v201217.zip",
    2020: "STAT KV 2020 XLSX V220510.zip",
    2021: "STAT KV 2021 XLSX_V230222.zip",
}

GROUP_D_FILES: dict[int, str] = {
    2022: "STATKV 2022 XLSX V20231207.zip",
    2023: "STATKV2023 XLSX v20250424.zip",
    2024: "KVSTAT2024 XLSX v20260120.zip",
}

# Table number → (variable_name, [(col_idx, metric, scale, unit)])
# Column indices are 0-based as they appear in the raw Excel sheet.
SHEET_CONFIG: dict[str, tuple[str, list[tuple[int, str, str, str]]]] = {
    "307": (
        "okp_premium",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
            (7, "per_capita_chf", "chf_per_capita_year", "CHF"),
        ],
    ),
    "403": (
        "praemienverbilligung",
        [
            (3, "beneficiaries_count", "count", "Anzahl"),
            (4, "beneficiary_rate", "rate", "Anteil"),
            (5, "total_mio_chf", "mio_chf", "CHF"),
        ],
    ),
    "211": (
        "okp_kostenbeteiligung",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
            (7, "per_capita_chf", "chf_per_capita_year", "CHF"),
        ],
    ),
    "209": (
        "okp_nettoleistungen",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
            (7, "per_capita_chf", "chf_per_capita_year", "CHF"),
        ],
    ),
    "206": (
        "okp_bruttoleistungen",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
            (7, "per_capita_chf", "chf_per_capita_year", "CHF"),
        ],
    ),
}

# Older files (2006–2010) use sheet "315d" for okp_premium; per-capita col absent.
GROUP_B_SHEET_CONFIG: dict[str, tuple[str, list[tuple[int, str, str, str]]]] = {
    "315d": (
        "okp_premium",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
        ],
    ),
    "403": (
        "praemienverbilligung",
        [
            (3, "beneficiaries_count", "count", "Anzahl"),
            (4, "beneficiary_rate", "rate", "Anteil"),
            (5, "total_mio_chf", "mio_chf", "CHF"),
        ],
    ),
    "211": (
        "okp_kostenbeteiligung",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
        ],
    ),
    "209": (
        "okp_nettoleistungen",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
        ],
    ),
    "206": (
        "okp_bruttoleistungen",
        [
            (5, "total_mio_chf", "mio_chf", "CHF"),
        ],
    ),
}

# Generation definitions: (birth_year_min, birth_year_max, label, order)
GENERATIONS: list[tuple[int, int, str, int]] = [
    (0,    1945, "Silent Generation", 1),
    (1946, 1964, "Babyboomers",       2),
    (1965, 1980, "Generation X",      3),
    (1981, 1996, "Millennials",       4),
    (1997, 2012, "Generation Z",      5),
    (2013, 9999, "Generation Alpha",  6),
]

_EXCLUDE_RE = re.compile(
    r"^(total\b|unbekannt|alter\s+unbekannt)",
    re.IGNORECASE,
)


# -----------------------------------------
# 3. Helper Functions
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
    for by_min, by_max, label, order in GENERATIONS:
        if by_min <= birth_year <= by_max:
            return label, order
    return "Unknown", 0


def parse_age_label(label: str) -> tuple[int | None, int | None]:
    """
    Parse a Swiss OKP age-group label into (age_min, age_max).

    Handles single years ("25"), ranges ("20 – 24"), open upper bounds
    (">90", "≥ 90", "100 und mehr") and returns (None, None) for
    aggregate totals, footnotes or unrecognised strings.

    Args:
        label: Raw label string from col 0 of a KV-Statistik sheet.

    Returns:
        (age_min, age_max) as ints, or (None, None) if the row should be skipped.
    """
    if not isinstance(label, str):
        return None, None
    label = label.strip()
    if not label:
        return None, None

    # Aggregate totals, "Unbekannt", footnotes
    if _EXCLUDE_RE.match(label):
        return None, None

    # ">100" / "≥100" / "100 und mehr" → (100, 100)
    if re.match(r"^[>≥]\s*100", label) or re.match(
        r"^100\s+und\s+mehr", label, re.IGNORECASE
    ):
        return 100, 100

    # ">X" or "≥X" (open upper bound) → map to (X, 100)
    m = re.match(r"^[>≥]\s*(\d{1,3})$", label)
    if m:
        return int(m.group(1)), 100

    # "X – Y" ranges (en-dash, hyphen, or em-dash)
    m = re.match(r"^(\d{1,3})\s*[–\-—]\s*(\d{1,3})$", label)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Single integer
    m = re.match(r"^(\d{1,3})$", label)
    if m:
        age = int(m.group(1))
        return age, age

    return None, None


def _clean_numeric(val: object) -> float | None:
    """
    Coerce an Excel cell value to float.

    Handles Swiss thousand-separator apostrophes, non-breaking spaces,
    and trailing non-numeric characters.

    Args:
        val: Raw cell value.

    Returns:
        Float or None if conversion fails.
    """
    if pd.isna(val):
        return None
    s = (
        str(val)
        .strip()
        .replace("'", "")
        .replace("\xa0", "")
        .replace(",", ".")
    )
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _find_sheet(workbook: pd.ExcelFile, keyword: str) -> str | None:
    """
    Return the first sheet name whose name contains keyword (case-insensitive).

    Args:
        workbook: Open ExcelFile handle.
        keyword:  Substring to search for (e.g. "307").

    Returns:
        Matching sheet name or None.
    """
    kw = keyword.lower()
    kw_norm = re.sub(r'[^a-z0-9]', '', kw)
    for name in workbook.sheet_names:
        name_lower = name.lower()
        name_norm = re.sub(r'[^a-z0-9]', '', name_lower)
        if kw in name_lower or kw_norm in name_norm:
            return name
    return None


# -----------------------------------------
# 4. Population Data Loader
# -----------------------------------------

def load_population_data(path: Path) -> pd.DataFrame:
    """
    Load BFS population data from the px-x xlsx Cube file.

    Year is detected as a 4-digit integer in column 0.
    Age is read from column 1.
    Population at 1 January is in column 5; at 31 December in column 17.
    pop_avg = (pop_jan1 + pop_dec31) / 2 is used as the disaggregation weight.

    Falls back to BASE_PATH/data/<filename> if the primary path is missing
    (accommodating alternative file placement in the repo).

    Args:
        path: Expected path to the xlsx population file.

    Returns:
        DataFrame with columns: year (int), age (int), pop_avg (float).

    Raises:
        FileNotFoundError: If the file cannot be located via either path.
        ValueError: If no year rows can be detected in column 0.
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
    # Jahr vorwärts auffüllen: jede Alterszeile erbt das Jahr ihres Blocks
    df_raw["year_ff"] = col0_num.where(col0_num.between(1990, 2030)).ffill()
    df_data = df_raw[df_raw["year_ff"].notna()].copy()

    if df_data.empty:
        raise ValueError(
            "Could not detect year rows in population file. "
            "Column 0 must contain 4-digit year integers (1990–2030)."
        )

    df_data["year"] = df_data["year_ff"].astype(int)
    df_data["age_raw"] = df_data.iloc[:, 4].astype(str)
    df_data["age"] = df_data["age_raw"].str.extract(r'^(\d+)').astype(float)
    df_data["pop_jan1"] = pd.to_numeric(df_data.iloc[:, 5], errors="coerce")
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
# 5. XLS Conversion and ZIP Extraction
# -----------------------------------------

def _find_libreoffice() -> str:
    """
    Locate the LibreOffice executable on the current system.

    Checks common installation paths on macOS and Linux.

    Returns:
        Resolved executable path or name.

    Raises:
        FileNotFoundError: If LibreOffice cannot be found anywhere.
    """
    candidates = [
        "libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/libreoffice",
        "/usr/local/bin/libreoffice",
    ]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    raise FileNotFoundError(
        "LibreOffice not found. Install from https://www.libreoffice.org"
    )


def convert_xls_to_xlsx(xls_path: Path, tmp_dir: Path) -> Path:
    """
    Convert an XLS file to XLSX using LibreOffice in headless mode.

    Args:
        xls_path: Source .xls file.
        tmp_dir:  Directory where the converted .xlsx will be written.

    Returns:
        Path to the produced .xlsx file.

    Raises:
        FileNotFoundError: If LibreOffice is not installed or produced no output.
        subprocess.CalledProcessError: If LibreOffice exits with a non-zero status.
    """
    lo = _find_libreoffice()
    subprocess.run(
        [
            lo, "--headless", "--convert-to", "xlsx",
            str(xls_path), "--outdir", str(tmp_dir),
        ],
        check=True,
        capture_output=True,
    )
    xlsx_path = tmp_dir / (xls_path.stem + ".xlsx")
    if not xlsx_path.exists():
        raise FileNotFoundError(
            f"LibreOffice conversion produced no output. Expected: {xlsx_path}"
        )
    return xlsx_path


def extract_zip(zip_path: Path, year: int) -> Path:
    """
    Extract a ZIP archive to /tmp/whopays_unzip/<year>/.

    Any previous extraction for the same year is removed first.

    Args:
        zip_path: Source .zip file.
        year:     Data year (used to name the extraction sub-directory).

    Returns:
        Path to the extraction directory.
    """
    out_dir = _UNZIP_TMP / str(year)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    return out_dir


def find_xlsx_in_dir(directory: Path, keyword: str) -> Path | None:
    """
    Recursively search for an xlsx/xls file whose name contains keyword.

    Args:
        directory: Root directory to search.
        keyword:   Case-insensitive substring to match against filenames.

    Returns:
        Path to the first matching file, or None.
    """
    kw = keyword.lower()
    for f in sorted(directory.rglob("*")):
        if f.suffix.lower() in (".xlsx", ".xls") and kw in f.name.lower():
            return f
    return None


# -----------------------------------------
# 6. Sheet-level Data Extraction
# -----------------------------------------

def extract_from_sheet(
    xlsx_path: Path,
    sheet_name: str,
    year: int,
    variable_name: str,
    col_specs: list[tuple[int, str, str, str]],
) -> list[dict]:
    """
    Extract age-group data rows from a single Excel sheet.

    Reads the sheet with no header assumption and filters rows whose
    label in column 0 can be parsed as a valid age group.

    Args:
        xlsx_path:     Path to the workbook.
        sheet_name:    Exact sheet name to read.
        year:          Reference year for the data.
        variable_name: OKP variable identifier (e.g. "okp_premium").
        col_specs:     List of (col_idx, metric, scale, unit) tuples.

    Returns:
        List of long-format record dicts ready for DataFrame construction.
    """
    try:
        df = pd.read_excel(
            xlsx_path, sheet_name=sheet_name, header=None, dtype=object
        )
    except Exception as e:
        print(f"   ⚠️  Cannot read sheet '{sheet_name}' in {xlsx_path.name}: {e}")
        return []

    records: list[dict] = []

    for _, row in df.iterrows():
        raw_label = row.iloc[0] if len(row) > 0 else None
        label = str(raw_label).strip() if pd.notna(raw_label) else ""

        age_min, age_max = parse_age_label(label)
        if age_min is None:
            continue

        notes = ""
        if variable_name == "praemienverbilligung" and age_min == 0 and age_max == 18:
            notes = "403d_coarse_0_18"

        for col_idx, metric, scale, unit in col_specs:
            if col_idx >= len(row):
                continue
            value = _clean_numeric(row.iloc[col_idx])
            if value is None:
                continue

            records.append(
                {
                    "year":            year,
                    "variable_name":   variable_name,
                    "age_group_label": label,
                    "age_min":         age_min,
                    "age_max":         age_max,
                    "metric":          metric,
                    "value":           value,
                    "unit":            unit,
                    "scale":           scale,
                    "notes":           notes,
                }
            )

    return records


def _read_all_sheets_from_file(
    xlsx_path: Path,
    year: int,
    sheet_config: dict | None = None,
) -> list[dict]:
    """
    Read all configured tables from a single workbook.

    Args:
        xlsx_path:    Path to the xlsx workbook.
        year:         Data year.
        sheet_config: Table config to use; defaults to SHEET_CONFIG.

    Returns:
        Combined list of long-format records from all matched sheets.
    """
    if sheet_config is None:
        sheet_config = SHEET_CONFIG

    records: list[dict] = []
    try:
        wb = pd.ExcelFile(xlsx_path)
    except Exception as e:
        print(f"   ❌ Cannot open {xlsx_path.name}: {e}")
        return records

    for table_num, (variable_name, col_specs) in sheet_config.items():
        sheet_name = _find_sheet(wb, table_num)
        if sheet_name is None:
            print(f"   ⚠️  Sheet '{table_num}' not found in {xlsx_path.name}")
            continue
        recs = extract_from_sheet(xlsx_path, sheet_name, year, variable_name, col_specs)
        print(f"   ✓ Table {table_num} ({variable_name}): {len(recs)} rows")
        records.extend(recs)

    return records


# -----------------------------------------
# 7. Year-level Processing
# -----------------------------------------

def process_direct_file(
    year: int,
    filename: str,
    sheet_config: dict | None = None,
) -> list[dict]:
    """
    Process a direct xlsx (or xls, converted via LibreOffice) file.

    Used for Group B years 2006–2010 and Group C years 2012–2015.

    Args:
        year:         Data year.
        filename:     File name within RAW_WHOPAYS_PATH.
        sheet_config: Table config to use; defaults to SHEET_CONFIG.

    Returns:
        List of extracted long-format records.
    """
    if sheet_config is None:
        sheet_config = SHEET_CONFIG

    path = RAW_WHOPAYS_PATH / filename
    if not path.exists():
        print(f"   ⚠️  File not found: {path}")
        return []

    _sep()
    print(f"PROCESSING YEAR {year}: {filename}")
    print("=" * 50)

    with tempfile.TemporaryDirectory(prefix="whopays_xls_") as tmp:
        tmp_path = Path(tmp)

        if path.suffix.lower() == ".xls":
            print("   📄 Converting XLS → XLSX via LibreOffice …")
            try:
                xlsx_path = convert_xls_to_xlsx(path, tmp_path)
                print(f"   ✓ Converted: {xlsx_path.name}")
            except Exception as e:
                print(f"   ❌ XLS conversion failed: {e}")
                return []
        else:
            xlsx_path = path

        return _read_all_sheets_from_file(xlsx_path, year, sheet_config)


def process_zip_group_c(year: int, filename: str) -> list[dict]:
    """
    Process a Group C ZIP file (years 2016–2021).

    Locates the main workbook by searching for a file whose name contains
    "307". If no such file exists (e.g. 2016), falls back to the first xlsx
    in the archive. After reading the main workbook, any tables still missing
    (403, 211, 209, 206) are looked up in their own per-table files, using
    the same strategy as process_zip_group_d.

    Args:
        year:     Data year.
        filename: ZIP file name within RAW_WHOPAYS_PATH.

    Returns:
        List of extracted long-format records.
    """
    zip_path = RAW_WHOPAYS_PATH / filename
    if not zip_path.exists():
        print(f"   ⚠️  ZIP not found: {zip_path}")
        return []

    _sep()
    print(f"PROCESSING YEAR {year} (ZIP Group C): {filename}")
    print("=" * 50)

    extract_dir = extract_zip(zip_path, year)
    print(f"   📦 Extracted to: {extract_dir}")

    # Locate main workbook — prefer file with "307" in name
    main_file = find_xlsx_in_dir(extract_dir, "307")
    if main_file is None:
        # Fallback: first xlsx found anywhere in the archive
        candidates = sorted(
            f for f in extract_dir.rglob("*") if f.suffix.lower() in (".xlsx", ".xls")
        )
        if candidates:
            main_file = candidates[0]
            print(f"   ⚠️  No '307' file found — using fallback: {main_file.name}")
        else:
            print(f"   ❌ No xlsx files found in {extract_dir}")
            return []

    print(f"   📂 Main file: {main_file.name}")
    records = _read_all_sheets_from_file(main_file, year)

    # Determine which tables were successfully extracted from the main file
    found_tables = {r["variable_name"] for r in records}
    missing = [
        (num, var, cols)
        for num, (var, cols) in SHEET_CONFIG.items()
        if var not in found_tables
    ]

    if missing:
        print(f"   ↳ {len(missing)} table(s) missing from main file — searching per-table files …")
        for table_num, variable_name, col_specs in missing:
            file_path = find_xlsx_in_dir(extract_dir, table_num)
            if file_path is None:
                print(f"   ⚠️  No file for table '{table_num}' found in {extract_dir}")
                continue
            print(f"   📂 Table {table_num}: {file_path.name}")
            try:
                wb = pd.ExcelFile(file_path)
            except Exception as e:
                print(f"   ❌ Cannot open {file_path.name}: {e}")
                continue
            sheet_name = _find_sheet(wb, table_num)
            if sheet_name is None:
                sheet_name = wb.sheet_names[0] if wb.sheet_names else None
            if sheet_name is None:
                print(f"   ⚠️  No usable sheet in {file_path.name}")
                continue
            recs = extract_from_sheet(file_path, sheet_name, year, variable_name, col_specs)
            print(f"   ✓ Table {table_num} ({variable_name}): {len(recs)} rows")
            records.extend(recs)

    return records


def process_zip_group_d(year: int, filename: str) -> list[dict]:
    """
    Process a Group D ZIP file (years 2022–2024).

    Each table may reside in its own xlsx file within the archive.
    First attempts to find a single main workbook (file containing "307"
    in its name) that contains all sheets. If that fails or the sheets are
    absent, falls back to searching for one file per table number.

    Args:
        year:     Data year.
        filename: ZIP file name within RAW_WHOPAYS_PATH.

    Returns:
        List of extracted long-format records.
    """
    zip_path = RAW_WHOPAYS_PATH / filename
    if not zip_path.exists():
        print(f"   ⚠️  ZIP not found: {zip_path}")
        return []

    _sep()
    print(f"PROCESSING YEAR {year} (ZIP Group D): {filename}")
    print("=" * 50)

    extract_dir = extract_zip(zip_path, year)
    print(f"   📦 Extracted to: {extract_dir}")

    # Try single-workbook approach first
    main_file = find_xlsx_in_dir(extract_dir, "307")
    if main_file is not None:
        try:
            wb = pd.ExcelFile(main_file)
            has_all = all(_find_sheet(wb, num) is not None for num in SHEET_CONFIG)
        except Exception:
            has_all = False

        if has_all:
            print(f"   📂 Single workbook (all sheets): {main_file.name}")
            return _read_all_sheets_from_file(main_file, year)

    # Fall back: one file per table
    print("   ↳ Multi-file layout detected — searching per table …")
    records: list[dict] = []

    for table_num, (variable_name, col_specs) in SHEET_CONFIG.items():
        file_path = find_xlsx_in_dir(extract_dir, table_num)
        if file_path is None:
            print(f"   ⚠️  No file for table '{table_num}' found in {extract_dir}")
            continue

        print(f"   📂 Table {table_num}: {file_path.name}")
        try:
            wb = pd.ExcelFile(file_path)
        except Exception as e:
            print(f"   ❌ Cannot open {file_path.name}: {e}")
            continue

        sheet_name = _find_sheet(wb, table_num)
        if sheet_name is None:
            # Last resort: use the first sheet
            sheet_name = wb.sheet_names[0] if wb.sheet_names else None
        if sheet_name is None:
            print(f"   ⚠️  No usable sheet in {file_path.name}")
            continue

        recs = extract_from_sheet(file_path, sheet_name, year, variable_name, col_specs)
        print(f"   ✓ Table {table_num} ({variable_name}): {len(recs)} rows")
        records.extend(recs)

    return records


def _read_312d_percapita(df: pd.DataFrame, year: int) -> dict[str, float]:
    """
    Extract per-capita annual premium (CHF/year) from a 312d sheet.

    Handles two layouts found across 2006–2008:
    - Vertical (2006-2007): three stacked sub-tables, each introduced by an
      age-group header in col 0 ('Kinder', 'Junge Erwachsene', 'Erwachsene'),
      followed by a 'Jahr' label row, then year-data rows with col 5 = Total.
    - Horizontal (2008): a single table where col 0 = Jahr, col 1 = Kinder,
      col 3 = Junge Erwachsene, col 5 = Erwachsene.

    Args:
        df:   Raw 312d DataFrame (header=None, dtype=object).
        year: Target data year.

    Returns:
        Dict mapping group keyword to per-capita CHF/year for the three groups.
        Returns an empty dict on parse failure.
    """
    # Detect layout by scanning rows 20-45
    layout = None
    for row_i in range(20, min(45, len(df))):
        c0 = str(df.iloc[row_i, 0]).strip()
        c1 = str(df.iloc[row_i, 1]).strip() if df.shape[1] > 1 else ""
        if "Kinder" in c0:
            layout = "vertical"
            break
        if "Kinder" in c1:
            layout = "horizontal"
            break

    result: dict[str, float] = {}

    if layout == "vertical":
        for keyword in ("Kinder", "Junge Erwachsene", "Erwachsene"):
            header_row = next(
                (i for i in range(20, len(df)) if str(df.iloc[i, 0]).strip() == keyword),
                None,
            )
            if header_row is None:
                continue
            jahr_row = next(
                (
                    i for i in range(header_row + 1, header_row + 10)
                    if str(df.iloc[i, 0]).strip() == "Jahr"
                ),
                None,
            )
            if jahr_row is None:
                continue
            for row_i in range(jahr_row + 1, jahr_row + 20):
                try:
                    yr = int(float(str(df.iloc[row_i, 0]).strip()))
                except (ValueError, TypeError):
                    break
                if yr == year:
                    v = _clean_numeric(df.iloc[row_i, 5])
                    if v is not None:
                        result[keyword] = v
                    break

    elif layout == "horizontal":
        jahr_row = next(
            (
                i for i in range(25, min(40, len(df)))
                if str(df.iloc[i, 0]).strip() == "Jahr"
            ),
            None,
        )
        if jahr_row is not None:
            for row_i in range(jahr_row + 1, jahr_row + 20):
                try:
                    yr = int(float(str(df.iloc[row_i, 0]).strip()))
                except (ValueError, TypeError):
                    break
                if yr == year:
                    for keyword, col in (
                        ("Kinder", 1),
                        ("Junge Erwachsene", 3),
                        ("Erwachsene", 5),
                    ):
                        v = _clean_numeric(df.iloc[row_i, col])
                        if v is not None:
                            result[keyword] = v
                    break

    return result


def _j1d_praemien_total(workbook_path: Path, year: int) -> float | None:
    """
    Read the reference Prämien total (Mio CHF) for *year* from the J1d sheet.

    Locates the year header row (first row in rows 0-10 that contains *year*
    as an integer value), reads the corresponding column from the 'Prämien'
    data row (col 1 == 'Prämien').

    Args:
        workbook_path: Path to the xlsx workbook.
        year:          Target data year.

    Returns:
        Reference Prämien total in Mio CHF, or None on failure.
    """
    try:
        wb = pd.ExcelFile(workbook_path)
    except Exception:
        return None

    j1_sheet = next(
        (s for s in wb.sheet_names if re.match(r"^j1", s.lower())), None
    )
    if j1_sheet is None:
        return None

    try:
        dfj = pd.read_excel(workbook_path, sheet_name=j1_sheet, header=None, dtype=object)
    except Exception:
        return None

    # Find year header row and the column for the target year
    year_col = None
    for row_i in range(min(10, len(dfj))):
        for col_i, val in enumerate(dfj.iloc[row_i].tolist()):
            try:
                if int(float(str(val))) == year:
                    year_col = col_i
                    break
            except (ValueError, TypeError):
                continue
        if year_col is not None:
            break

    if year_col is None:
        return None

    # Find Prämien row (col 1 exactly == 'Prämien')
    pram_row = next(
        (
            i for i in range(len(dfj))
            if str(dfj.iloc[i, 1]).strip() == "Prämien"
        ),
        None,
    )
    if pram_row is None:
        return None

    return _clean_numeric(dfj.iloc[pram_row, year_col])


def extract_okp_premium_group_b(
    year: int,
    workbook_path: Path,
    pop_df: pd.DataFrame,
) -> list[dict]:
    """
    Derive okp_premium cohort records for 2006–2008 from sheet 312d.

    Sheet 315d (the standard okp_premium source for Group B) is absent in
    2006–2008.  Sheet 312d carries per-capita annual premiums (CHF/year) for
    three age groups. This function converts those per-capita values to
    total_mio_chf by multiplying by the BFS average population for each group,
    then runs a 10 % plausibility check against the J1d 'Prämien' total.

    Args:
        year:          Data year (2006, 2007, or 2008).
        workbook_path: Path to the xlsx workbook.
        pop_df:        Population reference DataFrame (year, age, pop_avg).

    Returns:
        Three cohort-level records (Kinder / Junge Erwachsene / Erwachsene),
        formatted identically to records from extract_from_sheet(), or an
        empty list on failure.
    """
    print(f"   312d okp_premium (year {year}): {workbook_path.name}")

    try:
        wb = pd.ExcelFile(workbook_path)
    except Exception as e:
        print(f"   ❌ Cannot open {workbook_path.name}: {e}")
        return []

    sheet_312 = _find_sheet(wb, "312")
    if sheet_312 is None:
        print(f"   ⚠️  Sheet '312d' not found in {workbook_path.name}")
        return []

    try:
        df312 = pd.read_excel(workbook_path, sheet_name=sheet_312, header=None, dtype=object)
    except Exception as e:
        print(f"   ❌ Cannot read sheet '{sheet_312}': {e}")
        return []

    percapita = _read_312d_percapita(df312, year)
    if len(percapita) < 3:
        print(
            f"   ⚠️  Could not parse all three age-group per-capita values from 312d "
            f"(got {list(percapita.keys())})"
        )
        return []

    # Age-group definitions: (keyword, age_min, age_max, label)
    age_groups = [
        ("Kinder",           0,   18, "0 – 18"),
        ("Junge Erwachsene", 19,  25, "19 – 25"),
        ("Erwachsene",       26, 100, "> 25"),
    ]

    pop_year = pop_df[pop_df["year"] == year]

    records: list[dict] = []
    computed_totals: list[float] = []

    for keyword, age_min, age_max, label in age_groups:
        per_capita = percapita[keyword]
        pop_sum = float(
            pop_year[(pop_year["age"] >= age_min) & (pop_year["age"] <= age_max)]["pop_avg"].sum()
        )
        if pop_sum == 0:
            print(f"   ⚠️  Zero population for {keyword} {year} — skipping")
            continue

        total_mio = per_capita * pop_sum / 1_000_000
        computed_totals.append(total_mio)

        records.append(
            {
                "year":            year,
                "variable_name":   "okp_premium",
                "age_group_label": label,
                "age_min":         age_min,
                "age_max":         age_max,
                "metric":          "total_mio_chf",
                "value":           total_mio,
                "unit":            "CHF",
                "scale":           "mio_chf",
                "notes":           "312d_per_capita_x_pop",
            }
        )

    if not records:
        return []

    our_total = sum(computed_totals)
    print(
        f"   ✓ 312d: Kinder={percapita['Kinder']:.2f}, "
        f"JE={percapita['Junge Erwachsene']:.2f}, "
        f"Erw={percapita['Erwachsene']:.2f} CHF/yr  →  "
        f"sum={our_total:.1f} Mio CHF"
    )

    # Plausibility: compare against J1d Prämien reference
    ref = _j1d_praemien_total(workbook_path, year)
    if ref is not None and ref > 0:
        rel_err = abs(our_total - ref) / ref
        status = "✓" if rel_err <= 0.10 else "⚠️ "
        print(
            f"   {status} J1d reference={ref:.1f} Mio CHF  "
            f"rel. error={rel_err:.1%}  ({'OK' if rel_err <= 0.10 else 'EXCEEDS 10%'})"
        )
    else:
        print("   ⚠️  J1d Prämien reference not found — plausibility check skipped")

    return records


# -----------------------------------------
# 8. Disaggregation
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
        method: "pop_weighted", "equal_distribution", or "direct".

    Returns:
        Record dict enriched with age, birth_year, generation, and method.
    """
    birth_year = year - age
    gen_label, gen_order = map_generation(birth_year)
    r = base.copy()
    r.update(
        {
            "age":                age,
            "birth_year":         birth_year,
            "project_age_group":  gen_label,
            "project_age_order":  gen_order,
            "method":             method,
            "value":              value,
        }
    )
    return r


def disaggregate_to_single_age(
    df_cohort: pd.DataFrame,
    pop_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Disaggregate cohort-level OKP data to single-age / birth-year rows.

    Disaggregation rules by scale:
    - mio_chf:            population-weighted split across the age range.
                          Falls back to equal distribution when population
                          data are unavailable.
    - chf_per_capita_year: direct copy to every single age in the range.
    - count / rate:        direct copy to every single age in the range.

    Adds columns: age, birth_year, project_age_group, project_age_order, method.

    Args:
        df_cohort: Cohort-level long-format DataFrame from the extraction step.
        pop_df:    Population reference DataFrame (year, age, pop_avg).

    Returns:
        Single-age long-format DataFrame.
    """
    _sep()
    print("DISAGGREGATING TO SINGLE AGE / BIRTH YEAR")
    print("=" * 50)

    # Build O(1) lookup: (year, age) → pop_avg
    pop_lookup: dict[tuple[int, int], float] = {
        (int(r.year), int(r.age)): float(r.pop_avg)
        for r in pop_df.itertuples(index=False)
    }

    records: list[dict] = []

    for _, row in df_cohort.iterrows():
        year    = int(row["year"])
        age_min = int(row["age_min"])
        age_max = int(row["age_max"])
        scale   = row["scale"]
        value   = float(row["value"])

        # Cap at 100 to avoid inflated age ranges from open upper bounds
        ages = list(range(age_min, min(age_max, 100) + 1))
        if not ages:
            continue

        base = row.to_dict()

        if scale in ("mio_chf", "count"):
            # Population-weighted split: both total amounts and beneficiary counts
            # are additive across ages and must be distributed, not copied.
            # beneficiary_rate (scale="rate") stays on direct copy below.
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

        else:
            # chf_per_capita_year, rate → direct copy (rates are not additive)
            method = "direct"
            for age in ages:
                records.append(_make_disagg_record(base, year, age, value, method))

    df_out = pd.DataFrame(records)
    print(
        f"✓ Disaggregated: {len(df_cohort):,} cohort rows → "
        f"{len(df_out):,} single-age rows"
    )
    return df_out


# -----------------------------------------
# 9. Missing-Year Interpolation
# -----------------------------------------

def interpolate_missing_okp_premium(df_birth_year: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing okp_premium rows for 2016 by linear interpolation from 2015 and 2017.

    2016 is absent because the source ZIP contained no table-307 file.
    For every (age, metric) combination present in both 2015 and 2017,
    the interpolated value is the arithmetic mean of the two years.

    Non-value columns (birth_year, project_age_group, project_age_order,
    method) are copied from the 2017 rows and then corrected for 2016.

    No rows are added if 2016 data are already present, or if neither
    2015 nor 2017 rows exist.

    Args:
        df_birth_year: Disaggregated single-age DataFrame (all variables).

    Returns:
        DataFrame with 2016 okp_premium rows appended, or unchanged if
        the condition is not triggered.
    """
    mask_premium = df_birth_year["variable_name"] == "okp_premium"

    if (mask_premium & (df_birth_year["year"] == 2016)).any():
        print("   ↳ 2016 okp_premium already present — interpolation skipped.")
        return df_birth_year

    df_2015 = df_birth_year[mask_premium & (df_birth_year["year"] == 2015)].copy()
    df_2017 = df_birth_year[mask_premium & (df_birth_year["year"] == 2017)].copy()

    if df_2015.empty or df_2017.empty:
        print("   ⚠️  Cannot interpolate 2016 okp_premium: 2015 or 2017 data missing.")
        return df_birth_year

    # Average value per (age, metric) across 2015 and 2017
    key_cols = ["age", "metric"]
    avg_2015 = df_2015.set_index(key_cols)["value"]
    avg_2017 = df_2017.set_index(key_cols)["value"]
    common   = avg_2015.index.intersection(avg_2017.index)
    avg_vals = ((avg_2015.loc[common] + avg_2017.loc[common]) / 2).reset_index()
    avg_vals.columns = ["age", "metric", "value"]

    # Use 2017 rows as structural template, overwrite year-dependent fields
    template = df_2017[df_2017.set_index(key_cols).index.isin(common)].copy()
    template = template.merge(avg_vals, on=key_cols, suffixes=("_old", ""))
    template.drop(columns=["value_old"], inplace=True)

    template["year"]       = 2016
    template["birth_year"] = 2016 - template["age"]
    template["notes"]      = "interpolated_2015_2017"
    template["method"]     = "interpolated"

    gen_cols = template["birth_year"].apply(
        lambda by: pd.Series(map_generation(int(by)))
    )
    template[["project_age_group", "project_age_order"]] = gen_cols

    n = len(template)
    print(f"   ✓ Interpolated {n} okp_premium rows for 2016 (notes='interpolated_2015_2017')")
    return pd.concat([df_birth_year, template], ignore_index=True)


# -----------------------------------------
# 10. Plausibility Check
# -----------------------------------------

def run_plausibility_check(
    df_cohort: pd.DataFrame, df_birth_year: pd.DataFrame
) -> None:
    """
    Verify that disaggregated mio_chf totals match cohort totals within 0.01%.

    For each (year, variable_name, metric) group with scale == mio_chf,
    the sum of disaggregated single-age values is compared to the cohort
    total. Deviations exceeding 0.01% are logged as WARNING.

    Args:
        df_cohort:     Cohort-level DataFrame.
        df_birth_year: Disaggregated single-age DataFrame.
    """
    _sep()
    print("PLAUSIBILITY CHECK (mio_chf totals)")
    print("=" * 50)

    mio_cohort = df_cohort[df_cohort["scale"] == "mio_chf"]
    mio_disagg = df_birth_year[df_birth_year["scale"] == "mio_chf"]

    if mio_cohort.empty:
        print("   ⚠️  No mio_chf rows to check.")
        return

    grp = ["year", "variable_name", "metric"]
    cohort_sums = mio_cohort.groupby(grp)["value"].sum()
    disagg_sums = mio_disagg.groupby(grp)["value"].sum()

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
                f"   ⚠️  {key}: expected {expected:.4f}, got {actual:.4f} "
                f"(rel. error {rel_err:.4%})"
            )
            mismatches += 1

    total = len(cohort_sums)
    if mismatches == 0:
        print(f"   ✓ All {total} checks passed (tolerance < 0.01 %)")
    else:
        print(f"   ⚠️  {mismatches}/{total} check(s) exceeded tolerance")


# -----------------------------------------
# 10. Main Pipeline
# -----------------------------------------

def run_whopays_pipeline() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Execute the full WhoPays OKP data pipeline.

    Steps:
    1. Ensure output directory exists.
    2. Load BFS population reference data.
    3. Extract cohort data from Group C files (2012–2021).
    4. Extract cohort data from Group D files (2022–2024).
    5. Save okp_cohort.csv.
    6. Disaggregate to single age / birth year.
    7. Save okp_by_birth_year.csv.
    8. Run plausibility checks.

    Returns:
        Tuple of (df_okp_cohort, df_okp_birth_year).
        Both DataFrames are empty if no records could be extracted.
    """
    PROCESSED_WHOPAYS_PATH.mkdir(parents=True, exist_ok=True)
    _UNZIP_TMP.mkdir(parents=True, exist_ok=True)

    _sep()
    print("WHOPAYS OKP PIPELINE START")
    print("=" * 50)

    # Population reference
    pop_df = load_population_data(RAW_POPULATION_PATH)

    all_records: list[dict] = []

    # Group B: 2006–2010, direct xlsx files with older sheet structure
    # 2006-2008 lack sheet 315d; okp_premium is derived from 312d per-capita data.
    for year, filename in GROUP_B_FILES.items():
        recs = process_direct_file(year, filename, sheet_config=GROUP_B_SHEET_CONFIG)
        if year in {2006, 2007, 2008}:
            filepath = RAW_WHOPAYS_PATH / filename
            recs_312d = extract_okp_premium_group_b(year, filepath, pop_df)
            recs.extend(recs_312d)
        print(f"   ↳ Year {year}: {len(recs):,} records")
        all_records.extend(recs)

    # Group C: 2012–2015 direct files, 2016–2021 ZIP archives
    for year, filename in GROUP_C_FILES.items():
        if filename.endswith(".zip"):
            recs = process_zip_group_c(year, filename)
        else:
            recs = process_direct_file(year, filename)
        print(f"   ↳ Year {year}: {len(recs):,} records")
        all_records.extend(recs)

    # Group D: 2022–2024 ZIP archives (possibly one file per table)
    for year, filename in GROUP_D_FILES.items():
        recs = process_zip_group_d(year, filename)
        print(f"   ↳ Year {year}: {len(recs):,} records")
        all_records.extend(recs)

    if not all_records:
        print("❌ No records extracted. Check that raw data files are present.")
        return pd.DataFrame(), pd.DataFrame()

    # Cohort-level output
    df_cohort = pd.DataFrame(all_records)
    cohort_path = PROCESSED_WHOPAYS_PATH / "okp_cohort.csv"
    df_cohort.to_csv(cohort_path, index=False)

    _sep()
    print(f"✓ okp_cohort.csv saved: {cohort_path}")
    print(
        f"   {len(df_cohort):,} rows | "
        f"{df_cohort['year'].nunique()} years | "
        f"{df_cohort['variable_name'].nunique()} variables"
    )

    # Single-age / birth-year output
    df_birth_year = disaggregate_to_single_age(df_cohort, pop_df)
    df_birth_year = interpolate_missing_okp_premium(df_birth_year)
    birth_year_path = PROCESSED_WHOPAYS_PATH / "okp_by_birth_year.csv"
    df_birth_year.to_csv(birth_year_path, index=False)

    _sep()
    print(f"✓ okp_by_birth_year.csv saved: {birth_year_path}")
    print(f"   {len(df_birth_year):,} rows")

    # Quality gate
    run_plausibility_check(df_cohort, df_birth_year)

    _sep()
    print("WHOPAYS OKP PIPELINE COMPLETE ✓")
    print("=" * 50)

    return df_cohort, df_birth_year


# -----------------------------------------
# 11. Entry Point
# -----------------------------------------

if __name__ == "__main__":
    try:
        df_c, df_b = run_whopays_pipeline()
        print(
            f"\n✓ Done: {len(df_c):,} cohort rows, {len(df_b):,} birth-year rows"
        )
    except Exception as exc:
        print(f"\n❌ Pipeline failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
