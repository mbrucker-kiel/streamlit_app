import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("4.1 Klinikaufnahme mit ROSC nach Reanimation")



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
