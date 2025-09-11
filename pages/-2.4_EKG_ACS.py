import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("2.4 12-Kanal-EKG bei V.a. Akutes Koronarsyndrom (ACS)")

ekg_df = data_loading("12-Kanal-EKG")
df_index = data_loading("Index")

st.write(ekg_df)
st.write(df_index)
# df_index["leadingDiagnosis"] contains STEMI ACS Brustschmerz, angina pektoris, Herzinfarkt
# ekg_df["performed"] == True, match over protocolId

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Bei Patienten mit akutem Brustschmerz oder V.a. ACS soll ein 12-Kanal-EKG abgeleitet werden.**
            
## Rationaleie 
Die prähospitale Registrierung eines 12-Kanal-EKGs bei Patientinnen und Patienten mit Verdacht auf einen ST-Streckenhebungsinfarkt beschleunigt nicht nur die prä- bzw. intrahospitale Reperfusion, sondern vermindert auch die Sterblichkeit. Daher empfehlen die Leitlinien der European Society of Cardiology (ESC) und des European Resuscitation Council (ERC) die Ableitung eines 12-Kanal-EKGs innerhalb von 10 Minuten ab erstem Patientenkontakt.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit dokumentiertem 12-Kanal-EKG bei Primäreinsätzen in der Notfallrettung bei Patienten mit unklarem Thoraxschmerz / V.a. ACS unter Ausschluss von Behandlungsverweigerung und Palliativsituatione
                        
**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit unklarem Thoraxschmerz / V.a. ACS unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                                    
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Einsatzort (Krankenhaus oder Arztpraxis vs. sonstige)
                       
""")

st.subheader("Gefilterte Datenvorschau")
