import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import ast
from data_loading import data_loading
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

# Title and description
st.title("5.4  Zielklinik Z.n. Reanimation")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

df_krankenhaus = pd.read_csv("data/krankenhausDigagnosen.csv", sep=";")
st.write(df_krankenhaus)
df_reanimation = data_loading("Reanimation_mit_targetDestination")
st.write(df_reanimation)

# Qualitätsziel und Rationale mit Markdown
st.markdown(
    """
## Qualitätsziel
**Patienten mit V.a. eine Tracerdiagnose werden primär in eine geeignete Zielklinik transportiert.**

"""
)

# Berechnungsgrundlage
st.markdown(
    """
## Berechnungsgrundlage
**Zähler:** Fälle mit Aufnahme in ein zertifiziertes Cardiac Arrest Zentrum (oder gleichwertig geeignetes Krankenhaus) bei Primäreinsätzen in der Notfallrettung mit
präklinischer Reanimation erwachsener, nicht-traumatologischer Patienten und wiedererlangtem Spontankreislauf (ROSC) bei Klinikaufnahme
            
**Nenner:** Primäreinsätze in der Notfallrettung mit präklinischer Reanimation erwachsener, nicht-traumatologischer Patienten und wiedererlangtem Spontankreislauf (ROSC) bei Klinikaufnahme
            
**Ergebnisdarstellung:** Anteil in Prozent
"""
)


def check_hospital_eligibility(df_krankenhaus, df_reanimation):
    """
    Check and display hospital eligibility for reanimation patient transports
    """
    # Create a dictionary for faster lookups
    hospital_capabilities = {}

    # Process hospital data
    for _, row in df_krankenhaus.iterrows():
        hospital_names = ast.literal_eval(row["Name"])
        capabilities = {"Reanimation": row["Reanimation"]}

        # Add each name variant to the dictionary
        for name in hospital_names:
            hospital_capabilities[name.lower()] = capabilities

    # Function to check individual transport
    def check_transport(target, rea_status):
        if pd.isna(target) or not rea_status:
            return False

        target = target.strip().lower()

        # Check if any hospital name matches
        for hospital_name, capabilities in hospital_capabilities.items():
            if hospital_name in target or target in hospital_name:
                return capabilities.get("Reanimation", False)

        return False

    # Add eligibility column
    df_reanimation["hospital_eligible"] = df_reanimation.apply(
        lambda row: check_transport(
            row.get("targetDestination", ""), row.get("rea_status", False)
        ),
        axis=1,
    )

    return df_reanimation


# Perform eligibility check
df_checked = check_hospital_eligibility(df_krankenhaus, df_reanimation)

# Analyze reanimation cases
st.header("Analyse der Reanimationsfälle")

# Filter for reanimation cases with ROSC
rea_cases = df_checked[df_checked["rea_status"] == True].copy()

# Display basic count
rea_count = len(rea_cases)
st.write(f"Anzahl Reanimationsfälle mit ROSC: {rea_count}")

if rea_count > 0:
    # Calculate key metrics
    eligible_count = rea_cases["hospital_eligible"].sum()
    percentage = (eligible_count / rea_count * 100) if rea_count > 0 else 0

    # Create metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Reanimationsfälle mit ROSC", f"{rea_count}")
    col2.metric("Geeignetes Cardiac Arrest Zentrum", f"{eligible_count}")
    col3.metric(
        label="Anteil",
        value=f"{percentage:.1f}%",
        delta=f"{percentage - 100:.1f}%" if percentage < 100 else "Ziel erreicht",
    )

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

    # Display the data
    rea_cases_sorted = rea_cases.sort_values(by="hospital_eligible")
    rea_cases_display = rea_cases_sorted[
        ["protocolId", "targetDestination", "hospital_eligible"]
    ]
    st.dataframe(rea_cases_display)
else:
    st.warning("Keine Reanimationsfälle mit ROSC in den Daten vorhanden.")
