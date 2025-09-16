import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("2.5 Befunderhebung Schlaganfall")

import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Load configuration
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
stauth.Hasher.hash_passwords(config['credentials'])

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)
try:
    authenticator.login()
except Exception as e:
    st.error(e)


# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
Bei Patienten mit V.a. Schlaganfall sollen (zusätzlich zu den Vitalparametern) GCS, BZ, Seitenzeichen / Sprachstörung, Körpertemperatur, Rhythmusfeststellung und Symptombeginn dokumentiert werden.
                        
## Rationaleie 
Um die rasche und zielgerichtete Therapie zu bahnen ist bei Patienten mit akutem fokalem neurologischem Defizit eine sorgfältige präklinische Befunderhebung erforderlich. Dies erlaubt eine Verlaufsbeurteilung und Differentialdiagnose des Schlaganfalls. Versäumnisse können in der Klinik nur bedingt kompensiert werden. Die von den einschlägigen Leitlinien empfohlene Befunddokumentation wird von diesem Qualitätsindikator adressiert.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit Dokumentation von GCS, BZ, neurologischem Befund, Körpertemperatur, Rhythmusfeststellung und Symptombeginn bei Primäreinsätzen in der Notfallrettung bei Patienten mit V.a. akuten Schlaganfall / akut aufgetretenem neurologischem Defizit unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                                    
**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit V.a. akuten Schlaganfall/ akut aufgetretenem neurologischem Defizit unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
                                                
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Symptombeginn bis einschließlich 6 Stunden bis Ankunft (frühester dokumentierter Status 4 eines RTW / arztbesetzten Rettungsmittels) vs. > 6 Stunden
                       
""")

st.subheader("Gefilterte Datenvorschau")
