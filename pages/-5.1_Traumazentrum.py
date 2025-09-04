import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from data_loader import data_loading

st.set_page_config(layout="wide", page_title="Polytrauma Analysis Dashboard")

# Title and description
st.title("Polytrauma Analysis Dashboard")

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Das Prähospitalintervall beträgt bei Patienten mit Tracerdiagnose Polytrauma maximal 60 Minuten.**

Der Patient wird zeitgerecht in einer geeigneten Behandlungseinrichtung weiterversorgt.

## Rationale
Bei polytraumatisierten Patienten hat die rasche zielgerichtete Diagnostik und Therapie in der Klinik einen relevanten Einfluss auf den Behandlungserfolg.

Das interdisziplinäre Eckpunktepapier zur Gesundheitsversorgung in Deutschland fordert ein Prähospitalintervall von **maximal 60 Minuten** für Schwerverletzte. In der aktuellen S3-Leitlinie Schwerverletztenversorgung ist ein quantitativ festgelegtes Ziel für das Prähospitalintervall jedoch nicht mehr zu finden. Auch bei Kindern soll die Zeitspanne bis zur Klinikaufnahme so kurz wie möglich gehalten werden.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Zähler:** Fälle welche primär in ein geeignetes Traumazentrum transportiert werden bei Primäreinsätzen in der Notfallrettung bei Patienten mit V.a. Polytrauma und Schockraum-Indikation, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen

**Nenner:** Primäreinsätze in der Notfallrettung bei Patienten mit V.a. Polytrauma und Schockraum-Indikation, die in eine Klinik transportiert werden unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Ergebnisdarstellung:** Anteil in Prozent
""")

# Load data with error handling
@st.cache_data
def load_data():
    try:
        hospital = pd.read_csv("/home/mbrucker/streamlit_app/data/krankenhausDigagnosen.csv", sep=";")
        details = data_loading("Index")
        return hospital, details
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

hospital, details = load_data()

if hospital is None or details is None:
    st.error("Could not load required data. Please check your data sources.")
    st.stop()


st.write("Folgende Krankenhäuser sind geeignete Traumazentren:")
st.write(hospital[hospital["Polytrauma"] == True])


polytrauma= details[details["leadingDiagnosis"] == "polytrauma"]

st.write(polytrauma[polytrauma["targetDestination"] == hospital[hospital["Polytrauma"] == True]["Name"].values[0]])