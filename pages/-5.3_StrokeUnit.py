import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import ast
from data_loader import data_loading

st.set_page_config(layout="wide", page_title="Stroke Analysis Dashboard")

# Title and description
st.title("5.3 Zielklinik Stroke-Unit")

# Load data
df_krankenhaus = pd.read_csv('/home/mbrucker/streamlit_app/data/krankenhausDigagnosen.csv', sep=';')
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
    
    # Display results
    st.subheader("Hospital Eligibility Results")
    display_cols = ['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']
    st.dataframe(df_index[display_cols])
    
    return df_index

# Perform eligibility check
df_checked = check_hospital_eligibility(df_krankenhaus, df_index)

# Analyze stroke cases
st.header("Stroke/TIA Case Analysis")

# Filter for stroke cases (handle NaN values safely)
df_stroke = df_checked.copy()
df_stroke['leadingDiagnosis'] = df_stroke['leadingDiagnosis'].fillna('')
stroke_mask = df_stroke['leadingDiagnosis'].str.lower().str.contains('schlaganfall|tia|stroke|apoplex|neurologisches defizit|halbseitenlähmung|hemiplegie|parese|sprachstörung')
stroke_cases = df_stroke[stroke_mask].copy()

# Display basic count
stroke_count = len(stroke_cases)
st.write(f"Total Stroke/TIA cases: {stroke_count}")

