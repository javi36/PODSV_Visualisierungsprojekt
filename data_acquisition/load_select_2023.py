# =========================================
# Load and prepare Selects 2023 data
# =========================================

from pathlib import Path
import pandas as pd

# -----------------------------------------
# 1. Paths definieren
# -----------------------------------------
BASE_PATH = Path(__file__).resolve().parents[1]

RAW_PATH = BASE_PATH / "data" / "raw" / "2634_Selects2023_PES_Data_v2.0.csv"
PROCESSED_PATH = BASE_PATH / "data" / "processed" / "selects_2023_clean.csv"

# Ordner sicherstellen
PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)

# -----------------------------------------
# 2. Daten laden
# -----------------------------------------
print("Loading data...")
print("Trying to load from:", RAW_PATH)
print("File exists:", RAW_PATH.exists())

df = pd.read_csv(RAW_PATH, sep=";", low_memory=False)

print(f"Raw shape: {df.shape}")

# -----------------------------------------
# 3. Minimale Standardisierung
# -----------------------------------------
df.columns = df.columns.str.lower().str.strip()

# -----------------------------------------
# 4. Erstmal ganze Datei speichern
# -----------------------------------------
# Später können wir gezielt Variablen auswählen,
# sobald wir die echten Spaltennamen geprüft haben.

print("Saving processed data...")
df.to_csv(PROCESSED_PATH, index=False)

print(f"Saved to: {PROCESSED_PATH}")
print("Done ✅")

print(df.columns.tolist())