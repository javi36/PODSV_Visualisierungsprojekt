# =========================================
# Load and prepare data sources for WhoDecides, WhoOwns and Whopays.
# =========================================

from pathlib import Path
import pandas as pd
import re
import sys

from load_whopays_final import (
    run_whopays_pipeline,
    run_ahv_einnahmen_pipeline,
    run_ahv_ausgaben_pipeline,
)

# -----------------------------------------
# 1. Define Paths and Constants
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

# RAW Paths for WhoDecides Data
RAW_SELECTS_2023_PATH = BASE_PATH / "data" / "whodecide" / "raw" / "2634_Selects2023_PES_Data_v2.0.csv"
RAW_SELECTS_2019_PATH = BASE_PATH / "data" / "whodecide" / "raw" / "1179_Selects2019_PES_Data_v1.1.0.csv"  # NEU
RAW_SELECTS_2015_PATH = BASE_PATH / "data" / "whodecide" / "raw" / "726_Selects2015_PES_Data_v1.03.dta"  # NEU

# Processed Paths for WhoDecides Data
PROCESSED_SELECTS_2023_PATH = BASE_PATH / "data" / "whodecide" / "processed" / "selects_2023_clean.csv"
PROCESSED_SELECTS_2019_PATH = BASE_PATH / "data" / "whodecide" / "processed" / "selects_2019_clean.csv"  # NEU
PROCESSED_SELECTS_2015_PATH = BASE_PATH / "data" / "whodecide" / "processed" / "selects_2015_clean.csv"  # NEU

# RAW Paths for WhoOwns Data
RAW_WOHNEIGENTUMSQUOTE_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "wohneigentumsquote_kanton_2026.csv"
RAW_WOHNEIGENTUMS_META_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "metadaten_wohneigentumsquote_kanton_2026.ods"
RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "bfs_bewohnertyp_groesse.xlsx"

# Processed Paths for WhoOwns Data
PROCESSED_WOHNEIGENTUMSQUOTE_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "wohneigentumsquote_kanton_2026_clean.csv"
PROCESSED_BFS_BEWOHNERTYP_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "bfs_bewohnertyp_20260414_clean.csv"
PROCESSED_BFS_WOHNFLAECHE_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "bfs_wohnflaeche_20260414_clean.csv"


# Ordnerstruktur sicherstellen
PROCESSED_SELECTS_2023_PATH.parent.mkdir(parents=True, exist_ok=True)
PROCESSED_SELECTS_2019_PATH.parent.mkdir(parents=True, exist_ok=True)
PROCESSED_WOHNEIGENTUMSQUOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
PROCESSED_BFS_BEWOHNERTYP_PATH.parent.mkdir(parents=True, exist_ok=True)
PROCESSED_BFS_WOHNFLAECHE_PATH.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------------------
# 2. Helper-Funktionen
# -----------------------------------------
def load_selects_data(path: Path) -> pd.DataFrame:
    """
    Lade Selects 2023 Daten.
    
    Args:
        path: Pfad zur CSV-Datei
        
    Returns:
        DataFrame mit den geladenen Daten
    """
    print("\n" + "="*50)
    print("LOADING SELECT DATA")
    print("="*50)
    
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    
    print(f"📂 Loading from: {path}")
    
    df = pd.read_csv(path, sep=None, engine="python")
    
    print(f"✓ Loaded: {df.shape[0]} rows × {df.shape[1]} columns")
    
    return df

def load_selects_2015_data(path: Path) -> pd.DataFrame:
    """Lade Selects 2015 Daten (.dta Stata-Format)."""
    print("\n" + "="*50)
    print("LOADING SELECTS 2015 DATA (.dta)")
    print("="*50)

    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    print(f"📂 Loading from: {path}")

    df = pd.read_stata(path, convert_categoricals=False)

    # f11100rec nachbauen: 1=gewählt, 0=nicht gewählt, Rest als NaN
    df["f11100rec"] = df["f11100r"].map({1.0: 1, 0.0: 0})

    print(f"✓ Loaded: {df.shape[0]} rows × {df.shape[1]} columns")
    return df

