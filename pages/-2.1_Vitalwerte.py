import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("2.1 Erhebung und Überwachung der Vitalwerte")

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

df_index = data_loading("Index")
gcs_df = data_loading("GCS")
bd_df = data_loading("bd")
hf_df = data_loading("hf")
spo2_df = data_loading("spo2")
af_df = data_loading("af")
# auch noch geburtsdatum des patienten laden

st.write(df_index)
st.write(gcs_df)
st.write(bd_df)
st.write(hf_df)
st.write(spo2_df)
st.write(af_df)

st.write("was sind genau die Tracer-Diagnosen? Eckpunktepapier?")

st.write("aktuell keine altersprüfung und keine prüfung nach inversiven maßnahmen")

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Erhebung und Überwachung der relevanten Vitalparameter bei schwer erkrankten / schwer verletzten Notfallpatienten.**
            
## Rationale
Die Erhebung und Überwachung der Vitalparameter ist die Voraussetzung für eine adäquate Situationseinschätzung sowie für die Erkennung von klinischen Zustandsänderungen und Komplikationen. Ein Basismonitoring bestehend aus **EKG, nicht-invasiver Blutdruckmessung und Pulsoxymetrie** ist anerkannter notfallmedizinischer Standard. Leitlinien für typische notfallmedizinische Krankheitsbilder empfehlen explizit das Basismonitoring oder gründen Therapieentscheidungen auf den Vitalparametern. Ferner fordern die Fachinformationen zu vielen, insbesondere herzkreislaufwirksamen, potent analgetischen und sedierenden Notfallmedikamenten bei deren Anwendung eine Überwachung der Vitalparameter. Gleichzeitig werden Defizite bei der Dokumentation berichtet.
""")

# for each in df_index wo RTW-Transport
# -> if in transport:
# transport über protocollId versuchen mit gcs_df, bd_df hf_df spo2_df, af_df etwas zu matchen, wenn eintrag gut
# 

# einsätze mit Notarzt = where 


# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit mindestens zweimaliger dokumentierter Messung von GCS, Blutdruck, Herzfrequenz oder Puls, SpO2 und Atemfrequenz bei Primäreinsätzen des Rettungsdienstes bei Patienten ab 5 Jahren mit dokumentierter Tracerdiagnose oder invasiver Maßnahme oder Medikamentengabe unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
            
**Nenner**
Primäreinsätze des Rettungsdienstes bei Patienten ab 5 Jahren mit dokumentierter Tracerdiagnose oder invasiver Maßnahme oder Medikamentengabe unter Ausschluss von Behandlungsverweigerung und Palliativsituationen     

            
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Einsätze mit vs. ohne physischer Notarzt-Beteiligung
                       
""")

st.subheader("Gefilterte Datenvorschau")
