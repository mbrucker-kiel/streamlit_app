import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("1.4 Ausrückeintervall")



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
