import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("2.2 Kapnographie")

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

st.write("aktuell noch probleme mit laden der kapnographie daten, hier ist in nida was gespeichert aber in der mongoDb sind leere objekte siehe protokoll '4650'")

df_kapnographie = data_loading("co2")
df_inturbation = data_loading("Intubation")

# df_inturbation["type"].value_counts()

st.write(df_kapnographie, limit=100000)
st.write(df_inturbation)
# tuben bei denen kapno möglich ist: df_inturbation["type"] = "Endotrachealtubus", "Larynxmaske", "Larynxtubus"

# für jedes protkoll mit inturbation df_inturbation["protokolId"] müssen df_kapnographie["value"] werte existieren > 0
# -> hierbei können auch mehrere einträge in df_kapnographie pro protokolId existieren

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Anwendung der Kapnographie bei allen Patienten mit erfolgter Atemwegssicherung.**
            
## Rationale
Die Kapnometrie / Kapnographie erlaubt u.a. die Kontrolle der intratrachealen
Tubuslage, die Detektion einer Dislokation der Atemwegssicherung, die Steu-
erung und Überwachung der Ventilation und unterstützt das Kreislaufmonito-
ring.
Die Leitlinie zum prähospitalen Atemwegsmanagement fordert: „Nach invasiver Atemwegssicherung soll bei allen Patienten obligat […] die Kapnografie
unmittelbar angewendet werden.“ Während der weiteren Versorgung und des
Transports soll die Kapnographie kontinuierlich verwendet werden.
Auch die S3-Leitlinie Polytrauma empfiehlt:
* Zur Narkoseeinleitung, endotrachealen Intubation und Führung der Notfallnarkose soll der Patient mittels EKG, Blutdruckmessung, Pulsoxymetrie
und Kapnografie überwacht werden (GoR A).
* Die Kapnometrie/-grafie soll präklinisch und innerklinisch im Rahmen der
endotrachealen Intubation zur Tubuslagekontrolle und danach zur Dislokations- und Beatmungskontrolle angewendet werden (GoR A).
Während Reanimation soll die Kapnographie zur Überwachung der Qualität
der Herzdruckmassage und nach Wiedererlangung eines Spontankreislaufs zur
Steuerung der Ventilation zum Einsatz kommen.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit dokumentierter Kapnometrie / Kapnographie bei Einsätzen in Notfallrettung und Interhospitaltransfer bei Patienten mit dokumentierter Atemwegssicherung.            

**Nenner**
Einsätze in Notfallrettung und Interhospitaltransfer bei Patienten mit dokumentierter Atemwegssicherung
            
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Einsatzart Notfallrettung vs. Interhospitaltransfer
* Reanimationssituation (ja vs. nein)
* Art der Atemwegssicherung (endotracheale Intubation vs. EGA)
                       
""")

st.subheader("Gefilterte Datenvorschau")