if stroke_count > 0:
    # Calculate key metrics
    eligible_count = stroke_cases['hospital_eligible'].sum()
    percentage = (eligible_count / stroke_count * 100) if stroke_count > 0 else 0
    
    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Stroke/TIA Cases", f"{stroke_count}")
    col2.metric("Appropriate Stroke Unit", f"{eligible_count}")
    col3.metric("Percentage", f"{percentage:.1f}%")
    
    # Display filtered cases
    st.subheader("Stroke/TIA Transport Details")
    st.dataframe(stroke_cases[['protocolId', 'targetDestination', 'leadingDiagnosis', 'hospital_eligible']])
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ['Appropriate Stroke Unit', 'Inappropriate Facility']
    sizes = [eligible_count, stroke_count - eligible_count]
    colors = ['#4CAF50', '#F44336']
    explode = (0.1, 0) if eligible_count > 0 else (0, 0.1)
    
    ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
           shadow=True, startangle=90)
    ax.axis('equal')
    ax.set_title('Appropriateness of Stroke Center Selection')
    
    st.pyplot(fig)
    
    # TIA vs Stroke Stratification
    st.subheader("Stratification by TIA vs Acute Stroke")
    
    # Detect TIA vs Stroke in diagnosis
    stroke_cases['TIA'] = stroke_cases['leadingDiagnosis'].str.lower().str.contains('tia|transitorisch')
    stroke_cases['Acute_Stroke'] = stroke_cases['leadingDiagnosis'].str.lower().str.contains('schlaganfall|stroke|apoplex') & ~stroke_cases['TIA']
    stroke_cases['Other_Neuro'] = ~(stroke_cases['TIA'] | stroke_cases['Acute_Stroke'])
    
    # Count by stroke type
    tia_cases = stroke_cases[stroke_cases['TIA'] == True]
    acute_stroke_cases = stroke_cases[stroke_cases['Acute_Stroke'] == True]
    other_neuro_cases = stroke_cases[stroke_cases['Other_Neuro'] == True]
    
    tia_count = len(tia_cases)
    acute_stroke_count = len(acute_stroke_cases)
    other_neuro_count = len(other_neuro_cases)
    
    tia_eligible = tia_cases['hospital_eligible'].sum() if tia_count > 0 else 0
    acute_stroke_eligible = acute_stroke_cases['hospital_eligible'].sum() if acute_stroke_count > 0 else 0
    other_neuro_eligible = other_neuro_cases['hospital_eligible'].sum() if other_neuro_count > 0 else 0
    
    tia_percentage = (tia_eligible / tia_count * 100) if tia_count > 0 else 0
    acute_stroke_percentage = (acute_stroke_eligible / acute_stroke_count * 100) if acute_stroke_count > 0 else 0
    other_neuro_percentage = (other_neuro_eligible / other_neuro_count * 100) if other_neuro_count > 0 else 0
    
    # Display stratification
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**TIA:**")
        st.write(f"- Anzahl: {tia_count}")
        st.write(f"- Geeignete Stroke-Unit: {tia_eligible} ({tia_percentage:.1f}%)")
    
    with col2:
        st.write("**Akuter Schlaganfall:**")
        st.write(f"- Anzahl: {acute_stroke_count}")
        st.write(f"- Geeignete Stroke-Unit: {acute_stroke_eligible} ({acute_stroke_percentage:.1f}%)")
        
    with col3:
        st.write("**Andere neurologische Defizite:**")
        st.write(f"- Anzahl: {other_neuro_count}")
        st.write(f"- Geeignete Stroke-Unit: {other_neuro_eligible} ({other_neuro_percentage:.1f}%)")
    
    # Time window analysis for thrombolysis eligibility
    st.subheader("Zeitfenster-Analyse für Thrombolyse-Eignung")
    
    # Check if we have mission date and times
    if 'missionDate' in stroke_cases.columns and 'Status4' in stroke_cases.columns:
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(stroke_cases['missionDate']):
            stroke_cases['missionDate'] = pd.to_datetime(stroke_cases['missionDate'])
        
        if not pd.api.types.is_datetime64_any_dtype(stroke_cases['Status4']):
            stroke_cases['Status4'] = pd.to_datetime(stroke_cases['Status4'])
        
        # Calculate symptom onset time (estimated from mission time)
        # Assuming mission alarm is within 30 minutes of symptom onset on average
        stroke_cases['estimated_onset'] = stroke_cases['missionDate'] - pd.Timedelta(minutes=30)
        
        # Calculate time from estimated onset to arrival at patient (Status 4)
        stroke_cases['time_to_patient'] = (stroke_cases['Status4'] - stroke_cases['estimated_onset']).dt.total_seconds() / 60
        
        # Categorize by time window
        stroke_cases['time_window'] = pd.cut(
            stroke_cases['time_to_patient'], 
            bins=[0, 90, 180, 270, float('inf')],
            labels=['< 90 min', '90-180 min', '180-270 min', '> 270 min']
        )
        
        # Count by time window
        time_window_counts = stroke_cases['time_window'].value_counts().sort_index()
        
        # Display time window distribution
        st.write("Verteilung nach geschätztem Zeitfenster seit Symptombeginn:")
        st.write(time_window_counts)
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        time_window_counts.plot(kind='bar', ax=ax, color='skyblue')
        ax.set_title('Verteilung nach Zeitfenster seit Symptombeginn')
        ax.set_ylabel('Anzahl der Fälle')
        ax.set_xlabel('Zeitfenster')
        
        # Add percentage labels
        total = time_window_counts.sum()
        for i, count in enumerate(time_window_counts):
            percentage = count / total * 100
            ax.text(i, count + 0.5, f"{percentage:.1f}%", ha='center')
        
        st.pyplot(fig)
        
        # Analyze eligibility by time window
        st.write("Eignung der Zielklinik nach Zeitfenster:")
        eligibility_by_window = stroke_cases.groupby('time_window')['hospital_eligible'].mean() * 100
        st.write(eligibility_by_window)
        
        # Create bar chart for eligibility by time window
        fig, ax = plt.subplots(figsize=(10, 6))
        eligibility_by_window.plot(kind='bar', ax=ax, color='lightgreen')
        ax.set_title('Eignung der Zielklinik nach Zeitfenster')
        ax.set_ylabel('Prozent geeignete Zielkliniken')
        ax.set_xlabel('Zeitfenster')
        ax.set_ylim(0, 100)
        
        # Add percentage labels
        for i, percentage in enumerate(eligibility_by_window):
            ax.text(i, percentage + 2, f"{percentage:.1f}%", ha='center')
        
        st.pyplot(fig)
else:
    st.info("Keine Schlaganfall/TIA-Fälle in den Daten gefunden.")

# Display value counts as requested
st.subheader("Verteilung der Schlaganfall/TIA-Fälle")
try:
    stroke_terms = ['schlaganfall', 'tia', 'stroke', 'apoplex', 'neurologisches defizit', 
                   'halbseitenlähmung', 'hemiplegie', 'parese', 'sprachstörung']
    pattern = '|'.join(stroke_terms)
    stroke_counts = df_checked[df_checked["leadingDiagnosis"].str.lower().str.contains(pattern)].value_counts()
    st.write(stroke_counts)
except:
    st.write("Keine Schlaganfall/TIA-Fälle vorhanden oder Fehler in der Datenstruktur.")

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

