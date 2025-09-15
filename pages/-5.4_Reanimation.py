import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from data_loading import data_loading

st.set_page_config(layout="wide", page_title="Polytrauma Analysis Dashboard")

# Title and description
st.title("5.4  Zielklinik Z.n. Reanimation")

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