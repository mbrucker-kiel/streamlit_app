import streamlit as st
import pandas as pd
from data_loading import data_loading
import plotly.express as px
import plotly.graph_objects as go
from auth import check_authentication
from data_helpers import analyze_freetext_requirements

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()


st.title("Schwerpunktanalyse")

st.markdown("""
Aufgrund wiederkehrender Anfragen ist aufgefallen, dass die Adresse häufig als Einsatz ohne Transportindikation auftaucht.  
Mithilfe dieser Auswertung sollen tiefere Einblicke in die Daten gewonnen werden, um mögliche Ursachen zu identifizieren.  

**Filteroptionen:**  
In dem folgenden Dropdown-Menü können gezielt Einsätze nach Stadt, Straße und Hausnummer gefiltert werden.
""")

color = ["#8ea9db", "#ffc000", "#ffff00", "#92d050", "#7030a0"]
color_brighter = ["#a8c0f0", "#ffd966", "#ffff99", "#b6d7a8", "#8a4fbf"]
color_darker = ["#6d8ac9", "#e6b800", "#e6e600", "#6aa84f", "#4a1d6a"]
# nef, ktw, sktw, rtw, unterstützer/sonstige
# darker when missionTypeIncludes "kein Transport"

index_df = data_loading("Index", limit=50000) 


# filter for patient address use env variables as placeholders
with st.expander("Filteroptionen"):
    st.write("Filteroptionen für die Schwerpunktanalyse")
    
    # City filter with "Alle" option
    city_options = ["Alle"] + list(index_df["patientCity"].dropna().unique())
    st.selectbox("Stadt", options=city_options, key="city_filter")
    
    # Filter by city first to get streets
    temp_filtered = index_df
    if st.session_state["city_filter"] != "Alle":
        temp_filtered = temp_filtered[temp_filtered["patientCity"] == st.session_state["city_filter"]]
    
    # Street filter with "Alle" option, dynamic based on city
    street_options = ["Alle"] + list(temp_filtered["patientStreet"].dropna().unique())
    st.selectbox("Straße", options=street_options, key="street_filter")
    
    # Filter by street to get house numbers
    if st.session_state["street_filter"] != "Alle":
        temp_filtered = temp_filtered[temp_filtered["patientStreet"] == st.session_state["street_filter"]]
    
    # House number filter with "Alle" option, dynamic based on city and street
    house_options = ["Alle"] + list(temp_filtered["patientHouseNumber"].dropna().unique())
    st.selectbox("Hausnummer", options=house_options, key="house_number_filter")

filtered_df = index_df

if st.session_state["city_filter"] != "Alle":
    filtered_df = filtered_df[filtered_df["patientCity"] == st.session_state["city_filter"]]

if st.session_state["street_filter"] != "Alle":
    filtered_df = filtered_df[filtered_df["patientStreet"] == st.session_state["street_filter"]]
    
if st.session_state["house_number_filter"] != "Alle":
    filtered_df = filtered_df[filtered_df["patientHouseNumber"] == st.session_state["house_number_filter"]]

# Filter für Einsatzdatum Intervall
st.date_input("Einsatzdatum von-bis", 
              value=(pd.to_datetime("2025-01-01T00:00:00"), pd.to_datetime("2025-12-31")),
              key="date_range")

# filter df based on index_df["missionDate"]
start_date, end_date = st.session_state["date_range"]

# Fix: Convert to timezone-aware datetime in UTC to match the column's dtype
start_date_utc = pd.to_datetime(start_date).tz_localize('UTC')
end_date_utc = pd.to_datetime(end_date).tz_localize('UTC')

filtered_df['alarmTime'] = pd.to_datetime(filtered_df['alarmTime']).dt.tz_convert('UTC')

mask = (filtered_df["alarmTime"] >= start_date_utc) & (filtered_df["alarmTime"] <= end_date_utc)
filtered_df = filtered_df.loc[mask]

# i want to display big the total number of filtered_df and display a pie chart with missionType

st.markdown(f"### Gesamtanzahl der Einsätze: {len(filtered_df)}")

