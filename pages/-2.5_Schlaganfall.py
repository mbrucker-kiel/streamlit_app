import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("2.5 Befunderhebung Schlaganfall")



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
