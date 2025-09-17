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

st.title("1.4 Ausrückeintervall")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Das Ausrückintervall ist kurz**
            
## Rationale
Das Ausrückintervall ist Teil des therapiefreien Intervalls und soll möglichst kurz sein. Dabei spielen sowohl baulich-technische Gegebenheiten als auch Verhaltensaspekte der Besatzungen eine Rolle.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Indikator:** Zeitintervall zwischen erster Alarmierung und Ausrücken des Rettungsmittels (FMS-Status 3)
            
**Grundgesamtheit:** Alarmierungen Leitstellen-eigener Notfallrettungsmittel (RTW, NEF, NAW, RTH, dual-use-Hubschrauber) zu Primäreinsätzen in der Notfallrettung mit Alarmierung als Notfalleinsatz
            
**Ergebnisdarstellung:** Median, Quartile, 10. und 90. Perzentil in Minuten und Sekunden
            
**Stratifizierungen** 
* Alarmierung aus FMS-Status 2 vs. andere Status
* Nach Rettungsmitteltyp (RTW vs. NEF vs. NAW vs. Luftrettung)
                       
""")

st.subheader("Gefilterte Datenvorschau")
