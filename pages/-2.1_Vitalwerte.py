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

st.title("2.1 Erhebung und Überwachung der Vitalwerte")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication
df_index = data_loading("Index")
gcs_df = data_loading("GCS")
bd_df = data_loading("bd")
hf_df = data_loading("hf")
spo2_df = data_loading("spo2")
af_df = data_loading("af")
# auch noch geburtsdatum des patienten laden

st.write("was sind genau die Tracer-Diagnosen? Eckpunktepapier?")
st.write("aktuell keine altersprüfung und keine prüfung nach inversiven maßnahmen")

df_index_filtered = df_index[
    (df_index["missionType"] == "RTW-Transport")
    | (df_index["missionType"] == "Pauschale RTW")
]

st.write("AKTUELL BASIEREND WENN MISSION TYPE = RTW-TRANSPORT oder PAUSCHALE RTW")


# Qualitätsziel und Rationale mit Markdown
st.markdown(
    """
## Qualitätsziel
**Erhebung und Überwachung der relevanten Vitalparameter bei schwer erkrankten / schwer verletzten Notfallpatienten.**
            
## Rationale
Die Erhebung und Überwachung der Vitalparameter ist die Voraussetzung für eine adäquate Situationseinschätzung sowie für die Erkennung von klinischen Zustandsänderungen und Komplikationen. Ein Basismonitoring bestehend aus **EKG, nicht-invasiver Blutdruckmessung und Pulsoxymetrie** ist anerkannter notfallmedizinischer Standard. Leitlinien für typische notfallmedizinische Krankheitsbilder empfehlen explizit das Basismonitoring oder gründen Therapieentscheidungen auf den Vitalparametern. Ferner fordern die Fachinformationen zu vielen, insbesondere herzkreislaufwirksamen, potent analgetischen und sedierenden Notfallmedikamenten bei deren Anwendung eine Überwachung der Vitalparameter. Gleichzeitig werden Defizite bei der Dokumentation berichtet.
"""
)

# for each in df_index wo RTW-Transport
# -> if in transport:
# transport über protocollId versuchen mit gcs_df, bd_df hf_df spo2_df, af_df etwas zu matchen, wenn eintrag gut
#


# Berechnungsgrundlage
st.markdown(
    """
## Berechnungsgrundlage
            
**Zähler**
Fälle mit mindestens zweimaliger dokumentierter Messung von GCS, Blutdruck, Herzfrequenz oder Puls, SpO2 und Atemfrequenz bei Primäreinsätzen des Rettungsdienstes bei Patienten ab 5 Jahren mit dokumentierter Tracerdiagnose oder invasiver Maßnahme oder Medikamentengabe unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Nenner**
Primäreinsätze des Rettungsdienstes bei Patienten ab 5 Jahren mit dokumentierter Tracerdiagnose oder invasiver Maßnahme oder Medikamentengabe unter Ausschluss von Behandlungsverweigerung und Palliativsituationen     

            
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Einsätze mit vs. ohne physischer Notarzt-Beteiligung
                       
"""
)

st.subheader("Gefilterte Datenvorschau")

# ...existing code...

# Datenvorverarbeitung für Vitalwerte-Überwachung
st.subheader("Auswertung der Vitalwerte-Überwachung")

# Sammle alle relevanten Protokoll-IDs aus dem Index
protokoll_ids = df_index_filtered["protocolId"].unique()
st.write(f"Gesamtzahl der Protokolle: {len(protokoll_ids)}")


# 1. Für jedes Vitalzeichen zählen, wie viele Messungen pro Protokoll existieren
def count_measurements_per_protocol(df, name):
    counts = df.groupby("protocolId").size().reset_index(name=f"{name}_count")
    return counts


gcs_counts = count_measurements_per_protocol(gcs_df, "gcs")
bd_counts = count_measurements_per_protocol(bd_df, "bd")
hf_counts = count_measurements_per_protocol(hf_df, "hf")
spo2_counts = count_measurements_per_protocol(spo2_df, "spo2")
af_counts = count_measurements_per_protocol(af_df, "af")

