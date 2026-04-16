# Daten-Ladevorgang: Strukturiertes Dokument

## 📋 Übersicht

Dieses Dokument beschreibt den vollständigen Prozess zum Laden, Verarbeiten und Speichern der Daten für das PODSV-Visualisierungsprojekt.

---

## 🗂️ Ordnerstruktur

```
project_root/
├── data/
│   ├── raw/                          # Rohdaten (unverändert)
│   │   ├── 2634_Selects2023_PES_Data_v2.0.csv
│   │   └── 2634_Selects2023_PES_Data_v2.0/  (Alternativformate)
│   │
│   ├── processed/                    # Verarbeitete Daten (bereit für Analysen)
│   │   └── selects_2023_clean.csv
│   │
│   └── whoOwns/                      # Zusatzdaten (Wohneigentum)
│       ├── wohneigentumsquote_kanton_2026.csv
│       └── bfs/
│
└── data_acquisition/
    ├── load_select_2023.py          # Hauptladevorgang
    └── DATA_LOADING_GUIDE.md        # Dieses Dokument
```

---

## 🔄 Ladevorgang: Schritte

### **Schritt 1: Rohdaten laden** 
- **Quelle:** `data/raw/2634_Selects2023_PES_Data_v2.0.csv`
- **Format:** CSV mit Semikolon-Trennzeichen (`;`)
- **Kodierung:** UTF-8 (angenommen)
- **Pandas-Parameter:**
  ```python
  pd.read_csv(path, sep=";", low_memory=False)
  ```

**Wichtige Informationen:**
- Die Rohdatei sollte **NICHT verändert** werden
- Trennzeichen: Semikolon (`;`), nicht Komma!
- `low_memory=False` verhindert Typ-Warnung bei gemischten Datentypen

---

### **Schritt 2: Grundlegende Standardisierung**
Nach dem Laden folgende Normalisierungen:

| Schritt | Aktion | Ziel |
|---------|--------|------|
| Spaltennamen | Lowercase + Strip | Konsistenz |
| Datentypen | Überprüfung | Korrekte Typen |
| Fehlende Werte | `dropna()` / `fillna()` | Umgang mit NaN-Werten |
| Duplikate | `drop_duplicates()` | Eindeutige Datensätze |

**Beispiel-Code:**
```python
# Spaltennamen standardisieren
df.columns = df.columns.str.lower().str.strip()

# Duplikate entfernen
df = df.drop_duplicates()

# Fehlende Werte behandeln (je nach Spalte unterschiedlich)
df = df.dropna(subset=['critical_columns'])
```

---

### **Schritt 3: Variablenauswahl und Feature Engineering**
Nur die benötigten Spalten beibehalten:

```python
# Beispiel verwandter Variablen
required_columns = [
    'id',                    # Eindeutige ID
    'survey_year',          # Erhebungsjahr
    'region',               # Kanton/Region
    'demographic_vars',     # Demografische Variablen
    # ... weitere Variablen
]

df_selected = df[required_columns]
```

---

### **Schritt 4: Verarbeitete Daten speichern**
- **Ziel:** `data/processed/selects_2023_clean.csv`
- **Format:** CSV mit Komma-Trennzeichen (`,`) — Standard für verarbeitete Daten
- **Indizes:** `index=False` (keine Zeilennummern speichern)

```python
df.to_csv(PROCESSED_PATH, index=False)
```

---

## 📊 Datenverarbeitung: Typische Operationen

### **Datentypkonvertierung**
```python
# Kategorische Variablen
categorical_cols = ['region', 'kategorie']
df[categorical_cols] = df[categorical_cols].astype('category')

# Numerische Variablen
numeric_cols = ['einkommen', 'alter']
df[numeric_cols] = df[numeric_cols].astype('float64')
```

### **Umgang mit Fehlwerten**
```python
# Fehlwertübersicht
print(df.isnull().sum())

# Strategien:
df_clean = df.dropna()                    # Löschen
df_clean = df.fillna(df.mean())          # Mit Mittelwert füllen
df_clean = df.fillna('Unbekannt')        # Mit Text füllen
```

### **Spalten umbennen**
```python
rename_mapping = {
    'old_column_name': 'new_column_name',
    'Kanton': 'canton'
}
df = df.rename(columns=rename_mapping)
```

---

## 🔗 Zusatzdaten integrieren

### **Wohneigentum-Daten** (`whoOwns/`)
```python
df_owns = pd.read_csv("data/whoOwns/wohneigentumsquote_kanton_2026.csv")

# Mit Hauptdatensatz mergen (auf Kanton)
df = df.merge(df_owns, left_on='canton', right_on='kanton', how='left')
```

---

## ✅ Qualitätskontrolle

Nach jedem Verarbeitungsschritt überprüfen:

```python
# Grundstatistiken
print(df.describe())           # Numerische Zusammenfassung
print(df.info())               # Datentypen & Null-Werte
print(df.shape)                # Zeilen & Spalten
print(df.duplicated().sum())   # Duplikate

# Erste/Letzte Zeilen
print(df.head())
print(df.tail())
```

---

## 🎯 Best Practices

| ✅ Empfohlen | ❌ Nicht empfohlen |
|------------|-----------------|
| Rohdaten in `raw/` unverändert lassen | Rohdaten modifizieren |
| Trennzeichen explizit angeben | Trennzeichen-Autodetection nutzen |
| Verarbeitungsschritte dokumentieren | "Große" Operation ohne Logs |
| Verarbeitete Daten speichern | Nur im RAM arbeiten |
| Fehler-Handling implementieren | Fehler ignorieren |
| Pandas `info()` zum Debuggen | Blind Code schreiben |

---

## 🐛 Häufige Probleme & Lösungen

| Problem | Ursache | Lösung |
|---------|--------|--------|
| `FileNotFoundError` | Falscher Pfad | `Path` absolut oder relativ überprüfen |
| Encoding-Fehler | UTF-8 angenommen, aber Latin-1 | `encoding='latin-1'` in `read_csv()` |
| Falsche Spalten | Trennzeichen falsch | `sep=";"` statt `sep=","` |
| Speicherüberlauf | Zu große Datei | Mit `chunksize` kleinere Teile laden |
| Merkwürdige Zahlen | Tausender-Trennzeichen | `thousands=','` und `decimal='.'` |

---

## 📝 Workflow Summary

```
1. Rohdaten laden
   ↓
2. Spaltennamen standardisieren
   ↓
3. Datentypen überprüfen & konvertieren
   ↓
4. Fehlwerte behandeln
   ↓
5. Duplikate entfernen (falls nötig)
   ↓
6. Variablen auswählen/Feature Engineering
   ↓
7. Zusatzdaten mergen (optional)
   ↓
8. Qualitätskontrolle durchführen
   ↓
9. Verarbeitete Daten speichern
```

---

## 📚 Weiterführende Ressourcen

- [Pandas Dokumentation: read_csv()](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)
- [Pandas Data Cleaning](https://pandas.pydata.org/docs/user_guide/missing_data.html)
- [Path (pathlib) Dokumentation](https://docs.python.org/3/library/pathlib.html)

---

## 👤 Versionshistorie

| Version | Datum | Notizen |
|---------|-------|---------|
| 1.0 | 2026-04-16 | Initiale Dokumentation |
