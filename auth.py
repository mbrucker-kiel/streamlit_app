import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import os

# Hilfsfunktion zum Überprüfen des Authentifizierungsstatus
def check_authentication():
    """Überprüft, ob der Benutzer authentifiziert ist und leitet ggf. zur Anmeldeseite weiter"""
    # Prüfen, ob der Authentifizierungsstatus bereits im Session State ist
    if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
        # Lade Konfiguration
        if os.path.exists('config.yaml'):
            with open('config.yaml') as file:
                config = yaml.load(file, Loader=SafeLoader)
        else:
            st.error("Konfigurationsdatei nicht gefunden. Bitte führen Sie zuerst auth_config.py aus.")
            st.stop()

        # Erstelle Authentifizierungsobjekt
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days'],
        )

# Hilfsfunktion zum Überprüfen des Authentifizierungsstatus
def check_authentication():
    """Überprüft, ob der Benutzer authentifiziert ist und leitet ggf. zur Anmeldeseite weiter"""
    # Prüfen, ob der Authentifizierungsstatus bereits im Session State ist
    if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
        # Lade Konfiguration
        if os.path.exists('config.yaml'):
            with open('config.yaml') as file:
                config = yaml.load(file, Loader=SafeLoader)
        else:
            st.error("Konfigurationsdatei nicht gefunden. Bitte führen Sie zuerst auth_config.py aus.")
            st.stop()

        # Erstelle Authentifizierungsobjekt
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days'],
        )

        # Zeige Login-Widget und prüfe das Ergebnis
        login_result = authenticator.login()

        # Prüfe, ob das Ergebnis None ist (kann bei Konfigurationsfehlern passieren)
        if login_result is None:
            st.error("Authentifizierungsfehler: Überprüfen Sie die config.yaml Datei und stellen Sie sicher, dass die Passwörter gehasht sind.")
            st.stop()

        # Entpacke das Ergebnis sicher
        try:
            name, authentication_status, username = login_result
        except (TypeError, ValueError) as e:
            st.error(f"Authentifizierungsfehler: {str(e)}")
            st.stop()

        # Speichere Authentifizierungsstatus im Session State
        st.session_state['authentication_status'] = authentication_status
        if authentication_status:
            st.session_state['name'] = name
            st.session_state['username'] = username
            st.session_state['authenticator'] = authenticator
            st.session_state['config'] = config
            return True
        elif authentication_status == False:
            st.error('Benutzername/Passwort ist falsch')
            return False
        else:
            st.warning('Bitte geben Sie Ihren Benutzernamen und Ihr Passwort ein')
            return False

    return st.session_state['authentication_status']

    return st.session_state['authentication_status']

# Hilfsfunktion für Logout
def logout():
    """Meldet den Benutzer ab"""
    if 'authenticator' in st.session_state:
        st.session_state['authenticator'].logout('Abmelden', 'sidebar')
        # Wenn der Logout-Button geklickt wurde, wird der Session State zurückgesetzt
        if st.session_state['logout']:
            for key in ['authentication_status', 'name', 'username', 'authenticator', 'config']:
                if key in st.session_state:
                    del st.session_state[key]
            st.experimental_rerun()