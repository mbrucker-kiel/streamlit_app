import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

st.title("3.3 Notfallnarkose und Intubation bei schwerem Schädel-Hirn-Trauma")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now load data after authentication

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
Patienten mit schwerem Schädel-Hirn-Trauma (SHT) sollen narkotisiert und intubiert werden.
                                                            
## Rationaleie 
Das Ziel der Notfallversorgung bei schwerem SHT ist die Vermeidung eines sekundären Hirnschadens. Dieser entsteht z.B. durch Hypoventilation und/oder
Hypoxie sowie sekundär nach Aspiration. Es konnte ein Outcomevorteil für
präklinisch intubierte, bewusstlose Patienten gezeigt werden. Vor diesem Hintergrund bestehen folgende Leitlinienempfehlungen:
* Bei polytraumatisierten Patienten sollten bei folgenden Indikationen
prähospital eine Notfallnarkose, eine endotracheale Intubation und eine
Beatmung durchgeführt werden: … schweres SHT (GCS < 9)… (Empfehlung
1.2.2., Empfehlungsgrad B) 
* Bewusstlose Patienten (Anhaltsgröße GCS ≤ 8) sollen intubiert werden und
für ausreichende (Be-) Atmung ist zu sorgen. (Empfehlungsgrad A)
* Kinder und Jugendliche: Bei bewusstlosen Patienten (schweres Schädel-Hirn-Trauma) […] soll prähospital eine Atemwegsicherung (tracheale Intubation oder Alternativen) und eine Beatmung inklusive einer Notfallnarkose durchgeführt werden (starker Konsens) (E8). Die tracheale Intubation
soll nur von einem versierten und erfahrenen Anwender durchgeführt werden. Als Alternativen stehen Beutel-Masken-Beatmung und Larynx-Maske
zur Verfügung (starker Konsens)..
Die Verabreichung von Anästhetika ist jedoch mit dem Risiko einer hämodynamischen Verschlechterung verbunden. Es erscheint fraglich, ob bei maximal
bewusstlosen Patienten (GCS 3, z. B. während Traumareanimation) eine Anästhesie in jedem Fall einen Vorteil für den Patienten bringt. Gleichzeitig gilt es,
ein Husten oder Pressen sicher zu vermeiden.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
            
**Zähler**
Fälle mit dokumentierter präklinischer Intubation oder Atemwegssicherung
mittels extraglottischem Atemwegsdevice unter Gabe von mindestens einem Narkotikum (Analgetikum, Hypnotikum) oder eines Muskelrelaxans bei Primäreinsätzen in der Notfallrettung bei Patienten mit Verdacht auf schweres
Schädel-Hirn-Trauma unter Ausschluss von Behandlungsverweigerung und Palliativsituatione     

**Nenner**
Primäreinsätze in der Notfallrettung bei Patienten mit Verdacht auf schweres
Schädel-Hirn-Trauma unter Ausschluss von Behandlungsverweigerung und
Palliativsituationen
             
**Ergebnisdarstellung:** Anteil in Prozent
            
**Stratifizierungen** 
* Transportdauer (0 – 10 min vs. >10 – 20 min vs. > 20 min).                 
""")

df_inturbation = data_loading("Intubation")
df_medikamente = data_loading("Medikamente")
st.write(df_inturbation)
st.write(df_medikamente)