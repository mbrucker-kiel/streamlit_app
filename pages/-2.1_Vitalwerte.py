import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("2.1 Erhebung und Überwachung der Vitalwerte")



# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Erhebung und Überwachung der relevanten Vitalparameter bei schwer erkrankten / schwer verletzten Notfallpatienten.**
            
## Rationale
Die Erhebung und Überwachung der Vitalparameter ist die Voraussetzung für eine adäquate Situationseinschätzung sowie für die Erkennung von klinischen Zustandsänderungen und Komplikationen. Ein Basismonitoring bestehend aus **EKG, nicht-invasiver Blutdruckmessung und Pulsoxymetrie** ist anerkannter notfallmedizinischer Standard. Leitlinien für typische notfallmedizinische Krankheitsbilder empfehlen explizit das Basismonitoring oder gründen Therapieentscheidungen auf den Vitalparametern. Ferner fordern die Fachinformationen zu vielen, insbesondere herzkreislaufwirksamen, potent analgetischen und sedierenden Notfallmedikamenten bei deren Anwendung eine Überwachung der Vitalparameter. Gleichzeitig werden Defizite bei der Dokumentation berichtet.
""")

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
