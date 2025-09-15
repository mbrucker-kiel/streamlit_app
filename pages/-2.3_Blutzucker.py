import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("2.3 Blutzucker-Messung bei Bewusstseinsminderung")


bz_df = data_loading("bz")
gcs_df = data_loading("GCS")

# Datenvorverarbeitung
# 1. Finde alle Transporte mit GCS < 15 
# (Bewusstseinsminderung)
mask_gcs_lt_15 = gcs_df["value_num"] < 15
mask_gcs_gt_0 = gcs_df["value_num"] > 0
mask_type_neuro = gcs_df["type"] == "eb_neuro"

bewusstsein_gemindert = gcs_df[
    mask_gcs_lt_15 &
    mask_gcs_gt_0 &
    mask_type_neuro
]

# 2. Identifiziere Transporte mit BZ-Messung (value > 0)
gueltige_bz = bz_df[bz_df["value"] > 0]

# 3. Merge, um zu sehen, welche Bewusstseinsgeminderten einen BZ-Wert haben
# Annahme: Die DFs haben eine gemeinsame transport_id Spalte
merged_df = pd.merge(
    bewusstsein_gemindert, 
    gueltige_bz[["protocolId", "value"]], 
    on="protocolId", 
    how="left", 
    suffixes=("_gcs", "_bz")
)

# 4. Berechne Ergebnisse
# Gesamtzahl bewusstseinsgeminderte Patienten (Nenner)
anzahl_bewusstseinsgemindert = len(bewusstsein_gemindert["protocolId"].unique())

# Anzahl mit BZ-Messung (Zähler)
anzahl_mit_bz = merged_df.dropna(subset=["value"]).protocolId.nunique()

# Prozentsatz berechnen
prozent_gesamt = (anzahl_mit_bz / anzahl_bewusstseinsgemindert * 100) if anzahl_bewusstseinsgemindert > 0 else 0


# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Bei jedem bewusstseinsveränderten Patienten erfolgt eine Blutglukosebestimmung.**
            
## Rationale 
Die Blutzucker-Bestimmung kann das Vorliegen einer leicht behandelbaren Hypoglykämie als Ursache für Bewusstseinsveränderungen aufdecken und damit für die weitere Therapie wegweisend sein. Damit ist für die Leitlinienautoren die Messung der Blutglukose einer der wichtigsten Parameter im Rahmen der präklinischen Versorgung von bewusstseinsgeminderten Patienten.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit mindestens einem dokumentiertem Blutglukosewert bei Primäreinsätzen in der Notfallrettung bei Patienten mit Bewusstseinseinschränkung (GCS < 15) im Erstbefund unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit Bewusstseinseinschränkung im Erstbefund unter Ausschluss von Behandlungsverweigerung und Palliativsituationen.
                        
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Reanimationssituation (ja vs. nein)
* Altersgruppe (< 16 Jahre vs. ≥ 16 Jahre)
                       
""")

# Gesamtergebnis anzeigen
st.subheader("Gesamtergebnis")
st.metric(
    label="Anteil der bewusstseinsgeminderten Patienten mit BZ-Messung", 
    value=f"{prozent_gesamt:.1f}%",
    delta=f"{prozent_gesamt - 100:.1f}%" if prozent_gesamt < 100 else "Ziel erreicht"
)

# Visualisierung des Gesamtergebnisses
fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = prozent_gesamt,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "Erfüllungsgrad des Qualitätsziels"},
    gauge = {
        'axis': {'range': [0, 100]},
        'bar': {'color': "darkblue"},
        'steps': [
            {'range': [0, 50], 'color': "red"},
            {'range': [50, 80], 'color': "orange"},
            {'range': [80, 95], 'color': "yellow"},
            {'range': [95, 100], 'color': "green"}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 100
        }
    }
))
st.plotly_chart(fig)