import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("3.2 Acetylsalicylsäure bei ST-Hebungsinfarkt")



# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
Patienten mit STEMI erhalten ASS gemäß aktueller Empfehlungen.
                                                            
## Rationaleie 
Patienten mit akutem ST-Hebungs-Myokardinfarkt (STEMI) sollen gemäß der
Leitlinie der European Society of Cardiology so schnell wie möglich Acetylsalicylsäure (ASS) erhalten, sofern keine Kontraindikation vorliegt (Klasse-I-Empfehlung, Evidenz B).

""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit dokumentierter ASS-Gabe bei Primäreinsätzen in der Notfallrettung bei Patienten mit dokumentiertem STEMI unter Ausschluss von Behandlungsverweigerung und Palliativsituationen            

**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit dokumentiertem STEMI unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                                                                    
**Ergebnisdarstellung:** Anteil in Prozent
                      
""")

st.subheader("Gefilterte Datenvorschau")
