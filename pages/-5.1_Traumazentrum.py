import pandas as pd
import streamlit as st
import ast
from data_loading import data_loading
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

# Title and description
st.title("5.1 Zielklinik geeignetes Traumazentrum")


# Load data
df_krankenhaus = pd.read_csv("data/krankenhausDigagnosen.csv", sep=";")
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
        hospital_names = ast.literal_eval(row["Name"])
        capabilities = {
            "TIA / Schlaganfall": row["TIA / Schlaganfall"],
            "ACS / STEMI /NSTEMI": row["ACS / STEMI /NSTEMI"],
            "Reanimation": row["Reanimation"],
            "Polytrauma": row["Polytrauma"],
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
    df_index["hospital_eligible"] = df_index.apply(
        lambda row: check_transport(
            row.get("targetDestination", ""), row.get("leadingDiagnosis", "")
        ),
        axis=1,
    )

    return df_index


# Perform eligibility check
df_checked = check_hospital_eligibility(df_krankenhaus, df_index)

# Qualitätsziel und Rationale mit Markdown
st.markdown(
    """
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
"""
)

# Berechnungsgrundlage
st.markdown(
    """
## Berechnungsgrundlage
**Zähler:** Fälle welche primär in ein geeignetes Traumazentrum transportiert werden
bei Primäreinsätzen in der Notfallrettung bei Patienten mit V.a. Polytrauma
und Schockraum-Indikation, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Nenner:** Primäreinsätze in der Notfallrettung bei Patienten mit V.a. Polytrauma und Schockraum-Indikation, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen**
* Schweres Schädel-Hirn-Trauma (ja vs. nein)   
* Penetrierendes Thorax- oder Abdominaltrauma (ja vs. nein)         
"""
)

# Analyze polytrauma cases
st.header("Analyse der Polytrauma-Fälle")

# Filter for polytrauma cases (handle NaN values safely)
df_trauma = df_checked.copy()
df_trauma["leadingDiagnosis"] = df_trauma["leadingDiagnosis"].fillna("")
trauma_mask = (
    df_trauma["leadingDiagnosis"].str.lower().str.contains("polytrauma|schwerverletzt")
)
trauma_cases = df_trauma[trauma_mask].copy()


import plotly.graph_objects as go  # Add this import at the top if not present

trauma_count = len(trauma_cases)
if trauma_count > 0:
    # Calculate key metrics
    eligible_count = trauma_cases["hospital_eligible"].sum()
    percentage = (eligible_count / trauma_count * 100) if trauma_count > 0 else 0

    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Anzahl Polytrauma-Fälle", f"{trauma_count}")
    col2.metric("Geeignetes Traumazentrum", f"{eligible_count}")
    col3.metric(
        label="Anteil der Polytrauma-Patienten mit geeignetem Traumazentrum",
        value=f"{percentage:.1f}%",
        delta=f"{percentage - 100:.1f}%" if percentage < 100 else "Ziel erreicht",
    )

    # Calculate key metrics
    eligible_count = trauma_cases["hospital_eligible"].sum()
    percentage = (eligible_count / trauma_count * 100) if trauma_count > 0 else 0

    # Visualisierung des Gesamtergebnisses als Gauge
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=percentage,
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

    # Display filtered cases
    st.subheader("Polytrauma Transport Details")
    trauma_cases_sorted = trauma_cases.sort_values(by="hospital_eligible")
    st.dataframe(
        trauma_cases_sorted[
            ["protocolId", "targetDestination", "leadingDiagnosis", "hospital_eligible"]
        ]
    )

st.write(
    "Todos: Stratifizierung: Prüfung ob gcs < 9 für prüfung & Penetrierendes Thorax- oder Abdominaltrauma"
)
st.write(
    "hier vlt auch mit leadingDiagnosis filter um neben polytrauma auch andere Diagnosen zu betrachten"
)
