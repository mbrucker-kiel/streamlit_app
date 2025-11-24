import streamlit as st


if not st.user.is_logged_in:
    st.set_page_config(page_title="KTW.sh - Login erforderlich", layout="centered")

    st.title("🔐 Authentifizierung erforderlich")
    st.write(
        "Diese Seite ist geschützt. Bitte melden Sie sich mit Ihrem Keycloak-Account an."
    )

    if st.button(
        "✨ Mit Keycloak anmelden ✨",
        type="primary",
        use_container_width=True,
    ):
        st.login()

    st.stop()  # Stop execution of the rest of the page
st.title("1.2 Notruf-Wartezeit")


# Now show content after authentication

st.write(
    "Indikator Zeitintervall zwischen Aufschalten des Notrufs und Notrufannahme in der Leitstelle"
)

st.write("Aktuell kein Datensatz vorhanden")