# Display pie chart for missionType distribution
if 'staticMissionType' in filtered_df.columns:
    mission_counts = filtered_df['staticMissionType'].value_counts().reset_index()
    mission_counts.columns = ['staticMissionType', 'count']
    
    # Group small categories into "Sonstige" after top 10
    if len(mission_counts) > 10:
        # Sort by count descending
        mission_counts = mission_counts.sort_values('count', ascending=False)
        
        # Keep top 10
        top_10 = mission_counts.head(10)
        
        # Sum the rest into "Sonstige"
        other_count = mission_counts.iloc[10:]['count'].sum()
        
        # Create new dataframe with top 10 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame({'staticMissionType': ['Sonstige'], 'count': [other_count]})
            mission_counts = pd.concat([top_10, other_row], ignore_index=True)
    
    st.write("**Verteilung der Einsatztypen:**")
    st.write(mission_counts)

    fig = px.pie(mission_counts, names='staticMissionType', values='count', 
                title='Verteilung der Einsatztypen (Top 10 + Sonstige)',
                color_discrete_sequence=color)
    st.plotly_chart(fig)

# Filter for Krankentransport missions
if 'staticMissionType' in filtered_df.columns:
    # Get unique types for filtering
    unique_types = filtered_df['staticMissionType'].unique()
    
    # Filter for Krankentransport only (exclude RTW and other emergency transports)
    krankentransport_values = [val for val in unique_types if 'krankentransport' in str(val).lower() and 'rtw' not in str(val).lower()]
    if krankentransport_values:
        filtered_df = filtered_df[filtered_df["staticMissionType"].isin(krankentransport_values)]
        st.write(f"**Gefiltert nach: {krankentransport_values}**")
    else:
        # Fallback to exact match if no values found
        filtered_df = filtered_df[filtered_df["staticMissionType"] == "Krankentransport"]
    
    st.write(f"**Nach Filter: {len(filtered_df)} Krankentransport-Einsätze gefunden**")

# Note: KTW-specific filtering will be applied only for the anamnesis analysis below

st.dataframe(filtered_df)

# display Einsätze pro Woche differentiated by emergencyCareType 
st.subheader("Einsätze pro Woche nach emergencyCareType")
if 'emergencyCareType' in filtered_df.columns:
    filtered_df['week'] = filtered_df['missionDate'].dt.to_period('W').apply(lambda r: r.start_time)
    weekly_counts = filtered_df.groupby(['week', 'emergencyCareType']).size().reset_index(name='counts')
    
    # Apply color scheme based on vehicle types
    fig = px.bar(weekly_counts, x='week', y='counts', color='emergencyCareType', 
                title='Einsätze pro Woche nach Einsatzart',
                color_discrete_sequence=color,
                labels={'week': 'Woche', 'counts': 'Anzahl je Woche'})
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'emergencyCareType' nicht gefunden im Datensatz.")