# 2. Merge alle Zählungen
all_counts = pd.DataFrame({"protocolId": protokoll_ids})
all_counts = pd.merge(all_counts, gcs_counts, on="protocolId", how="left")
all_counts = pd.merge(all_counts, bd_counts, on="protocolId", how="left")
all_counts = pd.merge(all_counts, hf_counts, on="protocolId", how="left")
all_counts = pd.merge(all_counts, spo2_counts, on="protocolId", how="left")
all_counts = pd.merge(all_counts, af_counts, on="protocolId", how="left")

# Fehlende Werte durch 0 ersetzen
all_counts = all_counts.fillna(0)

# 3. Kriterien für die Erfüllung der Vitalwerte-Überwachung: mindestens 2 Messungen pro Vitalzeichen
all_counts["gcs_erfuellt"] = all_counts["gcs_count"] >= 2
all_counts["bd_erfuellt"] = all_counts["bd_count"] >= 2
all_counts["hf_erfuellt"] = all_counts["hf_count"] >= 2
all_counts["spo2_erfuellt"] = all_counts["spo2_count"] >= 2
all_counts["af_erfuellt"] = all_counts["af_count"] >= 2

# 4. Gesamtkriterium: alle Vitalzeichen müssen erfüllt sein
all_counts["alle_vitalzeichen_erfuellt"] = (
    all_counts["gcs_erfuellt"]
    & all_counts["bd_erfuellt"]
    & all_counts["hf_erfuellt"]
    & all_counts["spo2_erfuellt"]
    & all_counts["af_erfuellt"]
)

# 5. Berechne Prozentsätze für jedes Vitalzeichen und das Gesamtkriterium
anzahl_protokolle = len(all_counts)
ergebnisse = {
    "GCS": all_counts["gcs_erfuellt"].mean() * 100,
    "Blutdruck": all_counts["bd_erfuellt"].mean() * 100,
    "Herzfrequenz": all_counts["hf_erfuellt"].mean() * 100,
    "SpO2": all_counts["spo2_erfuellt"].mean() * 100,
    "Atemfrequenz": all_counts["af_erfuellt"].mean() * 100,
    "Alle Vitalzeichen": all_counts["alle_vitalzeichen_erfuellt"].mean() * 100,
}

# Gesamtergebnis anzeigen
st.subheader("Gesamtergebnis")
gesamtergebnis = ergebnisse["Alle Vitalzeichen"]
st.metric(
    label="Anteil der Protokolle mit vollständiger Vitalzeichenüberwachung",
    value=f"{gesamtergebnis:.1f}%",
    delta=f"{gesamtergebnis - 100:.1f}%" if gesamtergebnis < 100 else "Ziel erreicht",
)

# Visualisierung des Gesamtergebnisses
fig = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=gesamtergebnis,
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

# Detailergebnisse für die einzelnen Vitalzeichen
st.subheader("Erfüllung nach einzelnen Vitalzeichen")
vitalzeichen_df = pd.DataFrame(
    {
        "Vitalzeichen": list(ergebnisse.keys()),
        "Erfüllungsgrad (%)": list(ergebnisse.values()),
    }
)

fig_bar = px.bar(
    vitalzeichen_df,
    x="Vitalzeichen",
    y="Erfüllungsgrad (%)",
    color="Erfüllungsgrad (%)",
    color_continuous_scale=["red", "orange", "yellow", "green"],
    range_color=[0, 100],
    text="Erfüllungsgrad (%)",
)

fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig_bar.update_layout(title_text="Erfüllungsgrad nach Vitalzeichen")
st.plotly_chart(fig_bar)

# Detailierte Datenansicht
st.subheader("Detailierte Datenübersicht")
st.write("Anzahl der Messungen pro Protokoll:")
all_counts_sorted = all_counts.sort_values(
    by="alle_vitalzeichen_erfuellt", ascending=True
)
st.dataframe(all_counts_sorted)

# Optional: Detailansicht mit Stratifizierung nach Notarzt-Beteiligung
# (Dies würde zusätzliche Informationen aus df_index erfordern)
# st.subheader("Stratifizierung nach Notarzt-Beteiligung")
# if "notarzt_beteiligung" in df_index.columns:
#     # Implementieren Sie hier die Stratifizierung
