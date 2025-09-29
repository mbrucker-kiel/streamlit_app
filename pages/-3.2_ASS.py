import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

st.title("3.2 Acetylsalicylsäure bei ST-Hebungsinfarkt")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

# Qualitätsziel und Rationale mit Markdown
st.markdown(
    """
## Qualitätsziel
Patienten mit STEMI erhalten ASS gemäß aktueller Empfehlungen.
                                                            
## Rationale 
Patienten mit akutem ST-Hebungs-Myokardinfarkt (STEMI) sollen gemäß der
Leitlinie der European Society of Cardiology so schnell wie möglich Acetylsalicylsäure (ASS) erhalten, sofern keine Kontraindikation vorliegt (Klasse-I-Empfehlung, Evidenz B).

"""
)

# Berechnungsgrundlage
st.markdown(
    """
## Berechnungsgrundlage
            
**Zähler**
Fälle mit dokumentierter ASS-Gabe bei Primäreinsätzen in der Notfallrettung bei Patienten mit dokumentiertem STEMI unter Ausschluss von Behandlungsverweigerung und Palliativsituationen            

**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit dokumentiertem STEMI unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                                                                    
**Ergebnisdarstellung:** Anteil in Prozent
                      
"""
)

# Daten laden
df_index = data_loading("Index")
df_ass = data_loading("Medikamente", med_name="Acetylsalicylsäure")

# Datenvorverarbeitung für ASS-Gabe bei STEMI
st.subheader("Auswertung der ASS-Gabe bei STEMI")

# Filter für STEMI-Fälle - prüfe, ob 'stemi' in der Diagnose vorkommt (case-insensitive)
if "leadingDiagnosis" not in df_index.columns:
    st.error("Spalte 'leadingDiagnosis' nicht gefunden!")
else:
    # Konvertiere alle Diagnosen zu Strings und führe einen Case-insensitive Vergleich durch
    df_index["leadingDiagnosis"] = df_index["leadingDiagnosis"].astype(str)
    mask_stemi = df_index["leadingDiagnosis"].str.lower().str.contains(
        "stemi", na=False
    ) & ~df_index["leadingDiagnosis"].str.lower().str.contains("nstemi", na=False)
    # Kombinierte Maske
    mask_herzinfarkt = mask_stemi

    # STEMI-Fälle filtern
    stemi_faelle = df_index[mask_herzinfarkt]

    # Anzahl der STEMI-Fälle anzeigen
    anzahl_stemi = len(stemi_faelle)
    st.write(f"Anzahl der identifizierten STEMI-Fälle: {anzahl_stemi}")

    if anzahl_stemi == 0:
        st.warning(
            "Keine STEMI-Fälle gefunden! Überprüfen Sie die Daten oder die Filterkriterien."
        )
    else:
        # Protokoll-IDs der STEMI-Fälle
        stemi_protokoll_ids = stemi_faelle["protocolId"].unique()

        # Fälle mit ASS-Gabe
        ass_gabe = df_ass[df_ass["protocolId"].isin(stemi_protokoll_ids)]

        # Anzahl der STEMI-Fälle mit ASS-Gabe
        anzahl_mit_ass = len(ass_gabe["protocolId"].unique())

        # Berechne Prozentsatz
        prozent_gesamt = (
            (anzahl_mit_ass / anzahl_stemi * 100) if anzahl_stemi > 0 else 0
        )

        # Gesamtergebnis anzeigen
        st.subheader("Gesamtergebnis")
        st.metric(
            label="Anteil der STEMI-Patienten mit ASS-Gabe",
            value=f"{prozent_gesamt:.1f}%",
            delta=(
                f"{prozent_gesamt - 100:.1f}%"
                if prozent_gesamt < 100
                else "Ziel erreicht"
            ),
        )

        # Visualisierung des Gesamtergebnisses mit go.Indicator
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=prozent_gesamt,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Erfüllungsgrad des Qualitätsziels"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 50], "color": "red"},
                        {"range": [50, 80], "color": "orange"},
                        {"range": [80, 95], "color": "yellow"},
                        {"range": [95, 100], "color": "green"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 100,
                    },
                },
            )
        )
        st.plotly_chart(fig)

        # Detailansicht der STEMI-Fälle mit und ohne ASS-Gabe
        st.subheader("Details zu STEMI-Fällen")

        # Erstelle ein DataFrame mit Status der ASS-Gabe für jeden STEMI-Fall
        stemi_mit_ass_status = pd.DataFrame(
            {
                "protocolId": stemi_protokoll_ids,
                "ASS_gegeben": [
                    pid in ass_gabe["protocolId"].unique()
                    for pid in stemi_protokoll_ids
                ],
            }
        )

        # Zusammenfassung als Balkendiagramm
        status_counts = stemi_mit_ass_status["ASS_gegeben"].value_counts().reset_index()
        status_counts.columns = ["ASS gegeben", "Anzahl"]
        status_counts["ASS gegeben"] = status_counts["ASS gegeben"].map(
            {True: "Ja", False: "Nein"}
        )

        fig_bar = px.bar(
            status_counts,
            x="ASS gegeben",
            y="Anzahl",
            color="ASS gegeben",
            color_discrete_map={"Ja": "green", "Nein": "red"},
            text="Anzahl",
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(title_text="STEMI-Fälle mit und ohne ASS-Gabe")
        st.plotly_chart(fig_bar)

        # Detaillierte Datenansicht
        st.subheader("Detaillierte Datenübersicht")

        # Merge mit Original-Daten für mehr Informationen
        detail_view = pd.merge(
            stemi_mit_ass_status,
            stemi_faelle[["protocolId", "leadingDiagnosis"]],
            on="protocolId",
            how="left",
        )

        # Anzeige der Details, sortiert nach ASS-Gabe-Status
        detail_view_sorted = detail_view.sort_values(
            by=["ASS_gegeben"], ascending=False
        )
        st.dataframe(detail_view_sorted)

        # Optional: Zeige die tatsächlichen ASS-Dosen für Fälle, die ASS erhalten haben
        if anzahl_mit_ass > 0:
            st.subheader("Details zur ASS-Dosierung")
            ass_details = ass_gabe[
                ["protocolId", "med_name", "dose", "dose_unit", "route"]
            ]
            st.dataframe(ass_details)
