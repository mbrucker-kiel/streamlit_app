import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import ast
from data_loading import data_loading
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

# Title and description
st.title("5.2 ST-Hebungsinfarkt und Zielklinik Herzkatheter-Zentrum")

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

# Additional rationale specific to cardiac care
st.markdown("""
## Rationale
Die S3-Leitlinie Infarkt-bedingte kardiogene Schock empfiehlt die primäre Aufnahme von Patienten mit kardiogenem Schock auf der Basis eines ST-Hebungsinfarkts in Krankenhäuser mit rund-um-die-Uhr unmittelbar einsatzbereitem Herzkatheterlabor.

Gleichermaßen empfiehlt die Nationale Versorgungsleitlinie Chronische KHK für den ST-Hebungsinfarkt die unverzügliche Reperfusionstherapie mit einer Bevorzugung der primären PCI gegenüber der Lysetherapie, wenn die zeitlichen Vorgaben eingehalten werden können.

Der Rettungsdienst ist daher angehalten, Patienten mit Verdacht auf einen ST-Hebungsinfarkt direkt und umgehend in ein geeignetes Herzkatheter-Zentrum zu transportieren, um die Door-to-Balloon-Zeit zu minimieren und die Prognose zu verbessern.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Zähler:** Fälle welche primär in ein rund-um-die-Uhr unmittelbar einsatzbereites Herzkatheter-Zentrum transportiert werden bei Primäreinsätzen in der Notfallrettung bei Patienten mit vermutetem ST-Hebungsinfarkt ohne reanimiert worden zu sein, die in ein Krankenhaus transportiert werden unter Ausschluss von
Behandlungsverweigerung und Palliativsituationen


**Nenner:** Primäreinsätze in der Notfallrettung bei Patienten mit vermutetem ST-Hebungsinfarkt ohne reanimiert worden zu sein, die in ein Krankenhaus transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
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
        "stemi": "ACS / STEMI /NSTEMI",
        "nstemi": "ACS / STEMI /NSTEMI",
        "acs": "ACS / STEMI /NSTEMI",
        "herzinfarkt": "ACS / STEMI /NSTEMI",
        "st-hebung": "ACS / STEMI /NSTEMI",
        "sthebung": "ACS / STEMI /NSTEMI",
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

# Analyze cardiac cases
st.header("Analyse der STEMI/NSTEMI/ACS Fälle")

# Filter for cardiac cases (handle NaN values safely)
df_cardiac = df_checked.copy()
df_cardiac['leadingDiagnosis'] = df_cardiac['leadingDiagnosis'].fillna('')
cardiac_mask = df_cardiac['leadingDiagnosis'].str.lower().str.contains('stemi|nstemi|acs|herzinfarkt|st-hebung|sthebung|akutes koronarsyndrom')
cardiac_cases = df_cardiac[cardiac_mask].copy()

# Exclude reanimation cases as per the quality goal
if 'leadingDiagnosis' in cardiac_cases.columns:
    reanimation_mask = cardiac_cases['leadingDiagnosis'].str.lower().str.contains('reanimation|herz-kreislauf-stillstand|wiederbelebung')
    cardiac_cases = cardiac_cases[~reanimation_mask]

# Display basic count
cardiac_count = len(cardiac_cases)
st.write(f"Anzahl STEMI/NSTEMI/ACS Fälle: {cardiac_count}")

if cardiac_count > 0:
    # Calculate key metrics
    eligible_count = cardiac_cases['hospital_eligible'].sum()
    percentage = (eligible_count / cardiac_count * 100) if cardiac_count > 0 else 0
    
    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cardiac Cases", f"{cardiac_count}")
    col2.metric("Geeignetes Herzkatheter-Zentrum", f"{eligible_count}")
    col3.metric(
        label="Anteil",
        value=f"{percentage:.1f}%",
        delta=f"{percentage - 100:.1f}%" if percentage < 100 else "Ziel erreicht"
    )

    import plotly.graph_objects as go  # Add at the top if not present

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

    cardiac_cases_sorted = cardiac_cases.sort_values(by='hospital_eligible')
    cardiac_cases_display = cardiac_cases_sorted[['protocolId', 'leadingDiagnosis', 'targetDestination', 'hospital_eligible']]
    st.dataframe(cardiac_cases_display)