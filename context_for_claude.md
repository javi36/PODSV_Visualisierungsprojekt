# Context für Claude – PODSV_VISUALISIERUNGSPROJEKT

## Projekt
Universitätsprojekt: Generationenvertrag Schweiz kritisch beleuchten.
Schwerpunkt: Datenvisualisierung → Streamlit Dashboard.

## Meine Ebene: Who Pays (Ebene 2)
Cashflow zwischen Generationen: OKP + AHV.

## Generationsdefinitionen
- ≥2013: Generation Alpha
- 1997–2012: Generation Z
- 1981–1996: Millennials
- 1965–1980: Generation X
- 1946–1964: Babyboomers
- ≤1945: Silent Generation

## Datenstand
- OKP: 2012–2024 (2016 okp_premium interpoliert aus 2015/2017)
- AHV Einnahmen: 2010–2024
- AHV Ausgaben: 2012–2024
- Alle CSVs in: data/whopays/processed_whopays/

## Wichtige methodische Entscheide
- beneficiaries_count wird populationsgewichtet disaggregiert (nicht direct copy)
- Prämienverbilligung: pro Versicherten (nicht pro Bezüger)
- AHV-Rente: pro Bezüger, nur für Bezüger-Generationen
- Bruttolohn geschätzt via AHV-Satz 8.7% (AN+AG kombiniert)

## Offene Pendenzen
- load_whopays.py + load_ahv_einnahmen.py + load_ahv_ausgaben.py 
  in load_sources.py integrieren
- OKP-Daten bis 2000 vorhanden (XLS), AHV-Einnahmen nur bis 2010
  (BSV angefragt für frühere Daten)
- EDA abschliessen: eda_whopays.ipynb bereinigen

## Arbeitsweise
- Prompts für Claude Code hier vorbereiten, dann in Claude Code ausführen
- Kein Code ohne Rücksprache bei methodischen Fragen