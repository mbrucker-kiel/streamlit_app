import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import ast
from data_loading import data_loading

# Title and description
st.title("5.2 ST-Hebungsinfarkt und Zielklinik Herzkatheter-Zentrum")

import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Load configuration
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
stauth.Hasher.hash_passwords(config['credentials'])

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)
try:
    authenticator.login()
except Exception as e:
    st.error(e)

# Load data
df_krankenhaus = pd.read_csv('data/krankenhausDigagnosen.csv', sep=';')
st.write(df_krankenhaus)

df_index = data_loading("Index")

st.write(df_index)

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
    
    # Display results
    st.subheader("Hospital Eligibility Results")
    display_cols = ['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']
    st.dataframe(df_index[display_cols])
    
    return df_index

# Perform eligibility check
df_checked = check_hospital_eligibility(df_krankenhaus, df_index)

# Analyze cardiac cases
st.header("STEMI/NSTEMI/ACS Case Analysis")

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
st.write(f"Total STEMI/NSTEMI/ACS cases (excluding reanimation): {cardiac_count}")

if cardiac_count > 0:
    # Calculate key metrics
    eligible_count = cardiac_cases['hospital_eligible'].sum()
    percentage = (eligible_count / cardiac_count * 100) if cardiac_count > 0 else 0
    
    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cardiac Cases", f"{cardiac_count}")
    col2.metric("Appropriate Cardiac Center", f"{eligible_count}")
    col3.metric("Percentage", f"{percentage:.1f}%")
    
    # Display filtered cases
    st.subheader("Cardiac Transport Details")
    st.dataframe(cardiac_cases[['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']])
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ['Appropriate Cardiac Center', 'Inappropriate Cardiac Center']
    sizes = [eligible_count, cardiac_count - eligible_count]
    colors = ['#4CAF50', '#F44336']
    explode = (0.1, 0) if eligible_count > 0 else (0, 0.1)
    
    ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
           shadow=True, startangle=90)
    ax.axis('equal')
    ax.set_title('Appropriateness of Cardiac Center Selection')
    
    st.pyplot(fig)
    
    # STEMI vs NSTEMI/ACS Stratification
    st.subheader("Stratification by STEMI vs NSTEMI/ACS")
    
    # Detect STEMI in diagnosis
    cardiac_cases['STEMI'] = cardiac_cases['leadingDiagnosis'].str.lower().str.contains('stemi|st-hebung|sthebung')
    cardiac_cases['NSTEMI_ACS'] = cardiac_cases['leadingDiagnosis'].str.lower().str.contains('nstemi|acs|akutes koronarsyndrom') & ~cardiac_cases['STEMI']
    
    # Count by STEMI status
    stemi_cases = cardiac_cases[cardiac_cases['STEMI'] == True]
    nstemi_acs_cases = cardiac_cases[cardiac_cases['NSTEMI_ACS'] == True]
    other_cardiac = cardiac_cases[~(cardiac_cases['STEMI'] | cardiac_cases['NSTEMI_ACS'])]
    
    stemi_count = len(stemi_cases)
    nstemi_acs_count = len(nstemi_acs_cases)
    other_count = len(other_cardiac)
    
    stemi_eligible = stemi_cases['hospital_eligible'].sum() if stemi_count > 0 else 0
    nstemi_acs_eligible = nstemi_acs_cases['hospital_eligible'].sum() if nstemi_acs_count > 0 else 0
    other_eligible = other_cardiac['hospital_eligible'].sum() if other_count > 0 else 0
    
    stemi_percentage = (stemi_eligible / stemi_count * 100) if stemi_count > 0 else 0
    nstemi_acs_percentage = (nstemi_acs_eligible / nstemi_acs_count * 100) if nstemi_acs_count > 0 else 0
    other_percentage = (other_eligible / other_count * 100) if other_count > 0 else 0
    
    # Display stratification
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**STEMI:**")
        st.write(f"- Anzahl: {stemi_count}")
        st.write(f"- Geeignetes Herzkatheter-Zentrum: {stemi_eligible} ({stemi_percentage:.1f}%)")
    
    with col2:
        st.write("**NSTEMI/ACS:**")
        st.write(f"- Anzahl: {nstemi_acs_count}")
        st.write(f"- Geeignetes Herzkatheter-Zentrum: {nstemi_acs_eligible} ({nstemi_acs_percentage:.1f}%)")
        
    with col3:
        st.write("**Other Cardiac:**")
        st.write(f"- Anzahl: {other_count}")
        st.write(f"- Geeignetes Herzkatheter-Zentrum: {other_eligible} ({other_percentage:.1f}%)")
    
    # ECG Analysis if data available
    if 'ecgCount' in cardiac_cases.columns:
        st.subheader("ECG Analysis")
        
        # Count cases with ECG performed
        ecg_performed = cardiac_cases['ecgCount'] > 0
        ecg_count = ecg_performed.sum()
        ecg_percentage = (ecg_count / cardiac_count * 100) if cardiac_count > 0 else 0
        
        st.write(f"ECG performed in {ecg_count} of {cardiac_count} cases ({ecg_percentage:.1f}%)")
        
        # Compare eligibility with ECG performed
        ecg_eligible = cardiac_cases[ecg_performed]['hospital_eligible'].sum()
        ecg_eligible_percentage = (ecg_eligible / ecg_count * 100) if ecg_count > 0 else 0
        
        no_ecg_eligible = cardiac_cases[~ecg_performed]['hospital_eligible'].sum()
        no_ecg_count = cardiac_count - ecg_count
        no_ecg_eligible_percentage = (no_ecg_eligible / no_ecg_count * 100) if no_ecg_count > 0 else 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**With ECG:**")
            st.write(f"- Anzahl: {ecg_count}")
            st.write(f"- Geeignetes Herzkatheter-Zentrum: {ecg_eligible} ({ecg_eligible_percentage:.1f}%)")
        
        with col2:
            st.write("**Without ECG:**")
            st.write(f"- Anzahl: {no_ecg_count}")
            st.write(f"- Geeignetes Herzkatheter-Zentrum: {no_ecg_eligible} ({no_ecg_eligible_percentage:.1f}%)")
        
        # Create visualization for ECG impact
        fig, ax = plt.subplots(figsize=(10, 6))
        categories = ['With ECG', 'Without ECG']
        appropriate = [ecg_eligible_percentage, no_ecg_eligible_percentage]
        
        ax.bar(categories, appropriate, color=['#4CAF50', '#2196F3'])
        ax.set_title('Impact of ECG on Appropriate Cardiac Center Selection')
        ax.set_ylabel('Percentage of Appropriate Transfers')
        ax.set_ylim(0, 100)
        
        for i, v in enumerate(appropriate):
            ax.text(i, v + 3, f"{v:.1f}%", ha='center')
        
        st.pyplot(fig)
else:
    st.info("Keine STEMI/NSTEMI/ACS-Fälle in den Daten gefunden.")

# Display value counts as requested
st.subheader("Verteilung der STEMI/NSTEMI/ACS-Fälle")
try:
    cardiac_diagnoses = ['stemi', 'nstemi', 'acs', 'herzinfarkt', 'st-hebung', 'sthebung', 'akutes koronarsyndrom']
    pattern = '|'.join(cardiac_diagnoses)
    cardiac_counts = df_checked[df_checked["leadingDiagnosis"].str.lower().str.contains(pattern)].value_counts()
    st.write(cardiac_counts)
except:
    st.write("Keine STEMI/NSTEMI/ACS-Fälle vorhanden oder Fehler in der Datenstruktur.")

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

