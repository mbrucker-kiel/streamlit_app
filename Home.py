import streamlit as st

if not st.user.is_logged_in:
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

# Title and introduction
st.title("🚑 Qualitätskriterien Dashboard")

st.markdown(
    """
## Willkommen zum Rettungsdienst-Qualitätsdashboard!

Dieses Dashboard bietet umfassende Analysen zu den definierten Qualitätsindikatoren im Rettungsdienst.  
Nutze die Navigation in der Seitenleiste, um detaillierte Auswertungen und Trends zu den verschiedenen Kategorien zu entdecken.
"""
)

# Categories section
st.markdown(
    """
### 📊 Verfügbare Kategorien

| Nr. | Kategorie | Beschreibung |
|-----|-----------|--------------|
| 1️⃣ | **Prozesszeiten** | Analyse von Reaktions-, Versorgungs- und Transportintervallen |
| 2️⃣ | **Befunderhebung** | Monitoring und Dokumentation von Vitalparametern |
| 3️⃣ | **Therapie** | Durchführung und Wirksamkeit von Behandlungsmaßnahmen |
| 4️⃣ | **Reanimation** | Outcomes und Prozessqualität bei Reanimationen |
| 5️⃣ | **Zielklinikauswahl** | Evaluation der Zielklinikentscheidungen |

👉 *Wähle eine Kategorie in der Seitenleiste aus, um die entsprechenden Auswertungen zu sehen.*
"""
)

# Hinweis zu Datenbank-Performance
st.info(
    """
Aktuell werden **standardmäßig 10.000 Einträge** aus der Datenbank geladen, 
um die Performance zu gewährleisten.  
Dies ermöglicht ein erstes Testen der Auswertungen, 
welche anschließend auf alle verfügbaren Einträge ausgeweitet werden können.

Mithilfe der dargestellten protocollId lassen sich einzelne Einsätze in der NIDA-Datenbank nachvollziehen.

Die einzelnen Protokolle können sich anhand der Protokoll ID angeschaut werden:
"""
)

# Show URLs from environment variables
import os

base_url = os.getenv("NIDA_PROTOCOL_BASE_URL")
example_url = os.getenv("NIDA_PROTOCOL_EXAMPLE_URL")

st.markdown(f"**Basis-URL:** {base_url}")
st.markdown(f"**Beispiel:** {example_url}")

# Two-column layout for data basis and changelog
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
    ### 📝 Datengrundlage

    Die dargestellten Qualitätsindikatoren basieren auf den Empfehlungen der  
    **AG "Qualität im Rettungsdienst" (Version 2.1, Stand 05.02.2025)**.

    **Aktuelle Datenquellen (NIDA-Protokoll API-Routen):**
    - `findings`
    - `measures`
    - `results`
    - `vitals`
    - `index`
    - `details`
    """
    )

with col2:
    st.markdown(
        """
    ### 🔄 Versionsverlauf

    **Version 2.2**
    - KeyCloak integration für Authentifizierung
    - ktw.sh Statuszeit Analyse

    **Version 2.1**
    - Hotspot-Analyse 6.0
    - Data Helper: KTW Indikationsprüfung 
    - Data Loader: freetext, ETÜ
    - Merging von NIDA-Protokollen und ETÜ Daten            

    **Version 2.0**
    - Neuer Data Loader mit DB-Caching (1 Woche)
    - Erweiterte Filtermöglichkeiten (Jahr, Datenmenge)
    - Zusätzliche Auswertungen (5.1 bis 5.3)
    - Einbindung Data-Loader für 2.1 bis 2.6

    **Version 1.0**
    - Erstellung des Streamlit-Dashboards
    - Integration der Basisdatengrundlage
    - Zeitauswertung 

    ### 🔮 Ausblick

    **Geplante Erweiterungen:**
    - Integration des Leitstellen-Datensatzes für *Einsatzannahme-Prozesszeiten*
    - Entwicklung aller Qualitätsindikatoren (1.1.1 bis 5.4)
    - Erweiterung um zusätzliche Qualitätsindikatoren
    """
    )

# Footer
st.markdown(
    """
---
### 📬 Kontakt

**Autor:** Martin Brucker  
📧 [martin.brucker@rettungsdienst-sl-fl.de](mailto:martin.brucker@rettungsdienst-sl-fl.de)  
💻 [GitHub: mbrucker-kiel/streamlit_app](https://github.com/mbrucker-kiel/streamlit_app)

Das Dashboard wird kontinuierlich weiterentwickelt – Feedback und Anregungen sind jederzeit willkommen.

*Stand: November 2025*
"""
)