def load_wohneigentums_data(path: Path) -> pd.DataFrame:
    """
    Lade Wohneigentum-Daten nach Kanton.
    
    Hinweis: BFS-Daten verwenden Semikolon als Trennzeichen!
    
    Args:
        path: Pfad zur CSV-Datei
        
    Returns:
        DataFrame mit Wohneigentum-Daten oder None wenn nicht vorhanden
    """
    print("\n" + "="*50)
    print("LOADING WHOOWNS DATA")
    print("="*50)
    
    if not path.exists():
        print(f"⚠️  Datei nicht gefunden: {path}")
        return None

    print(f"📂 Loading from: {path}")

    try:
        # BFS-Daten verwenden Semikolon als Trennzeichen!
        df = pd.read_csv(path, sep=";")

        print(f"✓ Loaded: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"   Columns: {df.columns.tolist()}")

        return df

    except Exception as e:
        print(f"❌ Loading failed: {e}")
        return None


def load_geo_metadata(path: Path) -> pd.DataFrame:
    """
    Lade GEO-Metadaten (Kanton-Codes und Labels) aus ODS.

    Args:
        path: Pfad zur Metadaten-ODS

    Returns:
        DataFrame mit GEO-Metadaten oder None wenn nicht vorhanden
    """
    print("\n" + "="*50)
    print("LOADING WHOOWNS GEO METADATA")
    print("="*50)

    if not path.exists():
        print(f"⚠️  Datei nicht gefunden: {path}")
        return None

    print(f"📂 Loading from: {path}")

    try:
        df = pd.read_excel(path, sheet_name="GEO", engine="odf")
        expected_cols = ["CODE", "LABEL_EN", "LABEL_FR", "LABEL_DE", "LABEL_IT"]
        available_cols = [c for c in expected_cols if c in df.columns]

        if "CODE" not in available_cols:
            print("❌ Spalte 'CODE' fehlt im GEO-Sheet")
            return None

        df = df[available_cols].copy()
        df["CODE"] = df["CODE"].astype(str).str.strip()

        print(f"✓ Loaded GEO metadata: {df.shape[0]} rows × {df.shape[1]} columns")
        return df

    except Exception as e:
        print(f"❌ Loading failed: {e}")
        return None


def load_bfs_bewohnertyp_groesse_data(path: Path, sheet_type: str) -> pd.DataFrame:
    """
    Lade BFS-Bewohnertyp-Größe-Daten (Excel).

    Args:
        path: Pfad zur Excel-Datei

    Args:
        sheet_type: "bewohnertyp" oder "wohnflaeche"

    Returns:
        DataFrame mit BFS-Daten aus allen passenden Sheets oder None wenn nicht vorhanden
    """
    print("\n" + "="*50)
    print("LOADING BFS DATA")
    print("="*50)

    if not path.exists():
        print(f"⚠️  Datei nicht gefunden: {path}")
        return None

    print(f"📂 Loading from: {path}")

    try:
        workbook = pd.ExcelFile(path)
        available_sheets = workbook.sheet_names

        if sheet_type not in {"bewohnertyp", "wohnflaeche"}:
            raise ValueError(f"Unbekannter sheet_type: {sheet_type}")

        def is_matching_sheet(name: str) -> bool:
            lowered = name.lower()
            if sheet_type == "bewohnertyp":
                return (
                    "bewohn" in lowered
                    or lowered.startswith("se")
                    or "se20" in lowered
                )
            return (
                "wohnflaeche" in lowered
                or "wohnfläche" in lowered
                or "gws" in lowered
            )

        def infer_year_from_sheet_name(name: str) -> int | None:
            match = re.search(r"(20\d{2})", name)
            if not match:
                return None
            year = int(match.group(1))
            return year if 2019 <= year <= 2024 else None

        matching_sheets = [sheet for sheet in available_sheets if is_matching_sheet(sheet)]
        if not matching_sheets:
            print(f"⚠️  Kein passendes Sheet fuer '{sheet_type}' gefunden. Verfuegbar: {available_sheets}")
            return None

        numeric_columns = [
            "Absolute Zahlen",
            "Vertrauens-intervall : \n± (in %)",
            "Anteil in %",
            "Vertrauens-\nintervall : \n± (in %-Pkte)",
            "Wohnfläche (in m2) pro Person",
        ]

        frames = []
        for sheet_name in matching_sheets:
            sheet_df = pd.read_excel(path, sheet_name=sheet_name, header=2)
            sheet_df = sheet_df.loc[:, ~sheet_df.columns.astype(str).str.startswith("Unnamed")].copy()

            year_col = next(
                (
                    col
                    for col in sheet_df.columns
                    if "jahr" in str(col).lower() or "time_period" in str(col).lower()
                ),
                None,
            )
            if year_col is not None:
                sheet_df["time_period"] = pd.to_numeric(sheet_df[year_col], errors="coerce")
            else:
                inferred_year = infer_year_from_sheet_name(sheet_name)
                if inferred_year is not None:
                    sheet_df["time_period"] = inferred_year

            if "time_period" in sheet_df.columns:
                sheet_df["time_period"] = pd.to_numeric(sheet_df["time_period"], errors="coerce")

            if "Alter" in sheet_df.columns:
                sheet_df["Alter"] = pd.to_numeric(sheet_df["Alter"], errors="coerce")
                sheet_df = sheet_df[sheet_df["Alter"].notna()].copy()

            if "Bewohnertyp" in sheet_df.columns:
                sheet_df = sheet_df[sheet_df["Bewohnertyp"].notna()].copy()

            for col in numeric_columns:
                if col in sheet_df.columns:
                    sheet_df[col] = pd.to_numeric(sheet_df[col], errors="coerce")

            sheet_df["source_sheet"] = sheet_name
            sheet_df["sheet_type"] = sheet_type
            frames.append(sheet_df)

        if not frames:
            return None

        df = pd.concat(frames, ignore_index=True)
        if "time_period" in df.columns:
            df = df[df["time_period"].between(2019, 2024, inclusive="both") | df["time_period"].isna()].copy()

        print(f"✓ Loaded {sheet_type}: {len(matching_sheets)} sheets, {df.shape[0]} rows")
        return df

    except Exception as e:
        print(f"❌ Loading failed: {e}")
        return None


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardisiere Spaltennamen (lowercase, strip whitespace).
    
    Args:
        df: Eingabe-DataFrame
        
    Returns:
        DataFrame mit standardisierten Spaltennamen
    """
    df.columns = df.columns.str.lower().str.strip()
    return df


def get_canton_mapping() -> dict:
    """
    Erstelle Mapping zwischen 2-letter Kantonscodes und BFS-Codes.
    
    Returns:
        Dictionary: {canton_code: bfs_code}
    """
    canton_mapping = {
        'ZH': 'CH010', 'BE': 'CH020', 'LU': 'CH030', 'UR': 'CH040',
        'SZ': 'CH050', 'OW': 'CH060', 'NW': 'CH061', 'GL': 'CH062',
        'ZG': 'CH063', 'FR': 'CH064', 'SO': 'CH065', 'BS': 'CH066',
        'BL': 'CH067', 'SH': 'CH070', 'AR': 'CH071', 'AI': 'CH072',
        'SG': 'CH073', 'GR': 'CH074', 'AG': 'CH075', 'TG': 'CH076',
        'TI': 'CH077', 'VD': 'CH078', 'VS': 'CH079', 'NE': 'CH080',
        'GE': 'CH081', 'JU': 'CH082'
    }
    return canton_mapping



# -----------------------------------------
# 3. MAIN: Daten laden und verarbeiten
# -----------------------------------------

try:
    if not RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH.exists():
        fallback_path = BASE_PATH / "data" / "whoOwns" / "raw" / "bfs_bewohnertyp_groesse.xlsx"
        RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH = fallback_path

    # Selects Daten laden
    df_selects_2023 = load_selects_data(RAW_SELECTS_2023_PATH)
    df_selects_2019 = load_selects_data(RAW_SELECTS_2019_PATH)  # NEU
    df_selects_2015 = load_selects_2015_data(RAW_SELECTS_2015_PATH)  # NEU

    # WhoOwns Daten laden
    df_whoowns = load_wohneigentums_data(RAW_WOHNEIGENTUMSQUOTE_PATH)
    df_whoowns_geo = load_geo_metadata(RAW_WOHNEIGENTUMS_META_PATH)
    df_bfs_bewohnertyp = load_bfs_bewohnertyp_groesse_data(RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH, "bewohnertyp")
    df_bfs_wohnflaeche = load_bfs_bewohnertyp_groesse_data(RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH, "wohnflaeche")

    # WhoOwns mit GEO-Metadaten anreichern
    if df_whoowns is not None and df_whoowns_geo is not None:
        geo_col = next((col for col in df_whoowns.columns if str(col).strip().lower() == "geo"), None)
        if geo_col is not None:
            df_whoowns[geo_col] = df_whoowns[geo_col].astype(str).str.strip()
            df_whoowns = df_whoowns.merge(
                df_whoowns_geo,
                left_on=geo_col,
                right_on="CODE",
                how="left",
            )
            print(
                "✓ WhoOwns mit GEO-Metadaten angereichert "
                f"(Match-Rate: {(df_whoowns['LABEL_DE'].notna().mean() * 100):.1f}%)"
            )
        else:
            print("⚠️  Spalte 'geo' nicht in WhoOwns-Daten gefunden. GEO-Merge uebersprungen.")

    # Standardisierung
    print("\n" + "="*50)
    print("DATA STANDARDIZATION")
    print("="*50)
    


    if df_selects_2023 is not None:
        df_selects_2023 = standardize_columns(df_selects_2023)
        df_selects_2023["year"] = 2023  # Jahresspalte hinzufügen
        df_selects_2023.to_csv(PROCESSED_SELECTS_2023_PATH, index=False)
        print(f"✓ Selects 2023 saved to: {PROCESSED_SELECTS_2023_PATH}")

    if df_selects_2019 is not None:
        df_selects_2019 = standardize_columns(df_selects_2019)
        df_selects_2019["year"] = 2019  # NEU
        df_selects_2019.to_csv(PROCESSED_SELECTS_2019_PATH, index=False)
        print(f"✓ Selects 2019 saved to: {PROCESSED_SELECTS_2019_PATH}")

    if df_selects_2015 is not None:
        df_selects_2015 = standardize_columns(df_selects_2015)
        df_selects_2015["year"] = 2015  # NEU
        df_selects_2015.to_csv(PROCESSED_SELECTS_2015_PATH, index=False)
        print(f"✓ Selects 2015 saved to: {PROCESSED_SELECTS_2015_PATH}")

    if df_whoowns is not None:
        df_whoowns = standardize_columns(df_whoowns)
        print("✓ WhoOwns columns standardized")

        df_whoowns.to_csv(PROCESSED_WOHNEIGENTUMSQUOTE_PATH, index=False)
        print(f"✓ WhoOwns data saved to: {PROCESSED_WOHNEIGENTUMSQUOTE_PATH}")

    if df_bfs_bewohnertyp is not None:
        df_bfs_bewohnertyp = standardize_columns(df_bfs_bewohnertyp)
        print("✓ BFS Bewohnertyp columns standardized")

        df_bfs_bewohnertyp.to_csv(PROCESSED_BFS_BEWOHNERTYP_PATH, index=False)
        print(f"✓ BFS Bewohnertyp data saved to: {PROCESSED_BFS_BEWOHNERTYP_PATH}")

    if df_bfs_wohnflaeche is not None:
        df_bfs_wohnflaeche = standardize_columns(df_bfs_wohnflaeche)
        print("✓ BFS Wohnflaeche columns standardized")

        df_bfs_wohnflaeche.to_csv(PROCESSED_BFS_WOHNFLAECHE_PATH, index=False)
        print(f"✓ BFS Wohnflaeche data saved to: {PROCESSED_BFS_WOHNFLAECHE_PATH}")
    
    
except FileNotFoundError as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# -----------------------------------------
# 4. WhoPays – OKP Gesundheitsdaten
# -----------------------------------------
try:
    df_okp_cohort, df_okp_birth_year = run_whopays_pipeline()
    print("✓ WhoPays OKP-Daten geladen und disaggregiert")
except Exception as e:
    print(f"❌ WhoPays Pipeline fehlgeschlagen: {e}")

# -----------------------------------------
# 5. WhoPays – AHV Einnahmen
# -----------------------------------------
try:
    df_ahv_cohort, df_ahv_birth_year, df_ahv_makro = run_ahv_einnahmen_pipeline()
    print("✓ WhoPays AHV-Einnahmen geladen und disaggregiert")
except Exception as e:
    print(f"❌ AHV Einnahmen Pipeline fehlgeschlagen: {e}")

# -----------------------------------------
# 6. WhoPays – AHV Ausgaben (Rentendaten)
# -----------------------------------------
try:
    df_ahv_ausgaben = run_ahv_ausgaben_pipeline()
    print("✓ WhoPays AHV-Ausgaben (Rentendaten) geladen")
except Exception as e:
    print(f"❌ AHV Ausgaben Pipeline fehlgeschlagen: {e}")