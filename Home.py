import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Qualitätskriterien Dashboard",
    page_icon="🚑",
    layout="wide"
)

# Title and introduction
st.title("🚑 Qualitätskriterien Dashboard")

st.markdown("""
## Willkommen zum Rettungsdienst-Qualitätsdashboard!

Dieses Dashboard bietet umfassende Analysen zu den definierten Qualitätsindikatoren im Rettungsdienst.  
Nutze die Navigation in der Seitenleiste, um detaillierte Auswertungen und Trends zu den verschiedenen Kategorien zu entdecken.
""")

# Categories section
st.markdown("""
### 📊 Verfügbare Kategorien

| Nr. | Kategorie | Beschreibung |
|-----|-----------|--------------|
| 1️⃣ | **Prozesszeiten** | Analyse von Reaktions-, Versorgungs- und Transportintervallen |
| 2️⃣ | **Befunderhebung** | Monitoring und Dokumentation von Vitalparametern |
| 3️⃣ | **Therapie** | Durchführung und Wirksamkeit von Behandlungsmaßnahmen |
| 4️⃣ | **Reanimation** | Outcomes und Prozessqualität bei Reanimationen |
| 5️⃣ | **Zielklinikauswahl** | Evaluation der Zielklinikentscheidungen |

👉 *Wähle eine Kategorie in der Seitenleiste aus, um die entsprechenden Auswertungen zu sehen.*
""")

# Hinweis zu Datenbank-Performance
st.info("""
Aktuell werden **standardmäßig 10.000 Einträge** aus der Datenbank geladen, 
um die Performance zu gewährleisten.  
Dies ermöglicht ein erstes Testen der Auswertungen, 
welche anschließend auf alle verfügbaren Einträge ausgeweitet werden können.
""")

# Two-column layout for data basis and changelog
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
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
    """)

with col2:
    st.markdown("""
    ### 🔄 Versionsverlauf
    
    **Version 2.0 (September 2025)**
    - Neuer Data Loader mit DB-Caching (10 Stunden)
    - Erweiterte Filtermöglichkeiten (Jahr, Datenmenge)
    - Zusätzliche Auswertungen (5.1 bis 5.3)
    - Einbindung Data-Loader für 2.1 bis 2.6
    
    **Version 1.0 (Frühjahr 2025)**
    - Erstellung des Streamlit-Dashboards
    - Integration der Basisdatengrundlage
    
    ### 🔮 Ausblick
    
    **Geplante Erweiterungen:**
    - Integration des Leitstellen-Datensatzes für *Einsatzannahme-Prozesszeiten*
    - Vollständige Anbindung aller NIDA-Protokolldaten über den Index hinaus
    - Erweiterung um zusätzliche Qualitätsindikatoren
    """)

# Footer
st.markdown("""
---
### 📬 Kontakt

**Autor:** Martin Brucker  
📧 [martin.brucker@rettungsdienst-sl-fl.de](mailto:martin.brucker@rettungsdienst-sl-fl.de)  
💻 [GitHub: mbrucker-kiel/streamlit_app](https://github.com/mbrucker-kiel/streamlit_app)

Das Dashboard wird kontinuierlich weiterentwickelt – Feedback und Anregungen sind jederzeit willkommen.

*Stand: September 2025*
""")
