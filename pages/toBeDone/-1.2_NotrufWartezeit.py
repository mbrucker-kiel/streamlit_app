import streamlit as st
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

st.title("1.2 Notruf-Wartezeit")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')

# Now show content after authentication

st.write("Indikator Zeitintervall zwischen Aufschalten des Notrufs und Notrufannahme in der Leitstelle")

st.write("Aktuell kein Datensatz vorhanden")