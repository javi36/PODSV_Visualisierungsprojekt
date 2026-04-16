# =========================================
# Load and prepare Selects 2023 data with supplementary data
# =========================================

from pathlib import Path
import pandas as pd
import sys

# -----------------------------------------
# 1. Paths definieren
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

# Selects 2023 Daten
RAW_SELECTS_PATH = BASE_PATH / "data" / "raw" / "2634_Selects2023_PES_Data_v2.0.csv"
PROCESSED_PATH = BASE_PATH / "data" / "processed" / "selects_2023_clean.csv"

# WhoOwns Daten (Wohneigentum)
WHOOWNS_PATH = BASE_PATH / "data" / "whoOwns" / "wohneigentumsquote_kanton_2026.csv"

# Ordner sicherstellen
PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)


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
    df_whoowns = load_whoowns_data(WHOOWNS_PATH)
    
    # Standardisierung
    print("\n" + "="*50)
    print("DATA STANDARDIZATION")
    print("="*50)
    
    df_selects = standardize_columns(df_selects)
    print("✓ Selects columns standardized")
    
    if df_whoowns is not None:
        df_whoowns = standardize_columns(df_whoowns)
        print("✓ WhoOwns columns standardized")
    
    
except FileNotFoundError as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)