import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("2.5 Befunderhebung und Überwachung Schädel-Hirn-Trauma")



# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
Bei Patienten mit akuten Schädelverletzungen sollen Bewusstseinsstatus, Glasgow Coma Scale (GCS), Pupillenstatus und die motorische Reaktion aller Extremitäten dokumentiert werden.
                                    
## Rationaleie 
Das Vorliegen weiter, lichtstarrer Pupillen sowie eine Verschlechterung des
GCS sind mit schlechtem klinischem Outcome vergesellschaftet. Um die zu
Grunde liegenden Ursachen rasch erkennen und therapieren zu können, empfiehlt die S3-Leitlinie Schwerverletztenversorgung:
Empfehlung 1.46: Die wiederholte Erfassung und Dokumentation von Bewusstseinslage, Pupillenfunktion und Glasgow Coma Scale soll erfolgen. (GoR A)
Zusätzlich wird empfohlen, den motorischen Status aller Extremitäten zu erheben.
Die S2e-Leitlinie SHT empfiehlt analog:
E5: Folgende Parameter zum neurologischen Befund
* Bewusstseinsklarheit, Bewusstseinstrübung oder Bewusstlosigkeit
* Pupillenfunktion und
* Motorische Funktionen seitendifferent an Armen und Beinen
sollen erfasst und dokumentiert werden (Empfehlungsgrad A)
sowie
E7: Der neurologische Befund sollte standardisiert erhoben werden. International hat sich hierfür die GCS eingebürgert. Die Limitationen der Skala (Scheinverbesserungen, Befund bei Intubation, Analgosedierung u.a.) müssen berücksichtigt werden (Empfehlungsgrad B).
Bei Kindern < 2 Jahren ist eine Modifikation des GCS erforderlich. Alternativ
kann die AVPU-Skala verwendet werden.""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit vollständiger Dokumentation von initialem Bewusstseinsstatus (wach/ getrübt / bewusstlos oder AVPU-Schema), Pupillenstatus und mindestens zweimalig GCS (erst ab dem vollendeten 2. Lebensjahr)bei Primäreinsätzen in der Notfallrettung bei Patienten mit Schädel-Hirn-Trauma, die lebend in eine Klinik aufgenommen werden

**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit Schädel-Hirn-Trauma, die lebend in eine Klinik aufgenommen werden    
                                                        
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Nach Schwere des Schädel-Hirn-Traumas (leicht vs. mittel vs. schwer)
""")

st.subheader("Gefilterte Datenvorschau")
