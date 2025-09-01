import streamlit as st

# Set page configuration
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
Navigiere durch die verschiedenen Kategorien, um detaillierte Auswertungen und Trends zu entdecken.
""")

# Main categories section with better formatting
st.markdown("""
### 📊 Verfügbare Kategorien

| Kategorie | Beschreibung |
|-----------|-------------|
| **1. Prozesszeiten** | Analyse von Reaktions-, Versorgungs- und Transportintervallen |
| **2. Befunderhebung** | Monitoring und Dokumentation von Vitalparametern |
| **3. Therapie** | Durchführung und Wirksamkeit von Behandlungsmaßnahmen |
| **4. Reanimation** | Outcomes und Prozessqualität bei Reanimationen |
| **5. Zielklinikauswahl** | Evaluation der Zielklinikentscheidungen |

*Wähle eine Kategorie in der Seitenleiste, um die entsprechenden Auswertungen zu sehen.*
""")

# Create columns for more compact information display
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📝 Datengrundlage
    
    Die dargestellten Qualitätsindikatoren basieren auf den Empfehlungen der 
    AG "Qualität im Rettungsdienst" (Version 2.1, Stand 05.02.2025).
    
    **Aktuelle Datenquellen:**
    - NIDA-Protokoll Indexdatei
    - Statuszeiten für Stroke-Patienten
    """)

with col2:
    st.markdown("""
    ### 🔄 Versionsverlauf
    
    **Version 1.0** 
    - Erstellen des Streamlit-Dashboards
    - Integration der Basisdatengrundlage
    
    ### 🔮 Ausblick
    
    **Geplante Erweiterungen:**
    - Integration des Leitstellen-Datensatzes für "EINSATZANNAHME"-Prozesszeiten
    - Anbindung aller NIDA-Protokolldaten über den Index hinaus
    - Erweiterung um weitere Qualitätsindikatoren
    """)

# Footer with contact information
st.markdown("""
---
### Kontakt

**Autor:** Martin Brucker  
**E-Mail:** martin.brucker@rettungsdienst-sl-fl.de

*Stand: August 2025*
""")