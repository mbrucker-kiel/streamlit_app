import streamlit as st
import pandas as pd
from data_loading import data_loading

# ========== KEYCLOAK LOGIN CHECK ==========
# Check if user is logged in with Keycloak
if not st.user.is_logged_in:
    st.set_page_config(page_title="KTW.sh - Login erforderlich", layout="centered")
    
    st.title("🔐 Authentifizierung erforderlich")
    st.write("Diese Seite ist geschützt. Bitte melden Sie sich mit Ihrem Keycloak-Account an.")
    
    if st.button(
        "✨ Mit Keycloak anmelden ✨",
        type="primary",
        use_container_width=True,
    ):
        st.login()
    
    st.stop()  # Stop execution of the rest of the page

st.title("🚨 Sonderrechte Dashboard")


st.markdown("""
### 📋 Überblick
Dieses Dashboard analysiert die Nutzung von **Sonderrechten (Blaulicht & Sirene)** 
im Rettungsdienst. Es zeigt detailliert auf, in welchen Fahrtphasen Sonderrechte 
eingesetzt wurden.

### 🎯 Funktionalität
Wählen Sie ein **Fahrzeug** und ein **Datum** aus, um folgende Informationen zu sehen:
- **Anfahrtsphase**: Von Alarmierung bis Eintreffen am Einsatzort
- **Transportphase**: Von Abfahrt vom Einsatzort bis Ankunft im Zielort
- **Sonderrechte-Status**: Ob Blaulicht und Sirene in jeder Phase verwendet wurden

### 📊 Datenquelle
Die Daten stammen aus dem **Leitstellendatensatz (ETÜ)** und zeigen die 
tatsächlich dokumentierten Zeiten und Sonderrechte-Nutzung.
""")




etu_df = data_loading("ETÜ")

# ========== FILTERS ==========
col1, col2 = st.columns(2)

with col1:
    # Filter for EINSATZMITTEL (Vehicle)
    vehicles = sorted(etu_df["EINSATZMITTEL"].dropna().unique())
    selected_vehicle = st.selectbox("🚑 Fahrzeug auswählen:", vehicles)

with col2:
    # Filter for Date
    etu_df["ALARMIERT_date"] = pd.to_datetime(etu_df["ALARMIERT"], errors="coerce").dt.date
    available_dates = sorted(etu_df["ALARMIERT_date"].dropna().unique(), reverse=True)
    selected_date = st.date_input("📅 Datum auswählen:", value=available_dates[0] if available_dates else None)

# ========== DATA PROCESSING ==========
# Filter data for selected vehicle and date
filtered_df = etu_df[
    (etu_df["EINSATZMITTEL"] == selected_vehicle) &
    (etu_df["ALARMIERT_date"] == selected_date)
].copy()

if filtered_df.empty:
    st.warning(f"❌ Keine Einsätze für {selected_vehicle} am {selected_date} gefunden.")
    st.stop()

st.success(f"✅ {len(filtered_df)} Einsätze gefunden für {selected_vehicle} am {selected_date}")

# ========== ANALYSIS TABLE ==========
st.subheader("📊 Fahrtanalyse - Anfahrt & Transport mit Sonderrechten")

analysis_data = []

for idx, row in filtered_df.iterrows():
    # Anfahrt (Approach)
    alarmiert = pd.to_datetime(row["ALARMIERT"], errors="coerce")
    zeit_an_e = pd.to_datetime(row["ZEIT_AN_E"], errors="coerce")
    sosi = row.get("SOSI", 0)
    
    if pd.notna(alarmiert) and pd.notna(zeit_an_e):
        anfahrt_duration = (zeit_an_e - alarmiert).total_seconds() / 60  # in minutes
        analysis_data.append({
            "Einsatznr": row.get("EINSATZ_NR", "N/A"),
            "Fahrtart": "🚗 Anfahrt",
            "Start": alarmiert.strftime("%H:%M:%S"),
            "Ende": zeit_an_e.strftime("%H:%M:%S"),
            "Dauer (Min)": round(anfahrt_duration, 1),
            "Sonderrechte (SOSI)": "✅ Ja" if sosi == 1 else "❌ Nein"
        })
    
    # Transport (Transport)
    zeit_ab_e = pd.to_datetime(row["ZEIT_AB_E"], errors="coerce")
    zeit_an_z = pd.to_datetime(row["ZEIT_AN_Z"], errors="coerce")
    sosi_zo = row.get("SOSI_ZO", 0)
    
    if pd.notna(zeit_ab_e) and pd.notna(zeit_an_z):
        transport_duration = (zeit_an_z - zeit_ab_e).total_seconds() / 60  # in minutes
        analysis_data.append({
            "Einsatznr": row.get("EINSATZ_NR", "N/A"),
            "Fahrtart": "🚑 Transport",
            "Start": zeit_ab_e.strftime("%H:%M:%S"),
            "Ende": zeit_an_z.strftime("%H:%M:%S"),
            "Dauer (Min)": round(transport_duration, 1),
            "Sonderrechte (SOSI)": "✅ Ja" if sosi_zo == 1 else "❌ Nein"
        })

if analysis_data:
    analysis_df = pd.DataFrame(analysis_data)
    analysis_df["_start_sort"] = pd.to_datetime(
        analysis_df["Start"],
        format="%H:%M:%S",
        errors="coerce",
    )
    analysis_df = analysis_df.sort_values(
        by="_start_sort",
        ascending=False,
        na_position="last",
    ).drop(columns=["_start_sort"])
    st.dataframe(analysis_df, use_container_width=True, hide_index=True)
    
    # Summary statistics
    st.subheader("📈 Zusammenfassung")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Einsätze", len(filtered_df))
    
    with col2:
        anfahrten_mit_sosi = len(analysis_df[(analysis_df["Fahrtart"] == "🚗 Anfahrt") & (analysis_df["Sonderrechte (SOSI)"] == "✅ Ja")])
        st.metric("Anfahrten mit Sonderrechte", anfahrten_mit_sosi)
    
    with col3:
        transporte_mit_sosi = len(analysis_df[(analysis_df["Fahrtart"] == "🚑 Transport") & (analysis_df["Sonderrechte (SOSI)"] == "✅ Ja")])
        st.metric("Transporte mit Sonderrechte", transporte_mit_sosi)
    
    with col4:
        avg_anfahrt = analysis_df[analysis_df["Fahrtart"] == "🚗 Anfahrt"]["Dauer (Min)"].mean()
        st.metric("Ø Anfahrtdauer (Min)", f"{avg_anfahrt:.1f}" if pd.notna(avg_anfahrt) else "N/A")
else:
    st.warning("❌ Keine gültigen Zeitstempel für die Analyse gefunden.")