# display Einsätze pro Woche differentiated by missionType
st.subheader("Einsätze pro Woche nach missionType")
if 'missionType' in filtered_df.columns:
    filtered_df['week'] = filtered_df['missionDate'].dt.to_period('W').apply(lambda r: r.start_time)
    weekly_counts = filtered_df.groupby(['week', 'missionType']).size().reset_index(name='counts')
    
    # Apply color scheme and use darker colors for "kein Transport" missions
    def get_color_for_mission(mission_type):
        if pd.isna(mission_type):
            return color[4]  # default - unterstützer color for unknown
        mission_str = str(mission_type).lower()
        
        # Check for "kein Transport" first (these get darker shades)
        if 'kein transport' in mission_str or 'keine versorgung' in mission_str:
            if 'nef' in mission_str:
                return color_darker[0]  # nef keine versorgung - darker blue
            elif 'ktw' in mission_str:
                return color_darker[1]  # ktw - darker orange
            elif 'rtw' in mission_str:
                return color_darker[3]  # rtw - darker green
            elif 's-ktw' in mission_str:
                return color_darker[2]  # sktw - darker yellow
            else:
                return color_darker[4]  # default darker for unknown vehicle
        
        # Regular missions (normal colors)
        if 'nef' in mission_str:
            return color[0]  # nef - blue
        elif 'rtw' in mission_str:
            return color[3]  # rtw - green
        elif 's-ktw' in mission_str:
            return color[2]  # sktw - yellow
        elif 'ktw' in mission_str:
            return color[1]  # ktw - orange
        elif 'unterstützer' in mission_str or 'dienstfahrt' in mission_str or 'werkstattfahrt' in mission_str or 'sonstige' in mission_str:
            return color[4]  # unterstützer/sonstige - purple
        else:
            return color[4]  # default - purple for other types
    
    # Create custom color mapping
    unique_missions = weekly_counts['missionType'].unique()
    color_mapping = {mission: get_color_for_mission(mission) for mission in unique_missions}
    
    # Define custom category order for legend
    category_order = []
    
    # Helper function to check if mission contains "kein transport" or similar
    def has_kein_transport(mission):
        if pd.isna(mission):
            return False
        mission_str = str(mission).lower()
        return 'kein' in mission_str or 'keine' in mission_str or 'ohne' in mission_str
    
    # Add NEF types first (without "kein transport")
    nef_types = [m for m in unique_missions if 'nef' in str(m).lower() and not has_kein_transport(m)]
    category_order.extend(sorted(nef_types))
    
    # Add NEF keine Versorgung
    nef_keine = [m for m in unique_missions if 'nef' in str(m).lower() and has_kein_transport(m)]
    category_order.extend(sorted(nef_keine))
    
    # Add RTW types (without "kein transport")
    rtw_types = [m for m in unique_missions if 'rtw' in str(m).lower() and not has_kein_transport(m) and 's-ktw' not in str(m).lower()]
    category_order.extend(sorted(rtw_types))
    
    # Add RTW keine Versorgung
    rtw_keine = [m for m in unique_missions if 'rtw' in str(m).lower() and has_kein_transport(m) and 's-ktw' not in str(m).lower()]
    category_order.extend(sorted(rtw_keine))
    
    # Add S-KTW types (without "kein transport")
    sktw_types = [m for m in unique_missions if 's-ktw' in str(m).lower() or ('sktw' in str(m).lower() and not has_kein_transport(m))]
    category_order.extend(sorted(sktw_types))
    
    # Add S-KTW keine Versorgung
    sktw_keine = [m for m in unique_missions if ('s-ktw' in str(m).lower() or 'sktw' in str(m).lower()) and has_kein_transport(m)]
    category_order.extend(sorted(sktw_keine))
    
    # Add KTW types (without "kein transport" and not S-KTW)
    ktw_types = [m for m in unique_missions if 'ktw' in str(m).lower() and not 's-ktw' in str(m).lower() and not has_kein_transport(m)]
    category_order.extend(sorted(ktw_types))
    
    # Add KTW keine Versorgung
    ktw_keine = [m for m in unique_missions if 'ktw' in str(m).lower() and not 's-ktw' in str(m).lower() and has_kein_transport(m)]
    category_order.extend(sorted(ktw_keine))
    
    # Add remaining types (unterstützer, sonstige, etc.)
    remaining = [m for m in unique_missions if m not in category_order]
    category_order.extend(sorted(remaining))
    
    fig = px.bar(weekly_counts, x='week', y='counts', color='missionType', 
                title='Einsätze pro Woche nach Einsatztyp',
                color_discrete_map=color_mapping,
                category_orders={'missionType': category_order},
                labels={'week': 'Woche', 'counts': 'Anzahl je Woche'})
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'missionType' nicht gefunden im Datensatz.")


# display Einsätze per Weekday and hour of day
st.subheader("Einsätze nach Wochentag und Uhrzeit")
if 'alarmTime' in filtered_df.columns:
    filtered_df['weekday'] = filtered_df['alarmTime'].dt.day_name()
    filtered_df['hour'] = filtered_df['alarmTime'].dt.hour
    heatmap_data = filtered_df.groupby(['weekday', 'hour']).size().reset_index(name='counts')
    heatmap_data = heatmap_data.pivot(index='weekday', columns='hour', values='counts').fillna(0)
    # Reorder weekdays
    weekdays_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(weekdays_order)
    fig = px.imshow(heatmap_data, labels=dict(x="Hour of Day", y="Weekday", color="Number of Missions"),
                    x=heatmap_data.columns, y=heatmap_data.index,
                    title='Einsätze nach Wochentag und Uhrzeit')
    st.plotly_chart(fig)


