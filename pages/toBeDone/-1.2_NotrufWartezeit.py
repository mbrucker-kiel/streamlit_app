import streamlit as st

st.title("1.2 Notruf-Wartezeit")

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

st.write("Indikator Zeitintervall zwischen Aufschalten des Notrufs und Notrufannahme in der Leitstelle")

st.write("Aktuell kein Datensatz vorhanden")