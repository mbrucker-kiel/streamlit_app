import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import ast
from data_loading import data_loading
import plotly.graph_objects as go
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

# Title and description
st.title("5.3 Zielklinik Stroke-Unit")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

# Load data
df_krankenhaus = pd.read_csv('data/krankenhausDigagnosen.csv', sep=';')
st.write(df_krankenhaus)

df_index = data_loading("Index")

    
    
# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Patienten mit V.a. eine Tracerdiagnose werden primär in eine geeignete Zielklinik transportiert.**
""")

# Additional rationale specific to stroke care
st.markdown("""
## Rationale
Die S3-Leitlinie Schlaganfall empfiehlt die primäre Aufnahme von Patienten mit Verdacht auf akuten Schlaganfall in eine spezialisierte Behandlungseinrichtung (Stroke Unit). Hierbei gilt der Grundsatz "Time is Brain" - je schneller die Therapie eingeleitet wird, desto besser die Prognose.

Die Deutsche Schlaganfall-Gesellschaft und die Deutsche Gesellschaft für Neurologie empfehlen, dass Patienten mit Verdacht auf einen akuten Schlaganfall direkt in eine Klinik mit Stroke Unit transportiert werden sollen, um eine zeitgerechte Diagnostik und Therapie (insbesondere Thrombolyse oder mechanische Thrombektomie) zu ermöglichen.

Die systemische Thrombolyse ist innerhalb eines Zeitfensters von 4,5 Stunden nach Symptombeginn möglich, während die mechanische Thrombektomie bei geeigneten Patienten in einem noch erweiterten Zeitfenster durchgeführt werden kann. Daher ist die Transportentscheidung des Rettungsdienstes entscheidend für das Outcome des Patienten.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Zähler:** Patienten, welche primär einer geeigneten Stroke-Unit, einem Comprehensive
Stroke Center, einer Tele-Stroke-Unit oder einer Schlaganfalleinheit mit spezifischer Behandlungsmöglichkeit zugeführt werden bei Primäreinsätzen in der
Notfallrettung bei Patienten mit V.a. akuten Stroke / akutes zentrales neurologisches Defizit, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen

**Nenner:** Primäreinsätze in der Notfallrettung bei Patienten mit V.a. akuten Stroke / akutes zentrales neurologisches Defizit, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen

**Ergebnisdarstellung:** Anteil in Prozent
""")


def check_hospital_eligibility(df_krankenhaus, df_index):
    """
    Check and display hospital eligibility for patient transports
    """
    # Create a dictionary for faster lookups
    hospital_capabilities = {}
    
    # Process hospital data
    for _, row in df_krankenhaus.iterrows():
        hospital_names = ast.literal_eval(row['Name'])
        capabilities = {
            "TIA / Schlaganfall": row["TIA / Schlaganfall"],
            "ACS / STEMI /NSTEMI": row["ACS / STEMI /NSTEMI"],
            "Reanimation": row["Reanimation"],
            "Polytrauma": row["Polytrauma"]
        }
        
        # Add each name variant to the dictionary
        for name in hospital_names:
            hospital_capabilities[name.lower()] = capabilities
    
    # Diagnosis mapping
    diagnosis_map = {
        "schlaganfall": "TIA / Schlaganfall",
        "tia": "TIA / Schlaganfall",
        "stroke": "TIA / Schlaganfall",
        "apoplex": "TIA / Schlaganfall",
        "neurologisches defizit": "TIA / Schlaganfall",
        "halbseitenlähmung": "TIA / Schlaganfall",
        "hemiplegie": "TIA / Schlaganfall",
        "parese": "TIA / Schlaganfall",
        "sprachstörung": "TIA / Schlaganfall",
        "stemi": "ACS / STEMI /NSTEMI",
        "nstemi": "ACS / STEMI /NSTEMI",
        "acs": "ACS / STEMI /NSTEMI",
        "herzinfarkt": "ACS / STEMI /NSTEMI",
        "reanimation": "Reanimation",
        "Herz-Kreislauf-Stillstand": "Reanimation",
        "polytrauma": "Polytrauma",
        "schwerverletzt": "Polytrauma",
    }
    
    # Function to check individual transport
    def check_transport(target, diagnosis):
        if pd.isna(target) or pd.isna(diagnosis):
            return False
            
        target = target.strip().lower()
        diagnosis_lower = diagnosis.lower()
        
        # Find matching diagnosis category
        matched_category = None
        for key, category in diagnosis_map.items():
            if key in diagnosis_lower:
                matched_category = category
                break
                
        if not matched_category:
            return False
            
        # Check if any hospital name matches
        for hospital_name, capabilities in hospital_capabilities.items():
            if hospital_name in target or target in hospital_name:
                return capabilities.get(matched_category, False)
                
        return False
    
    # Add eligibility column
    df_index['hospital_eligible'] = df_index.apply(
        lambda row: check_transport(
            row.get('targetDestination', ''), 
            row.get('leadingDiagnosis', '')
        ), 
        axis=1
    )
        
    return df_index

# Perform eligibility check
df_checked = check_hospital_eligibility(df_krankenhaus, df_index)

# Analyze stroke cases
st.header("Analyse der Stroke/TIA-Fälle")

# Filter for stroke cases (handle NaN values safely)
df_stroke = df_checked.copy()
df_stroke['leadingDiagnosis'] = df_stroke['leadingDiagnosis'].fillna('')
stroke_mask = df_stroke['leadingDiagnosis'].str.lower().str.contains('schlaganfall|tia|stroke|apoplex|neurologisches defizit|halbseitenlähmung|hemiplegie|parese|sprachstörung')
stroke_cases = df_stroke[stroke_mask].copy()

stroke_count = len(stroke_cases)

if stroke_count > 0:
    # Calculate key metrics
    eligible_count = stroke_cases['hospital_eligible'].sum()
    percentage = (eligible_count / stroke_count * 100) if stroke_count > 0 else 0
    
    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Anzahl Stroke/TIA Fälle", f"{stroke_count}")
    col2.metric("Geeignetes Stroke Unit", f"{eligible_count}")
    col3.metric(
        label="Anteil",
        value=f"{percentage:.1f}%",
        delta=f"{percentage - 100:.1f}%" if percentage < 100 else "Ziel erreicht"
    )
    
    # Visualisierung des Gesamtergebnisses als Gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percentage,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Erfüllungsgrad des Qualitätsziels"},
        gauge={
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

            # Display filtered cases
    st.subheader("Stroke/TIA Transport Details")
    # Display cases where hospital_eligible is False at the top
    stroke_cases_sorted = stroke_cases.sort_values(by='hospital_eligible')
    st.dataframe(stroke_cases_sorted[['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']])