# pie chart displaying leadingDiagnosis distribution
st.subheader("Verteilung der Einsatzdiagnosen")
if 'leadingDiagnosis' in filtered_df.columns:
    diagnosis_counts = filtered_df['leadingDiagnosis'].value_counts().reset_index()
    diagnosis_counts.columns = ['leadingDiagnosis', 'count']
    
    # Group small categories into "Sonstige" after top 10
    if len(diagnosis_counts) > 10:
        # Sort by count descending
        diagnosis_counts = diagnosis_counts.sort_values('count', ascending=False)
        
        # Keep top 10
        top_10 = diagnosis_counts.head(10)
        
        # Sum the rest into "Sonstige"
        other_count = diagnosis_counts.iloc[10:]['count'].sum()
        
        # Create new dataframe with top 10 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame({'leadingDiagnosis': ['Sonstige'], 'count': [other_count]})
            diagnosis_counts = pd.concat([top_10, other_row], ignore_index=True)
    
    st.write(diagnosis_counts)

    fig = px.pie(diagnosis_counts, names='leadingDiagnosis', values='count', 
                title='Verteilung der Einsatzdiagnosen (Top 10 + Sonstige)',
                color_discrete_sequence=color)
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'leadingDiagnosis' nicht gefunden im Datensatz.")




# Check merging quality
st.subheader("Überprüfung der Datenverknüpfung (Index ↔ ETU)")
st.write("Aufgrund von mehrfach allamierungen existieren zu einzelnen NIDA-Protokollen mehrere ETÜ-Datensätze.")

etu = data_loading("ETÜ", limit=50000)

# merge df_index["protocolID"] with etu["AUFTRAGS_NR"]
st.write("Merge über NIDA-Protokoll['missionNumber'] und ETÜ['EINSATZ_NR']")

merged_df = pd.merge(filtered_df, etu, left_on="missionNumber", right_on="EINSATZ_NR", how="left")
st.write(merged_df)


total_filtered = len(filtered_df)
total_etu = len(etu)
total_merged = len(merged_df)
# Count unique missions that have ETU data (since multiple vehicles can be assigned to same mission)
matched = merged_df.dropna(subset=['EINSATZ_NR'])['missionNumber'].nunique()
missing_etu = total_filtered - matched

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Gesamt gefilterte Einsätze", total_filtered)
with col2:
    st.metric("ETU-Datensätze", total_etu)
with col3:
    st.metric("Verknüpfte Einsätze", matched)
with col4:
    st.metric("Fehlende ETU-Daten", missing_etu)

if missing_etu > 0:
    st.warning(f"{missing_etu} Einsätze konnten nicht mit ETU-Daten verknüpft werden.")

# Sankey diagram: Flow from ETU CEDUS_CODE to leadingDiagnosis
st.subheader("Sankey-Diagramm: Von ETU-Diagnose zu endgültiger Diagnose")

# Prepare data for Sankey (only rows with both CEDUS_CODE and leadingDiagnosis)
sankey_data = merged_df.dropna(subset=['CEDUS_CODE', 'leadingDiagnosis'])

if not sankey_data.empty:
    # Group by CEDUS_CODE and leadingDiagnosis to count flows
    flow_counts = sankey_data.groupby(['CEDUS_CODE', 'leadingDiagnosis']).size().reset_index(name='count')
    
    # Create nodes (unique CEDUS_CODE + unique leadingDiagnosis)
    cedus_codes = flow_counts['CEDUS_CODE'].unique()
    diagnoses = flow_counts['leadingDiagnosis'].unique()
    nodes = list(cedus_codes) + list(diagnoses)
    
    # Create node index mapping
    node_dict = {node: i for i, node in enumerate(nodes)}
    
    # Create links
    links = []
    for _, row in flow_counts.iterrows():
        source = node_dict[row['CEDUS_CODE']]
        target = node_dict[row['leadingDiagnosis']]
        value = row['count']
        links.append({'source': source, 'target': target, 'value': value})
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes
        ),
        link=dict(
            source=[link['source'] for link in links],
            target=[link['target'] for link in links],
            value=[link['value'] for link in links]
        )
    )])
    
    fig.update_layout(
        title_text="Datenfluss: ETU-Diagnose (CEDUS_CODE) → Endgültige Diagnose (leadingDiagnosis)",
        font_size=10
    )
    
    st.plotly_chart(fig)
    
    # Display flow counts table
    st.write("**Detaillierte Flüsse:**")
    st.dataframe(flow_counts.sort_values('count', ascending=False))
