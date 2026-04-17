# =========================================
# Load and prepare data sources for WhoDecides, WhoOwns and Whopays.
# =========================================

from pathlib import Path
import pandas as pd
import sys

# -----------------------------------------
# 1. Define Paths and Constants
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

# RAW Paths for WhoDecides Data
RAW_SELECTS_PATH = BASE_PATH / "data" / "whodecide" / "raw" / "2634_Selects2023_PES_Data_v2.0.csv"

# Processed Paths for WhoDecides Data
PROCESSED_SELECTS_PATH = BASE_PATH / "data" / "whodecide" / "processed" / "selects_2023_clean.csv"

# RAW Paths for WhoOwns Data
RAW_WOHNEIGENTUMSQUOTE_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "wohneigentumsquote_kanton_2026.csv"
RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "bfs_bewohnertyp_groesse.xlsx"

# Processed Paths for WhoOwns Data
PROCESSED_WOHNEIGENTUMSQUOTE_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "wohneigentumsquote_kanton_2026_clean.csv"
PROCESSED_BFS_BEWOHNERTYP_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "bfs_bewohnertyp_20260414_clean.csv"
PROCESSED_BFS_WOHNFLAECHE_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "bfs_wohnflaeche_20260414_clean.csv"

# Ordnerstruktur sicherstellen
PROCESSED_SELECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    
    df = pd.read_csv(path, sep=";", low_memory=False)
    
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


def load_bfs_bewohnertyp_groesse_data(path: Path, sheet_type: str) -> pd.DataFrame:
    """
    Lade BFS-Bewohnertyp-Größe-Daten (Excel).

    Args:
        path: Pfad zur Excel-Datei

    Args:
        sheet_type: "bewohnertyp" oder "wohnflaeche"

    Returns:
        DataFrame mit BFS-Daten fuer genau ein Sheet oder None wenn nicht vorhanden
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

        sheet_map = {
            "bewohnertyp": ["Bewohnertyp", "SE2024"],
            "wohnflaeche": ["Wohnflaeche", "Wohnfläche", "GWS-STATPOP2024"],
        }

        if sheet_type not in sheet_map:
            raise ValueError(f"Unbekannter sheet_type: {sheet_type}")

        sheet_name = next((s for s in sheet_map[sheet_type] if s in available_sheets), None)
        if sheet_name is None:
            print(f"⚠️  Kein passendes Sheet fuer '{sheet_type}' gefunden. Verfuegbar: {available_sheets}")
            return None

        numeric_columns = [
            "Absolute Zahlen",
            "Vertrauens-intervall : \n± (in %)",
            "Anteil in %",
            "Vertrauens-\nintervall : \n± (in %-Pkte)",
            "Wohnfläche (in m2) pro Person",
        ]

        df = pd.read_excel(path, sheet_name=sheet_name, header=2)
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")].copy()

        if "Alter" in df.columns:
            df["Alter"] = pd.to_numeric(df["Alter"], errors="coerce")
            df = df[df["Alter"].notna()].copy()

        if "Bewohnertyp" in df.columns:
            df = df[df["Bewohnertyp"].notna()].copy()

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["sheet_type"] = sheet_type
  
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
    # Selects Daten laden
    df_selects = load_selects_data(RAW_SELECTS_PATH)
    
    # WhoOwns Daten laden
    df_whoowns = load_wohneigentums_data(RAW_WOHNEIGENTUMSQUOTE_PATH)
    df_bfs_bewohnertyp = load_bfs_bewohnertyp_groesse_data(RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH, "bewohnertyp")
    df_bfs_wohnflaeche = load_bfs_bewohnertyp_groesse_data(RAW_BFS_BEWOHNERTYP_WOHNFLAECHE_PATH, "wohnflaeche")

    # Standardisierung
    print("\n" + "="*50)
    print("DATA STANDARDIZATION")
    print("="*50)
    
    if df_selects is not None:
        df_selects = standardize_columns(df_selects)
        print("✓ Selects columns standardized")

        df_selects.to_csv(PROCESSED_SELECTS_PATH, index=False)
        print(f"✓ Selects data saved to: {PROCESSED_SELECTS_PATH}")
    
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