import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import ast
from data_loader import data_loading

st.write("Prüfung ob gcs < 9 für prüfung ")

# Title and description
st.title("5.1 Zielklinik geeignetes Traumazentrum")

st.write("hier vlt auch mit leadingDiagnosis filter um neben polytrauma auch andere Diagnosen zu betrachten")

# Load data
df_krankenhaus = pd.read_csv('/home/mbrucker/streamlit_app/data/krankenhausDigagnosen.csv', sep=';')
st.write(df_krankenhaus)

df_index = data_loading("Index")

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
    
    # Display results
    st.subheader("Hospital Eligibility Results")
    display_cols = ['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']
    st.dataframe(df_index[display_cols])
    
    return df_index

# Perform eligibility check
df_checked = check_hospital_eligibility(df_krankenhaus, df_index)

# Analyze polytrauma cases
st.header("Polytrauma Case Analysis")

# Filter for polytrauma cases (handle NaN values safely)
df_trauma = df_checked.copy()
df_trauma['leadingDiagnosis'] = df_trauma['leadingDiagnosis'].fillna('')
trauma_mask = df_trauma['leadingDiagnosis'].str.lower().str.contains('polytrauma|schwerverletzt')
trauma_cases = df_trauma[trauma_mask].copy()

# Display basic count
trauma_count = len(trauma_cases)
st.write(f"Total polytrauma cases: {trauma_count}")

if trauma_count > 0:
    # Calculate key metrics
    eligible_count = trauma_cases['hospital_eligible'].sum()
    percentage = (eligible_count / trauma_count * 100) if trauma_count > 0 else 0
    
    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Polytrauma Cases", f"{trauma_count}")
    col2.metric("Appropriate Trauma Center", f"{eligible_count}")
    col3.metric("Percentage", f"{percentage:.1f}%")
    
    # Display filtered cases
    st.subheader("Polytrauma Transport Details")
    st.dataframe(trauma_cases[['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']])
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ['Appropriate Trauma Center', 'Inappropriate Trauma Center']
    sizes = [eligible_count, trauma_count - eligible_count]
    colors = ['#4CAF50', '#F44336']
    explode = (0.1, 0) if eligible_count > 0 else (0, 0.1)
    
    ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
           shadow=True, startangle=90)
    ax.axis('equal')
    ax.set_title('Appropriateness of Trauma Center Selection')
    
    st.pyplot(fig)

   
# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Patienten mit V.a. eine Tracerdiagnose werden primär in eine geeignete Zielklinik transportiert.**

## Rationale
Die S3-Leitlinie Schwerverletztenversorgung sowie die Deutsche Gesellschaft für Unfallchirurgie empfiehlt die primäre Zuweisung von Schwerverletzten Patienten in ein geeignetes Traumazentrum innerhalb eines Traumanetzwerks. Lokale Traumazentren sind nur dann als Zielklinik vorgesehen,
wenn sie das nächstgelegene Traumazentrum bei penetrierenden thorakalen
oder abdominellen Verletzungen sind, oder ein höherwertiges Traumzentrum
nicht zeitgerecht erreicht werden kann. Im Vergleich zu früheren Versionen
der zitierten Dokumente fällt die Empfehlung zugunsten höherwertiger
Traumazentren weniger eindeutig aus.
Das Eckpunktepapier empfiehlt die primäre Aufnahme in ein regionales oder
überregionales Traumazentrum, wenn möglich.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Zähler:** Fälle welche primär in ein geeignetes Traumazentrum transportiert werden
bei Primäreinsätzen in der Notfallrettung bei Patienten mit V.a. Polytrauma
und Schockraum-Indikation, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Nenner:** Primäreinsätze in der Notfallrettung bei Patienten mit V.a. Polytrauma und Schockraum-Indikation, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen**
* Schweres Schädel-Hirn-Trauma (ja vs. nein)   
* Penetrierendes Thorax- oder Abdominaltrauma (ja vs. nein)         
""")

# Zusätzliche Auswertungen
st.header("Zusätzliche Auswertungen")

# Filter für Primäreinsätze
if 'statisticMissionType' in df_checked.columns:
    primary_missions = df_checked['statisticMissionType'].fillna('').str.contains('Primär')
    primary_count = primary_missions.sum()
    st.write(f"Anzahl Primäreinsätze: {primary_count}")

# Zusammenfassung und Empfehlungen
st.header("Zusammenfassung und Empfehlungen")

if trauma_count > 0:
    if percentage < 80:
        st.error(f"""
        **Verbesserungspotential identifiziert:** Nur {percentage:.1f}% der Polytrauma-Patienten werden in ein geeignetes Traumazentrum transportiert.
        
        **Empfehlungen:**
        1. Schulung des Rettungsdienstpersonals zur Identifikation von Polytrauma-Patienten
        2. Klare Richtlinien zur Auswahl des geeigneten Traumazentrums
        3. Regelmäßige Überprüfung der Transportziele bei Polytrauma-Patienten
        """)
    else:
        st.success(f"""
        **Gute Qualität:** {percentage:.1f}% der Polytrauma-Patienten werden in ein geeignetes Traumazentrum transportiert.
        
        **Empfehlungen zur weiteren Verbesserung:**
        1. Fortsetzung der bestehenden Praxis
        2. Regelmäßige Überprüfung der Transportziele
        """)