else:
    st.warning("Keine Daten mit sowohl ETU-Diagnose als auch endgültiger Diagnose verfügbar für das Sankey-Diagramm.")

# ===== ENHANCED TRANSPORT REQUIREMENT ANALYSIS =====
st.subheader("Erweiterte Transportbedarfsanalyse")


df_freetext = data_loading("Freetext", limit=500000)

# Explode the data array to get individual freetext entries
if not df_freetext.empty and 'data' in df_freetext.columns:
    df_freetext = df_freetext.explode('data').reset_index(drop=True)
    # Extract fields from the nested data structure
    freetext_expanded = pd.json_normalize(df_freetext['data'])
    # Combine with the original dataframe (excluding the data column and duplicate protocolId)
    df_freetext = pd.concat([df_freetext.drop(columns=['data', 'protocolId']), freetext_expanded], axis=1)

# Filter for anamnesis data (all transports for general analysis)
anamnesis_df = df_freetext[df_freetext['description'].str.contains('Anamnese', na=False, case=False)]

# Filter anamnesis data to only include protocols from the filtered Krankentransport missions (all transports)
anamnesis_df = anamnesis_df[anamnesis_df['protocolId'].isin(filtered_df['protocolId'])]

st.write(f"**Anamnesis-Daten: {len(anamnesis_df)} Protokolle gefunden für die gefilterten Einsätze**")
# Create KTW-specific anamnesis data for enhanced analysis (only KTW transports, excluding S-KTW and RTW)
if 'missionType' in filtered_df.columns:
    # Get protocolIds for KTW missions only (exclude S-KTW and RTW)
    ktw_protocols = filtered_df[
        filtered_df['missionType'].str.contains(r'\bktw\b', case=False, na=False, regex=True) & 
        ~filtered_df['missionType'].str.contains('s-ktw', case=False, na=False) &
        ~filtered_df['missionType'].str.contains(r'\brtw\b', case=False, na=False, regex=True)
    ]['protocolId']
    
    # Filter anamnesis data for KTW protocols only
    ktw_anamnesis_df = anamnesis_df[anamnesis_df['protocolId'].isin(ktw_protocols)]
    st.write(f"**KTW-Anamnesis-Daten: {len(ktw_anamnesis_df)} Protokolle für KTW-Transporte gefunden**")
else:
    ktw_anamnesis_df = anamnesis_df.copy()  # Fallback to all anamnesis data
    st.warning("Spalte 'missionType' nicht gefunden - KTW-Filter für Anamnese wird übersprungen.")

# 

