import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("4.1 Klinikaufnahme mit ROSC nach Reanimation")

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
Wiederbelebungsmaßnahmen führen zu einem Wiedereinsetzen des Spontankreislaufs                                                            
## Rationaleie 
Das Ziel jeder Reanimationsbemühung stellt die Wiederherstellung des Spontankreislaufs (ROSC) dar. Der Vergleich der ROSC-Raten ist ein national und
international gebräuchlicher Parameter der Ergebnisqualität der kardiopulmonalen Wiederbelebung.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit Spontankreislauf bei Klinikaufnahme bei Einsätzen mit durch den Rettungsdienst durchgeführter außerklinischer Reanimation unter Ausschluss von
Behandlungsverweigerung und Palliativsituationen

**Nenner**
Einsätze mit durch den Rettungsdienst durchgeführter außerklinischer Reanimation unter Ausschluss von Behandlungsverweigerung und Palliativsituationen
        
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Laienreanimation (ja vs. nein)
* Fahrzeit des ersteintreffenden Rettungsmittels (0 – 5 vs. >5 - 10 min vs. >10 – 20 min vs. > 20 min)
* Initialer EKG-Rhythmus (defibrillierbar vs. nicht-defibrillierbar)
* Kollaps beobachtet (ja vs. nein)
* Einsatzort Altenheim vs. Arztpraxis vs. alle anderen""")

st.subheader("Gefilterte Datenvorschau")
