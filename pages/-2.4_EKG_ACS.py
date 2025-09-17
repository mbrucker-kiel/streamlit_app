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

st.title("2.4 12-Kanal-EKG bei V.a. Akutes Koronarsyndrom (ACS)")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

ekg_df = data_loading("12-Kanal-EKG")
df_index = data_loading("Index")

# filter index to only contain primäreinsätze
# ["Pauschale RTW", "RTW - Transport", "Pauschale NEF"]
df_index = df_index[df_index['missionType'].isin(["Pauschale RTW", "RTW - Transport", "Pauschale NEF"])]

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Bei Patienten mit akutem Brustschmerz oder V.a. ACS soll ein 12-Kanal-EKG abgeleitet werden.**
            
## Rationale 
Die prähospitale Registrierung eines 12-Kanal-EKGs bei Patientinnen und Patienten mit Verdacht auf einen ST-Streckenhebungsinfarkt beschleunigt nicht nur die prä- bzw. intrahospitale Reperfusion, sondern vermindert auch die Sterblichkeit. Daher empfehlen die Leitlinien der European Society of Cardiology (ESC) und des European Resuscitation Council (ERC) die Ableitung eines 12-Kanal-EKGs innerhalb von 10 Minuten ab erstem Patientenkontakt.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit dokumentiertem 12-Kanal-EKG bei Primäreinsätzen in der Notfallrettung bei Patienten mit unklarem Thoraxschmerz / V.a. ACS unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                        
**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit unklarem Thoraxschmerz / V.a. ACS unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                                    
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Einsatzort (Krankenhaus oder Arztpraxis vs. sonstige)
                       
""")

# Filter für ACS-Fälle - prüfe, ob 'acs' oder ähnliche Begriffe in der Diagnose vorkommt (case-insensitive)
if 'leadingDiagnosis' not in df_index.columns:
    st.error("Spalte 'leadingDiagnosis' nicht gefunden!")
else:
    # Konvertiere alle Diagnosen zu Strings und führe einen Case-insensitive Vergleich durch
    df_index['leadingDiagnosis'] = df_index['leadingDiagnosis'].astype(str)
    mask_acs = (
        df_index['leadingDiagnosis'].str.lower().str.contains('acs', na=False) |
        df_index['leadingDiagnosis'].str.lower().str.contains('brustschmerz', na=False) |
        df_index['leadingDiagnosis'].str.lower().str.contains('thoraxschmerz', na=False) |
        df_index['leadingDiagnosis'].str.lower().str.contains('angina', na=False) |
        df_index['leadingDiagnosis'].str.lower().str.contains('herzinfarkt', na=False)
    )
    
    # ACS-Fälle filtern
    acs_faelle = df_index[mask_acs]
    
    # Anzahl der ACS-Fälle anzeigen
    anzahl_acs = len(acs_faelle)
    st.write(f"Anzahl der identifizierten ACS-Fälle: {anzahl_acs}")
    
    if anzahl_acs == 0:
        st.warning("Keine ACS-Fälle gefunden! Überprüfen Sie die Daten oder die Filterkriterien.")
    else:
        # Protokoll-IDs der ACS-Fälle
        acs_protokoll_ids = acs_faelle['protocolId'].unique()
        
        # Filtere EKG-Daten für ACS-Fälle und nur durchgeführte EKGs
        ekg_acs = ekg_df[
            (ekg_df['protocolId'].isin(acs_protokoll_ids)) & 
            (ekg_df['performed'] == True)
        ]
        
        # Anzahl der ACS-Fälle mit durchgeführtem EKG
        anzahl_mit_ekg = len(ekg_acs['protocolId'].unique())
        
        # Berechne Prozentsatz
        prozent_gesamt = (anzahl_mit_ekg / anzahl_acs * 100) if anzahl_acs > 0 else 0
        
        # Gesamtergebnis anzeigen
        st.subheader("Gesamtergebnis")
        st.metric(
            label="Anteil der ACS-Patienten mit 12-Kanal-EKG", 
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
        
        # Detailansicht der ACS-Fälle mit und ohne EKG
        st.subheader("Details zu ACS-Fällen")
        
        # Erstelle ein DataFrame mit Status der EKG-Durchführung für jeden ACS-Fall
        acs_mit_ekg_status = pd.DataFrame({
            'protocolId': acs_protokoll_ids,
            'EKG_durchgeführt': [pid in ekg_acs['protocolId'].unique() for pid in acs_protokoll_ids]
        })
        
        # Zusammenfassung als Balkendiagramm
        status_counts = acs_mit_ekg_status['EKG_durchgeführt'].value_counts().reset_index()
        status_counts.columns = ['EKG durchgeführt', 'Anzahl']
        status_counts['EKG durchgeführt'] = status_counts['EKG durchgeführt'].map({True: 'Ja', False: 'Nein'})
        
        fig_bar = px.bar(
            status_counts,
            x='EKG durchgeführt',
            y='Anzahl',
            color='EKG durchgeführt',
            color_discrete_map={'Ja': 'green', 'Nein': 'red'},
            text='Anzahl'
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(title_text='ACS-Fälle mit und ohne 12-Kanal-EKG')
        st.plotly_chart(fig_bar)
        
        # Detaillierte Datenansicht
        st.subheader("Detaillierte Datenübersicht")
        
        # Merge mit Original-Daten für mehr Informationen
        detail_view = pd.merge(
            acs_mit_ekg_status,
            acs_faelle[['protocolId', 'leadingDiagnosis']],
            on='protocolId',
            how='left'
        )
        
        # Anzeige der Details, sortiert nach EKG-Status
        detail_view_sorted = detail_view.sort_values(by=['EKG_durchgeführt'], ascending=True)
        st.dataframe(detail_view_sorted)
