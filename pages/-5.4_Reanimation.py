import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from data_loading import data_loading

# Title and description
st.title("5.4  Zielklinik Z.n. Reanimation")

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

df_krankenhaus = pd.read_csv('data/krankenhausDigagnosen.csv', sep=';')
st.write(df_krankenhaus)
df_reanimation = data_loading("Reanimation")
st.write(df_reanimation)

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Patienten mit V.a. eine Tracerdiagnose werden primär in eine geeignete Zielklinik transportiert.**

""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Zähler:** Fälle mit Aufnahme in ein zertifiziertes Cardiac Arrest Zentrum (oder gleichwertig geeignetes Krankenhaus) bei Primäreinsätzen in der Notfallrettung mit
präklinischer Reanimation erwachsener, nicht-traumatologischer Patienten und wiedererlangtem Spontankreislauf (ROSC) bei Klinikaufnahme
            
**Nenner:** Primäreinsätze in der Notfallrettung mit präklinischer Reanimation erwachsener, nicht-traumatologischer Patienten und wiedererlangtem Spontankreislauf (ROSC) bei Klinikaufnahme
            
**Ergebnisdarstellung:** Anteil in Prozent
""")