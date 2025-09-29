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

st.title("1.5 Anfahr-/ Anflugintervall ")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

# Qualitätsziel und Rationale mit Markdown
st.markdown(
    """
## Qualitätsziel
**Das Anfahr- / Anflugintervall des ersteintreffenden Rettungsmittels ist kurz**
            
## Rationale
Das Anfahr- / Anflugintervall des ersteintreffenden Rettungsmittels ist Teil des therapiefreien Intervalls und sollte kurz sein. Dabei spielt insbesondere die Vorhaltung und Lozierung der Rettungsmittel, aber auch das Dispositionsverhalten der Leitstelle eine Rolle.
"""
)

# Berechnungsgrundlage
st.markdown(
    """
## Berechnungsgrundlage
**Indikator:** Anfahr- bzw. Anflugintervall (FMS Status 3 bis Status 4) des ersten am Einsatzort eintreffenden, arztbesetzten Rettungsmittels oder Rettungstransportwagens (erster Status 4 für ein Notfallereignis)
            
**Grundgesamtheit:** Primäreinsätze in der Notfallrettung mit Alarmierung als Notfalleinsatz
**Ergebnisdarstellung:** Median, Quartile, 10. und 90. Perzentil in Minuten und Sekunden
            
**Stratifizierungen** 
* Alarmierung aus FMS-Status 2 vs. andere Status
* Nach Typ des ersteintreffenden Rettungsmittels (RTW vs. NEF vs. NAW vs. RTH/ITH vs. Sonstige)
                       
"""
)

st.subheader("Gefilterte Datenvorschau")
