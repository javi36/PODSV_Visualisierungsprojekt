from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
	page_title="Generational Conflict in Housing",
	page_icon="🏠",
	layout="wide",
)


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = BASE_DIR / "data" / "whoOwns" / "processed" / "wohneigentumsquote_kanton_2026_clean.csv"


@st.cache_data
def load_data(csv_path: Path) -> pd.DataFrame:
	"""Load CSV data with basic error handling."""
	return pd.read_csv(csv_path)


def main() -> None:
	st.title("Generationenkonflikt Wohnen")
	st.caption("Erste Streamlit-Vorlage fuer das Deployment")

	with st.sidebar:
		st.header("Einstellungen")
		use_default = st.checkbox("Standard-Datensatz verwenden", value=True)

		custom_path_input = st.text_input(
			"Eigener CSV-Pfad (optional)",
			value=str(DEFAULT_DATA_PATH),
			disabled=use_default,
		)

		st.markdown("---")
		st.write("Diese Vorlage ist der Startpunkt fuer eure finale Visualisierung.")

	data_path = DEFAULT_DATA_PATH if use_default else Path(custom_path_input)

	if not data_path.exists():
		st.error(f"Datei nicht gefunden: {data_path}")
		st.info("Passe den Pfad in der Sidebar an oder aktiviere den Standard-Datensatz.")
		st.stop()

	try:
		df = load_data(data_path)
	except Exception as exc:  # noqa: BLE001
		st.error("Fehler beim Laden der Daten.")
		st.exception(exc)
		st.stop()

	tab_intro, tab_data, tab_viz, tab_story = st.tabs(
		["Projekt", "Daten", "Visualisierung", "Story"]
	)

	with tab_intro:
		st.subheader("Projektidee")
		st.write(
			"Diese App untersucht moegliche Generationenkonflikte rund um "
			"Wohneigentum in der Schweiz."
		)
		st.info(
			"To-do: Forschungsfrage, Zielgruppe und Kernbotschaften aus "
			"euren Design-Dokumenten ergaenzen."
		)

	with tab_data:
		c1, c2, c3 = st.columns(3)
		c1.metric("Zeilen", f"{len(df):,}".replace(",", "'"))
		c2.metric("Spalten", df.shape[1])
		c3.metric("Fehlwerte", int(df.isna().sum().sum()))

		st.subheader("Datenvorschau")
		st.dataframe(df.head(20), use_container_width=True)

		with st.expander("Spalten und Datentypen"):
			schema_df = pd.DataFrame(
				{
					"Spalte": df.columns,
					"Datentyp": [str(dtype) for dtype in df.dtypes],
					"Missing": [int(df[col].isna().sum()) for col in df.columns],
				}
			)
			st.dataframe(schema_df, use_container_width=True)

	with tab_viz:
		st.subheader("Erste Explorations-Visualisierung")
		numeric_cols = df.select_dtypes(include="number").columns.tolist()

		if not numeric_cols:
			st.warning("Keine numerischen Spalten fuer einen schnellen Chart gefunden.")
		else:
			selected_col = st.selectbox(
				"Numerische Variable waehlen",
				options=numeric_cols,
				index=0,
			)
			st.bar_chart(df[selected_col].value_counts(dropna=False).head(20))

		st.info(
			"To-do: Hier spaeter die finalen Diagramme aus eurem Visual Mapping einbauen."
		)

	with tab_story:
		st.subheader("Narrative Struktur")
		st.markdown(
			"""
			1. **Kontext:** Warum ist Wohneigentum generationell relevant?
			2. **Befund:** Wo zeigen sich Unterschiede zwischen Altersgruppen?
			3. **Interpretation:** Welche sozialen oder politischen Faktoren spielen mit?
			4. **Fazit:** Welche offenen Fragen bleiben fuer die Diskussion?
			"""
		)
		st.success("To-do: Storyline mit konkreten Ergebnissen und Quellen verknuepfen.")


if __name__ == "__main__":
	main()
