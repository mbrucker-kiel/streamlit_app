import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("2.3 Blutzucker-Messung bei Bewusstseinsminderung")



# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Bei jedem bewusstseinsveränderten Patienten erfolgt eine Blutglukosebestimmung.**
            
## Rationaleie 
Die Blutzucker-Bestimmung kann das Vorliegen einer leicht behandelbaren Hypoglykämie als Ursache für Bewusstseinsveränderungen aufdecken und damit für die weitere Therapie wegweisend sein. Damit ist für die Leitlinienautoren die Messung der Blutglukose einer der wichtigsten Parameter im Rahmen der präklinischen Versorgung von bewusstseinsgeminderten Patienten.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit mindestens einem dokumentiertem Blutglukosewert bei Primäreinsätzen in der Notfallrettung bei Patienten mit Bewusstseinseinschränkung (GCS < 15) im Erstbefund unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit Bewusstseinseinschränkung im Erstbefund unter Ausschluss von Behandlungsverweigerung und Palliativsituationen.
                        
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Reanimationssituation (ja vs. nein)
* Altersgruppe (< 16 Jahre vs. ≥ 16 Jahre)
                       
""")

st.subheader("Gefilterte Datenvorschau")