if not ktw_anamnesis_df.empty:
    # Determine which column contains the text content
    text_column = 'content' if 'content' in ktw_anamnesis_df.columns else ('text' if 'text' in ktw_anamnesis_df.columns else None)
    
    if text_column is None:
        st.error("❌ Neither 'content' nor 'text' column found in KTW anamnesis data.")
        st.stop()
    
    # Use data helper to analyze freetext requirements
    enhanced_requirements = analyze_freetext_requirements(ktw_anamnesis_df)
    
    # Extract all categories
    ktw_anamnesis_df["medical_care"] = enhanced_requirements.apply(lambda x: x['medical_care'])
    ktw_anamnesis_df["ktw_equipment"] = enhanced_requirements.apply(lambda x: x['ktw_equipment'])
    ktw_anamnesis_df["infectious_disease"] = enhanced_requirements.apply(lambda x: x['infectious_disease'])
    ktw_anamnesis_df["crew_assessment"] = enhanced_requirements.apply(lambda x: x['crew_assessment'])
    ktw_anamnesis_df["krankenfahrt_mentioned"] = enhanced_requirements.apply(lambda x: x['krankenfahrt_mentioned'])
    
    # ===== DATA OVERVIEW STATISTICS =====
    st.markdown("### 📊 Datensatzübersicht")
    st.metric("Analysierte KTW-Protokolle", f"{len(ktw_anamnesis_df):,}")
    
    # ===== SPECIAL ANALYSIS: NO CATEGORIES =====
    none_all_three = ktw_anamnesis_df[
        (ktw_anamnesis_df["medical_care"].isna()) &
        (ktw_anamnesis_df["ktw_equipment"].isna()) &
        (ktw_anamnesis_df["infectious_disease"].isna())
    ]
    
    st.markdown("### 🚨 Kritisch: KTW-Transporte ohne Kategoriedokumentation")
    st.metric("Anzahl ohne Dokumentation", f"{len(none_all_three)} ({(len(none_all_three)/len(ktw_anamnesis_df)*100):.1f}%)")
    

    # ===== VISUALIZATIONS =====
    st.markdown("### 📈 Detaillierte Visualisierungen (KTW)")
    
    # Colors for charts
    chart_colors = {
        'indiziert': '#27ae60',
        'nicht_indiziert': '#e67e22',
        'logistische_soziale_paedagogische': "#cc2e70",
        'krankenfahrt': '#f39c12',
        'krankenfahrt_ausreichend': '#f39c12',
        'lokaler_schutz': '#3498db',
        None: '#95a5a6'
    }
    
    # Create all pie charts first
    # Medical Care Pie Chart
    medical_counts = ktw_anamnesis_df["medical_care"].value_counts(dropna=False)
    medical_labels = []
    for x, v in medical_counts.items():
        if pd.isna(x):
            medical_labels.append(f'keine Angaben ({v})')
        elif str(x) == 'indiziert':
            medical_labels.append(f'indiziert ({v})')
        elif str(x) == 'nicht_indiziert':
            medical_labels.append(f'nicht indiziert ({v})')
        elif str(x) == 'logistische_soziale_paedagogische':
            medical_labels.append(f'logistisch/sozial/pädagogisch ({v})')
        else:
            medical_labels.append(f'{x} ({v})')
    
    fig_medical = px.pie(values=medical_counts.values, names=medical_labels, 
                        title='Medizinische Betreuung notwendig (KTW)',
                        color_discrete_sequence=[chart_colors.get(x, '#95a5a6') for x in medical_counts.index])
    
    # KTW Equipment Pie Chart
    equipment_counts = ktw_anamnesis_df["ktw_equipment"].value_counts(dropna=False)
    equipment_labels = []
    for x, v in equipment_counts.items():
        if pd.isna(x):
            equipment_labels.append(f'keine Angaben ({v})')
        elif str(x) == 'indiziert':
            equipment_labels.append(f'indiziert ({v})')
        elif str(x) == 'nicht_indiziert':
            equipment_labels.append(f'nicht indiziert ({v})')
        elif str(x) == 'krankenfahrt':
            equipment_labels.append(f'Krankenfahrt ({v})')
        else:
            equipment_labels.append(f'{x} ({v})')
    
    fig_equipment = px.pie(values=equipment_counts.values, names=equipment_labels,
                          title='Besondere Ausstattung des KTW notwendig',
                          color_discrete_sequence=[chart_colors.get(x, '#95a5a6') for x in equipment_counts.index])
    
    # Infectious Disease Pie Chart
    infection_counts = ktw_anamnesis_df["infectious_disease"].value_counts(dropna=False)
    infection_labels = []
    for x, v in infection_counts.items():
        if pd.isna(x):
            infection_labels.append(f'keine Angaben ({v})')
        elif str(x) == 'indiziert':
            infection_labels.append(f'indiziert ({v})')
        elif str(x) == 'nicht_indiziert':
            infection_labels.append(f'nicht indiziert ({v})')
        elif str(x) == 'lokaler_schutz':
            infection_labels.append(f'lokaler Schutz ({v})')
        else:
            infection_labels.append(f'{x} ({v})')
    
    fig_infection = px.pie(values=infection_counts.values, names=infection_labels,
                          title='Hinweise auf eine schwere ansteckende Krankheit (KTW)',
                          color_discrete_sequence=[chart_colors.get(x, '#95a5a6') for x in infection_counts.index])
    
    # Crew Assessment Pie Chart
    crew_counts = ktw_anamnesis_df["crew_assessment"].value_counts(dropna=False)
    if crew_counts.sum() > 0:
        crew_labels = []
        for x, v in crew_counts.items():
            if pd.isna(x):
                crew_labels.append(f'keine Angaben ({v})')
            elif str(x) == 'indiziert':
                crew_labels.append(f'indiziert ({v})')
            elif str(x) == 'nicht_indiziert':
                crew_labels.append(f'nicht indiziert ({v})')
            elif str(x) == 'krankenfahrt_ausreichend':
                crew_labels.append(f'Krankenfahrt ausreichend ({v})')
            else:
                crew_labels.append(f'{x} ({v})')
        
        fig_crew = px.pie(values=crew_counts.values, names=crew_labels,
                         title='Einschätzung der Besatzung ob Krankentransport indiziert (KTW)',
                         color_discrete_sequence=[chart_colors.get(x, '#95a5a6') for x in crew_counts.index])
    
    # Arrange pie charts in a 2x2 grid
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_medical, use_container_width=True)
        st.plotly_chart(fig_equipment, use_container_width=True)
    with col2:
        st.plotly_chart(fig_infection, use_container_width=True)
        if crew_counts.sum() > 0:
            st.plotly_chart(fig_crew, use_container_width=True)
    
    # Documentation completeness
    st.markdown("### 📋 Dokumentationsvollständigkeit (KTW)")
    categories = ['Medizinische Betreuung', 'KTW Ausstattung', 'Ansteckende Krankheit']
    doc_rates = [
        ((len(ktw_anamnesis_df) - medical_counts.loc[pd.isna(medical_counts.index)].sum() if pd.isna(medical_counts.index).any() else 0)/len(ktw_anamnesis_df)*100),
        ((len(ktw_anamnesis_df) - equipment_counts.loc[pd.isna(equipment_counts.index)].sum() if pd.isna(equipment_counts.index).any() else 0)/len(ktw_anamnesis_df)*100),
        ((len(ktw_anamnesis_df) - infection_counts.loc[pd.isna(infection_counts.index)].sum() if pd.isna(infection_counts.index).any() else 0)/len(ktw_anamnesis_df)*100)
    ]
    
    fig_doc = px.bar(x=categories, y=doc_rates, 
                     title='Vollständigkeit der Klickstruktur (KTW)',
                     labels={'x': 'Kategorie', 'y': 'Prozent (%)'},
                     color_discrete_sequence=['#3498db'])
    fig_doc.update_traces(text=[f'{rate:.1f}%' for rate in doc_rates], textposition='outside')
    st.plotly_chart(fig_doc)
    
    # Categories needed per transport
    def count_needed_categories(row):
        count = 0
        if row['medical_care'] == 'indiziert':
            count += 1
        if row['ktw_equipment'] == 'indiziert':
            count += 1
        if row['infectious_disease'] == 'indiziert':
            count += 1
        return count
    
    ktw_anamnesis_df['categories_needed'] = ktw_anamnesis_df.apply(count_needed_categories, axis=1)
    categories_needed_dist = ktw_anamnesis_df['categories_needed'].value_counts().sort_index()
    
    fig_categories = px.bar(x=categories_needed_dist.index, y=categories_needed_dist.values,
                           title='Anzahl der besonderen Bedürfnisse pro KTW-Transport',
                           labels={'x': 'Anzahl Kategorien', 'y': 'Anzahl Transporte'},
                           color_discrete_sequence=['#2ecc71', '#f39c12', '#e67e22', '#e74c3c'])
    fig_categories.update_traces(text=categories_needed_dist.values, textposition='outside')
    st.plotly_chart(fig_categories)
    
    # Summary of special care requirements
    st.markdown("### 📋 Zusammenfassung der besonderen Pflegeanforderungen (KTW)")
    special_categories = ['Medizinische Betreuung', 'KTW Ausstattung', 'Ansteckende Krankheit']
    special_counts = [
        medical_counts.get('indiziert', 0),
        equipment_counts.get('indiziert', 0),
        infection_counts.get('indiziert', 0)
    ]
    
    fig_special = px.bar(x=special_categories, y=special_counts,
                        title='Anzahl der besonderen Bedürfnisse (Absolute Zahlen - KTW)',
                        labels={'x': 'Kategorie', 'y': 'Anzahl'},
                        color_discrete_sequence=['#e74c3c'])
    fig_special.update_traces(text=special_counts, textposition='outside')
    st.plotly_chart(fig_special)
    
else:
    st.warning("Keine KTW-Anamnesis-Daten für die Analyse verfügbar.")       