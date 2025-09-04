import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("1.3 Erstbearbeitungszeit in der Leitstelle")

st.write("Datenloader mit Leitstellendaten erweitern")

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Die Alarmierung der Einsatzmittel erfolgt verzögerungsfrei**

## Rationale
Die Dauer des Notrufgesprächs und der Rettungsmitteldisposition ist Teil des therapiefreien Intervalls. Die Herausforderung für die Leitstellen besteht dabei in einer möglichst raschen, aber dennoch zielgenauen Notrufabfrage und Disposition.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Indikator:** Zeitintervall zwischen Notrufannahme und Erstalarmierung des ersten alarmierten Einsatzmittels.

**Grundgesamtheit:** Erstmalige Notrufe über die Notrufnummer mit der höchsten Priorität mit Alarmierung mindestens eines Leitstellen-eigenen Rettungsmittels als Notfalleinsatz

**Ergebnisdarstellung:** Median, Quartile, 10. und 90. Perzentil in Minuten und Sekunden
""")

st.subheader("Gefilterte Datenvorschau")
