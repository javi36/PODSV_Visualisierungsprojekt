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

# WhoDecides Data
RAW_SELECTS_PATH = BASE_PATH / "data" / "whodecide" / "raw" / "2634_Selects2023_PES_Data_v2.0.csv"
PROCESSED_SELECTS_PATH = BASE_PATH / "data" / "whodecide" / "processed" / "selects_2023_clean.csv"

# WhoOwns Data
RAW_WHOOWNS_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "wohneigentumsquote_kanton_2026.csv"
RAW_ANFRAGE_MARTINEZ_PATH = BASE_PATH / "data" / "whoOwns" / "raw" / "Anfrage_Martinez_20260414.xlsx"
PROCESSED_WHOOWNS_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "wohneigentumsquote_kanton_2026_clean.csv"
PROCESSED_ANFRAGE_MARTINEZ_PATH = BASE_PATH / "data" / "whoOwns" / "processed" / "anfrage_martinez_20260414_clean.csv"

# Ordner für verarbeitete Daten sicherstellen 
PROCESSED_SELECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
PROCESSED_WHOOWNS_PATH.parent.mkdir(parents=True, exist_ok=True)


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
    print("LOADING SELECTS 2023 DATA")
    print("="*50)
    
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    
    print(f"📂 Loading from: {path}")
    print(f"   File size: {path.stat().st_size / (1024**2):.2f} MB")
    
    df = pd.read_csv(path, sep=";", low_memory=False)
    
    print(f"✓ Loaded: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"   Memory usage: {df.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
    
    return df


def load_whoowns_data(path: Path) -> pd.DataFrame:
    """
    Lade Wohneigentum-Daten nach Kanton.
    
    Hinweis: BFS-Daten verwenden Semikolon als Trennzeichen!
    
    Args:
        path: Pfad zur CSV-Datei
        
    Returns:
        DataFrame mit Wohneigentum-Daten oder None wenn nicht vorhanden
    """
    print("\n" + "="*50)
    print("LOADING WHOOWNS DATA (Wohneigentum)")
    print("="*50)
    
    if not path.exists():
        print(f"⚠️  Datei nicht gefunden: {path}")
        print("   Fortfahren ohne WhoOwns-Daten...")
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
        print("   Fortfahren ohne WhoOwns-Daten...")
        return None


def load_anfrage_martinez_data(path: Path) -> pd.DataFrame:
    """
    Lade Anfrage-Martinez-Daten (Excel).

    Args:
        path: Pfad zur Excel-Datei

    Returns:
        DataFrame mit Anfrage-Daten oder None wenn nicht vorhanden
    """
    print("\n" + "="*50)
    print("LOADING ANFRAGE MARTINEZ DATA")
    print("="*50)

    if not path.exists():
        print(f"⚠️  Datei nicht gefunden: {path}")
        print("   Fortfahren ohne Anfrage-Martinez-Daten...")
        return None

    print(f"📂 Loading from: {path}")

    try:
        # Header starts on row 3 in the source file (title and year rows above it).
        df = pd.read_excel(path, sheet_name="SE2024", header=2)

        # Keep only real data columns and drop footnote/comment columns.
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]

        # Keep only rows with valid numeric age values.
        df["Alter"] = pd.to_numeric(df["Alter"], errors="coerce")
        df = df.dropna(subset=["Alter", "Bewohnertyp"]).copy()

        # Parse numeric indicators; non-numeric placeholders (e.g. X) become NaN.
        numeric_columns = [
            "Absolute Zahlen",
            "Vertrauens-intervall : \n± (in %)",
            "Anteil in %",
            "Vertrauens-\nintervall : \n± (in %-Pkte)",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Capture the survey year from the metadata rows if available.
        meta = pd.read_excel(path, sheet_name="SE2024", header=None, nrows=2)
        year_candidates = pd.to_numeric(meta.iloc[1], errors="coerce").dropna()
        if not year_candidates.empty:
            df["year"] = int(year_candidates.iloc[0])

        print(f"✓ Loaded: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"   Columns: {df.columns.tolist()}")

        return df

    except Exception as e:
        print(f"❌ Loading failed: {e}")
        print("   Fortfahren ohne Anfrage-Martinez-Daten...")
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
    df_whoowns = load_whoowns_data(RAW_WHOOWNS_PATH)
    df_anfrage_martinez = load_anfrage_martinez_data(RAW_ANFRAGE_MARTINEZ_PATH)
    
    # Standardisierung
    print("\n" + "="*50)
    print("DATA STANDARDIZATION")
    print("="*50)
    
    df_selects = standardize_columns(df_selects)
    print("✓ Selects columns standardized")

    df_selects.to_csv(PROCESSED_SELECTS_PATH, index=False)
    print(f"✓ Selects data saved to: {PROCESSED_SELECTS_PATH}")
    
    if df_whoowns is not None:
        df_whoowns = standardize_columns(df_whoowns)
        print("✓ WhoOwns columns standardized")

        df_whoowns.to_csv(PROCESSED_WHOOWNS_PATH, index=False)
        print(f"✓ WhoOwns data saved to: {PROCESSED_WHOOWNS_PATH}")

    if df_anfrage_martinez is not None:
        df_anfrage_martinez = standardize_columns(df_anfrage_martinez)
        print("✓ Anfrage Martinez columns standardized")

        df_anfrage_martinez.to_csv(PROCESSED_ANFRAGE_MARTINEZ_PATH, index=False)
        print(f"✓ Anfrage Martinez data saved to: {PROCESSED_ANFRAGE_MARTINEZ_PATH}")
    
    
except FileNotFoundError as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)