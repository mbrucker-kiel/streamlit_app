import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime

st.title("3.1 Effektive Schmerzlinderung")

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
Bei starken Schmerzen (NRS ≥ 5) soll eine wirksame Schmerzlinderung erfolgen (Reduktion auf < 5 oder um mindestens 2 Punkte)
                                                
## Rationaleie 
Notfallpatienten mit akuten, starken Schmerzen erwarten vom Rettungsdienst
(Notarzt / Notfallsanitäter) eine zeitnahe und effektive Schmerzlinderung. Eine
solche hat auch positive Wirkungen auf den weiteren Heilungsverlauf. Da
Schmerz nicht objektiviert werden kann, erfolgt eine Selbsteinschätzung z. B.
mittels der nummerischen Rating Skala (NRS; von 0 = gar kein Schmerz bis 10
= maximaler vorstellbarer Schmerz). Bezüglich der Zielwerte der Analgesie
bzw. Anforderungen an eine relevante Schmerzreduktion äußert sich die Literatur uneinheitlich. Angestrebt werden soll ein NRS-Niveau unter 4 oder eine
Verbesserung um mindestens 3 Punkte, bzw. eine Reduktion um 40 %. Laut Polytrauma-Leitlinie liegt der NRS-Zielwert bei ≤ 4. Es ist aber zu
hinterfragen, ob diese Idealziele bereits während einer relativ kurzen Phase
der rettungsdienstlichen Notfallversorgung erreicht werden müssen, ggf. unter Inkaufnahme von Risiken durch überhastete medikamentöse Analgetikagaben. Aufgrund dieser Überlegungen wurden die Schwellenwerte für effektive Analgesie konservativer gestaltet.
Zur Linderung von Schmerzen kommen nicht-pharmakologische (z. B. Lagerung, Ruhigstellung, Kühlung, Zuwendung) und pharmakologische Interventionen zur Anwendung. Medikamentöse Schmerztherapie erfolgt durch notärztliches und Rettungsfachpersonal.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit einem dokumentierten Übergabe-NRS < 5 oder einer Verbesserung um 2 oder mehr Punkte bei Übergabe im Vergleich zum Initialwert bei Primäreinsätzen in der Notfallrettung bei Patienten mit einem dokumentierten initialen NRS ≥ 5 unter Ausschluss einer Behandlungsverweigerung
            

**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit einem dokumentierten
initialen NRS ≥ 5 unter Ausschluss einer Behandlungsverweigerung
                                                                    
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Analgetikagabe (ja vs. nein)
 *NRS bei Übergabe (oder gleichwertig „analgosediert / Narkose“) dokumentiert (nur ja)
                        
""")

st.subheader("Gefilterte Datenvorschau")
