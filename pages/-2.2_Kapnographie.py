import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("2.2 Kapnographie")



# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Anwendung der Kapnographie bei allen Patienten mit erfolgter Atemwegssicherung.**
            
## Rationale
Die Kapnometrie / Kapnographie erlaubt u.a. die Kontrolle der intratrachealen
Tubuslage, die Detektion einer Dislokation der Atemwegssicherung, die Steu-
erung und Überwachung der Ventilation und unterstützt das Kreislaufmonito-
ring.
Die Leitlinie zum prähospitalen Atemwegsmanagement fordert: „Nach in-
vasiver Atemwegssicherung soll bei allen Patienten obligat […] die Kapnografie
unmittelbar angewendet werden.“ Während der weiteren Versorgung und des
Transports soll die Kapnographie kontinuierlich verwendet werden.
Auch die S3-Leitlinie Polytrauma empfiehlt:
* Zur Narkoseeinleitung, endotrachealen Intubation und Führung der Not-
fallnarkose soll der Patient mittels EKG, Blutdruckmessung, Pulsoxymetrie
und Kapnografie überwacht werden (GoR A).
* Die Kapnometrie/-grafie soll präklinisch und innerklinisch im Rahmen der
endotrachealen Intubation zur Tubuslagekontrolle und danach zur Disloka-
tions- und Beatmungskontrolle angewendet werden (GoR A).
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
