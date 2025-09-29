import streamlit as st
import pandas as pd
import plotly.express as px
import os
from data_loading import data_loading
from auth import check_authentication


# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()


# Load configuration from environment variables
DEFAULT_VEHICLES = os.getenv('DEFAULT_SKTW_VEHICLES').split(',')

VEHICLE_CONFIG = os.getenv('VEHICLE_CONFIG')
VEHICLE_SCHEDULES = {}

for config in VEHICLE_CONFIG.split(','):
    if ':' in config:
        vehicle, hours = config.split(':', 1)
        VEHICLE_SCHEDULES[vehicle.strip()] = int(hours.strip())

st.markdown("""
# 🚑 S-KTW ETÜ Analyse

Dieses Dashboard analysiert die ETÜ-Daten für S-KTWs (Spezial-Krankentransportwagen).
""")

etu_df = data_loading("ETÜ", limit=25000)

# Filter für Einsatzdatum Intervall
st.date_input("Einsatzdatum von-bis", 
              value=(pd.to_datetime("2025-01-01T00:00:00"), pd.Timestamp.today()),
              key="date_range")

# Get date range from session state
start_date, end_date = st.session_state["date_range"]

# Convert dates to datetime for comparison, handling timezone
start_dt = pd.to_datetime(start_date)
end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # Include entire end date

# Filter ETÜ data based on date range first
if 'EINSATZDATUM' in etu_df.columns:
    # Convert to datetime if needed
    etu_df['EINSATZDATUM'] = pd.to_datetime(etu_df['EINSATZDATUM'], errors='coerce')
    
    # Normalize dates to avoid timezone issues - compare only dates
    start_date_only = pd.to_datetime(start_date).date()
    end_date_only = pd.to_datetime(end_date).date()
    
    # Filter by date range using .dt.date() for comparison
    filtered_df = etu_df[
        (etu_df['EINSATZDATUM'].dt.date >= start_date_only) &
        (etu_df['EINSATZDATUM'].dt.date <= end_date_only)
    ].copy()
else:
    filtered_df = etu_df.copy()
    st.warning("EINSATZDATUM Spalte nicht gefunden - verwende alle Daten")

# Select S-KTW based on EINSATZMITTEL
if 'EINSATZMITTEL' in filtered_df.columns:
    available_vehicles = sorted(filtered_df['EINSATZMITTEL'].dropna().unique())
    selected_vehicles = st.multiselect(
        "S-KTW auswählen",
        options=available_vehicles,
        default=[v.strip() for v in DEFAULT_VEHICLES if v.strip() in available_vehicles]
    )
    
    if selected_vehicles:
        filtered_df = filtered_df[filtered_df['EINSATZMITTEL'].isin(selected_vehicles)]
else:
    st.warning("EINSATZMITTEL column not found")
    selected_vehicles = []

st.write(f"Gefilterte ETÜ-Daten: {len(filtered_df)} Einträge")


st.subheader("Auslastung der S-KTW Fahrzeuge")

# Define schedules (hours per week)
schedules = VEHICLE_SCHEDULES

# please display the auslastung like in the following Mon-Thu, Fri, Sat, Sun
weekday_groups = {
    'Monday': 'Mon-Thu',
    'Tuesday': 'Mon-Thu', 
    'Wednesday': 'Mon-Thu',
    'Thursday': 'Mon-Thu',
    'Friday': 'Fri',
    'Saturday': 'Sat',
    'Sunday': 'Sun'
}

# Calculate utilization for selected vehicles
if selected_vehicles and not filtered_df.empty:
    # Ensure we have the required columns
    required_cols = ['EINSATZBEGINN', 'EINSATZENDE', 'EINSATZMITTEL']
    if all(col in filtered_df.columns for col in required_cols):
        
        # Convert datetime columns if needed
        filtered_df = filtered_df.copy()
        filtered_df['EINSATZBEGINN'] = pd.to_datetime(filtered_df['EINSATZBEGINN'], errors='coerce')
        filtered_df['EINSATZENDE'] = pd.to_datetime(filtered_df['EINSATZENDE'], errors='coerce')
        
        # Remove rows with invalid datetime data
        valid_missions = filtered_df.dropna(subset=['EINSATZBEGINN', 'EINSATZENDE']).copy()
        
        if not valid_missions.empty:
            # Calculate mission duration in hours
            valid_missions['mission_duration_hours'] = (valid_missions['EINSATZENDE'] - valid_missions['EINSATZBEGINN']).dt.total_seconds() / 3600
            
            # Filter out negative or unrealistic durations (missions longer than 24 hours are likely errors)
            valid_missions = valid_missions[(valid_missions['mission_duration_hours'] > 0) & (valid_missions['mission_duration_hours'] <= 24)]
            
            # Add weekday information
            valid_missions['weekday'] = valid_missions['EINSATZBEGINN'].dt.day_name()
            valid_missions['weekday_group'] = valid_missions['weekday'].map(weekday_groups)
            
            # Calculate total available hours for the selected period
            date_range_days = (end_date - start_date).days + 1
            
            # Calculate utilization by vehicle and weekday group
            utilization_data = []
            
            for vehicle in selected_vehicles:
                vehicle_data = valid_missions[valid_missions['EINSATZMITTEL'] == vehicle]
                
                if not vehicle_data.empty:
                    # Get vehicle schedule (hours per week)
                    vehicle_short = vehicle
                    weekly_hours = schedules.get(vehicle_short, 168)  # Default to 24/7 if not found
                    
                    # Calculate total available hours for the period
                    total_available_hours = (weekly_hours / 7) * date_range_days
                    
                    # Calculate total mission hours
                    total_mission_hours = vehicle_data['mission_duration_hours'].sum()
                    
                    # Calculate utilization percentage
                    utilization_pct = (total_mission_hours / total_available_hours * 100) if total_available_hours > 0 else 0
                    
                    # Group by weekday for detailed analysis
                    weekday_stats = vehicle_data.groupby('weekday_group').agg({
                        'mission_duration_hours': 'sum',
                        'AUFTRAGS_NR': 'count'
                    }).round(2)
                    
                    utilization_data.append({
                        'vehicle': vehicle,
                        'total_available_hours': round(total_available_hours, 1),
                        'total_mission_hours': round(total_mission_hours, 1),
                        'utilization_pct': round(utilization_pct, 1),
                        'total_missions': len(vehicle_data),
                        'weekday_stats': weekday_stats
                    })
            
            if utilization_data:
                # Display overall utilization summary
                st.write("### Gesamtauslastung")
                summary_cols = st.columns(len(utilization_data))
                
                for i, data in enumerate(utilization_data):
                    with summary_cols[i]:
                        st.metric(
                            label=f"{data['vehicle']}",
                            value=f"{data['utilization_pct']}%",
                            delta=f"{data['total_mission_hours']}h / {data['total_available_hours']}h verfügbar"
                        )
                
                # Display detailed weekday breakdown
                st.write("### Wochentag-Auslastung")
                
                for data in utilization_data:
                    with st.expander(f"📊 {data['vehicle']} - Detailansicht"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Stunden nach Wochentag:**")
                            # Calculate available hours per weekday group
                            vehicle_short = data['vehicle']
                            weekly_hours = schedules.get(vehicle_short, 168)
                            
                            # Estimate hours per weekday group (rough approximation)
                            weekday_available = {
                                'Mon-Thu': (weekly_hours / 7) * 4 * (date_range_days / 7),  # 4 weekdays
                                'Fri': (weekly_hours / 7) * (date_range_days / 7),
                                'Sat': (weekly_hours / 7) * (date_range_days / 7),
                                'Sun': (weekly_hours / 7) * (date_range_days / 7)
                            }
                            
                            weekday_df = data['weekday_stats'].copy()
                            for weekday in ['Mon-Thu', 'Fri', 'Sat', 'Sun']:
                                if weekday in weekday_df.index:
                                    available = weekday_available.get(weekday, 0)
                                    used = weekday_df.loc[weekday, 'mission_duration_hours']
                                    pct = (used / available * 100) if available > 0 else 0
                                    weekday_df.loc[weekday, 'available_hours'] = round(available, 1)
                                    weekday_df.loc[weekday, 'utilization_pct'] = round(pct, 1)
                                else:
                                    weekday_df.loc[weekday, 'available_hours'] = round(weekday_available.get(weekday, 0), 1)
                                    weekday_df.loc[weekday, 'utilization_pct'] = 0
                                    weekday_df.loc[weekday, 'mission_duration_hours'] = 0
                                    weekday_df.loc[weekday, 'AUFTRAGS_NR'] = 0
                            
                            # Reorder columns
                            weekday_df = weekday_df[['mission_duration_hours', 'available_hours', 'utilization_pct', 'AUFTRAGS_NR']]
                            weekday_df.columns = ['Einsatz-Stunden', 'Verfügbare Stunden', 'Auslastung %', 'Anzahl Einsätze']
                            
                            st.dataframe(weekday_df.style.format({
                                'Einsatz-Stunden': '{:.1f}',
                                'Verfügbare Stunden': '{:.1f}', 
                                'Auslastung %': '{:.1f}%',
                                'Anzahl Einsätze': '{:.0f}'
                            }))
                        
                        with col2:
                            st.write("**Einsätze nach Stunde:**")
                            # Group missions by hour of day
                            valid_missions_vehicle = valid_missions[valid_missions['EINSATZMITTEL'] == data['vehicle']].copy()
                            valid_missions_vehicle['hour'] = valid_missions_vehicle['EINSATZBEGINN'].dt.hour
                            
                            hourly_missions = valid_missions_vehicle.groupby('hour').size().reset_index(name='count')
                            hourly_missions.columns = ['Stunde', 'Anzahl Einsätze']
                            
                            # Fill missing hours with 0
                            all_hours = pd.DataFrame({'Stunde': range(24)})
                            hourly_missions = all_hours.merge(hourly_missions, on='Stunde', how='left').fillna(0)
                            
                            st.bar_chart(hourly_missions.set_index('Stunde'))
            else:
                st.warning("Keine gültigen Einsatzdaten für die ausgewählten Fahrzeuge gefunden.")
        else:
            st.warning("Keine gültigen Einsatzdaten mit Beginn- und Endzeiten gefunden.")
    else:
        st.warning(f"Erforderliche Spalten fehlen: {', '.join([col for col in required_cols if col not in filtered_df.columns])}")
else:
    st.info("Wählen Sie Fahrzeuge aus, um die Auslastungsanalyse zu sehen.")




st.subheader("Einsatzstichworte")

# sankey diagramm SZENARIO_BEGINN, SZENARIO_ABSCHLUSS
if not filtered_df.empty and selected_vehicles:
    # Check for scenario columns
    if 'SZENARIO_BEGINN' in filtered_df.columns and 'SZENARIO_ABSCHLUSS' in filtered_df.columns:
        # Prepare data for Sankey diagram
        sankey_data = filtered_df[['SZENARIO_BEGINN', 'SZENARIO_ABSCHLUSS']].copy()
        sankey_data = sankey_data.dropna()  # Remove rows with missing scenario data
        if not sankey_data.empty:
            # Count transitions between scenarios
            transitions = sankey_data.groupby(['SZENARIO_BEGINN', 'SZENARIO_ABSCHLUSS']).size().reset_index(name='count')
            
            # Create unique list of all scenarios for node indices
            all_scenarios = list(set(transitions['SZENARIO_BEGINN'].tolist() + transitions['SZENARIO_ABSCHLUSS'].tolist()))
            scenario_to_index = {scenario: i for i, scenario in enumerate(all_scenarios)}
            
            # Prepare Sankey diagram data
            source_indices = [scenario_to_index[scenario] for scenario in transitions['SZENARIO_BEGINN']]
            target_indices = [scenario_to_index[scenario] for scenario in transitions['SZENARIO_ABSCHLUSS']]
            values = transitions['count'].tolist()
            
            # Create node labels with counts
            node_labels = []
            for scenario in all_scenarios:
                begin_count = transitions[transitions['SZENARIO_BEGINN'] == scenario]['count'].sum()
                end_count = transitions[transitions['SZENARIO_ABSCHLUSS'] == scenario]['count'].sum()
                total_count = begin_count + end_count
                node_labels.append(f"{scenario}<br>({total_count} Einsätze)")
            
            # Create Sankey diagram
            fig = dict(
                type='sankey',
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=node_labels,
                    color="lightblue"
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=values,
                    label=[f"{count} Einsätze" for count in values]
                )
            )
            
            layout = dict(
                title="Szenario-Veränderungen von Beginn zu Abschluss",
                font=dict(size=10)
            )
            
            # Sankey diagram removed - keeping only the transition table
            
            # Show summary statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Häufigste Einsatzstichworte (Beginn):**")
                begin_counts = sankey_data['SZENARIO_BEGINN'].value_counts().head(10)
                st.dataframe(begin_counts.to_frame('Anzahl'))
            
            with col2:
                st.write("**Häufigste Einsatzstichworte (Abschluss):**")
                end_counts = sankey_data['SZENARIO_ABSCHLUSS'].value_counts().head(10)
                st.dataframe(end_counts.to_frame('Anzahl'))
            
            # Show most common transitions
            st.write("**Häufigste Szenario-Übergänge:**")
            top_transitions = transitions.nlargest(10, 'count')
            top_transitions.columns = ['Von', 'Nach', 'Anzahl']
            st.dataframe(top_transitions)
            
        else:
            st.warning("Keine gültigen Szenario-Daten gefunden.")
    else:
        st.warning("SZENARIO_BEGINN oder SZENARIO_ABSCHLUSS Spalten nicht gefunden.")
else:
    st.info("Wählen Sie Fahrzeuge aus, um die Szenario-Analyse zu sehen.")



st.header("🚩 Geo-Mapping der Einsatzorte")

# Color selection for selected vehicles
if selected_vehicles:
    st.subheader("🎨 Fahrzeug-Farben zuweisen")
    st.write("Weisen Sie jedem ausgewählten Fahrzeug eine Farbe zu:")
    
    # Available colors
    available_colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    
    # Create color mapping dictionary
    color_map = {}
    color_columns = st.columns(len(selected_vehicles))
    
    for i, vehicle in enumerate(selected_vehicles):
        with color_columns[i]:
            default_color = available_colors[i % len(available_colors)]
            color_map[vehicle] = st.selectbox(
                f"Farbe für {vehicle}",
                options=available_colors,
                index=available_colors.index(default_color) if default_color in available_colors else 0,
                key=f"color_{vehicle}"
            )

# Geo-Mapping section using filtered data (only selected vehicles)
if not filtered_df.empty and selected_vehicles:
    # Check for coordinate columns
    if 'EO_X_KOORD' in filtered_df.columns and 'EO_Y_KOORD' in filtered_df.columns:
        # Remove rows with missing coordinates
        geo_valid_df = filtered_df.dropna(subset=['EO_X_KOORD', 'EO_Y_KOORD']).copy()

        if not geo_valid_df.empty:
            # Try to convert coordinates to lat/lon for mapping
            # Assuming UTM Zone 32N (common for Germany) - adjust zone if needed
            import pyproj

            try:
                # Define UTM to WGS84 transformer (Zone 32N)
                utm_to_wgs84 = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)

                # Convert coordinates
                lon_coords, lat_coords = utm_to_wgs84.transform(
                    geo_valid_df['EO_X_KOORD'].values,
                    geo_valid_df['EO_Y_KOORD'].values
                )

                geo_valid_df = geo_valid_df.copy()
                geo_valid_df['latitude'] = lat_coords
                geo_valid_df['longitude'] = lon_coords

                # Use folium for colored map based on vehicle type
                st.subheader("🗺️ Karte der Einsatzorte")
                st.write("Konvertierte Koordinaten aus UTM Zone 32N nach WGS84")

                try:
                    import folium
                    from streamlit_folium import st_folium

                    # Debug: Show unique vehicle names
                    unique_vehicles = geo_valid_df['EINSATZMITTEL'].unique()

                    # Calculate center of all points
                    center_lat = geo_valid_df['latitude'].mean()
                    center_lon = geo_valid_df['longitude'].mean()

                    # Create folium map
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

                    # Add markers for each mission location
                    for idx, row in geo_valid_df.iterrows():
                        vehicle = str(row['EINSATZMITTEL'])
                        color = color_map.get(vehicle, 'red')  # Use user-defined colors, default to red for unknown vehicles

                        # Create popup with protocol ID and other details
                        popup_text = f"""
                        <b>Fahrzeug:</b> {vehicle}<br>
                        <b>AUFTRAGS_NR:</b> {row.get('AUFTRAGS_NR')}<br>
                        <b>Datum</b> {row.get('EINSATZDATUM', 'N/A')}<br>
                        <b>Stichwort</b> {row.get('SZENARIO_BEGINN', 'N/A')}<br>
                        <b>Lat:</b> {row['latitude']:.4f}<br>
                        <b>Lon:</b> {row['longitude']:.4f}
                        """

                        folium.CircleMarker(
                            location=[row['latitude'], row['longitude']],
                            radius=5,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.9,
                            popup=popup_text,
                            tooltip=f"{vehicle} - {row.get('SZENARIO_BEGINN', 'N/A')}"
                        ).add_to(m)

                    # Create dynamic legend based on user color selections
                    legend_html = '''
                    <div style="position: fixed; 
                                bottom: 50px; left: 50px; width: 200px; height: auto; 
                                background-color: white; border: 2px solid grey; z-index: 9999; 
                                font-size: 12px; padding: 10px; border-radius: 5px; color: black;">
                        <div style="font-weight: bold; margin-bottom: 8px; color: black;">Fahrzeug-Farben:</div>
                    '''

                    for vehicle, color in color_map.items():
                        # Display vehicle name in legend
                        vehicle_short = vehicle
                        legend_html += f'''
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <div style="width: 12px; height: 12px; background-color: {color}; border-radius: 50%; margin-right: 8px;"></div>
                            <span style="color: black;">{vehicle_short}</span>
                        </div>
                        '''

                    legend_html += '</div>'
                    m.get_root().html.add_child(folium.Element(legend_html))

                    # Display the map - PREVENT RERUNS when zooming/panning
                    st_folium(m, width=700, height=500, returned_objects=[])
                    st.write(f"**Einsatzorte auf Karte:** {len(geo_valid_df)} Punkte angezeigt")

                except ImportError:
                    st.warning("folium oder streamlit-folium nicht verfügbar - verwende Streamlit-Karte ohne Farbcodierung")
                    # Fallback to st.map without colors
                    map_data = geo_valid_df[['latitude', 'longitude']].rename(
                        columns={'latitude': 'lat', 'longitude': 'lon'}
                    ).dropna()
                    if not map_data.empty:
                        st.map(map_data)
                        st.write(f"**Einsatzorte auf Karte:** {len(map_data)} Punkte angezeigt")
                    else:
                        st.warning("Keine gültigen Koordinaten für Kartenanzeige")

            except ImportError:
                st.warning("pyproj nicht verfügbar - verwende Scatter-Plot anstelle von Karte")
            except Exception as e:
                st.warning(f"Koordinatenkonvertierung fehlgeschlagen: {e} - verwende Scatter-Plot")
                st.write("Falls die Koordinaten bereits in WGS84 sind, können wir sie direkt verwenden.")

                # Fallback: check if coordinates might already be lat/lon
                # German lat/lon ranges: lat 47-55, lon 5-16
                if (geo_valid_df['EO_Y_KOORD'].between(47, 55).any() and
                    geo_valid_df['EO_X_KOORD'].between(5, 16).any()):
                    st.write("Koordinaten scheinen bereits in WGS84 zu sein - verwende st.map")
                    map_data = geo_valid_df[['EO_Y_KOORD', 'EO_X_KOORD']].rename(
                        columns={'EO_Y_KOORD': 'lat', 'EO_X_KOORD': 'lon'}
                    ).dropna()
                    st.map(map_data)

        else:
            st.warning("Keine gültigen Koordinaten in den gefilterten Daten gefunden")
    else:
        st.warning("EO_X_KOORD oder EO_Y_KOORD Spalten nicht gefunden")
else:
    if not selected_vehicles:
        st.warning("Bitte wählen Sie mindestens ein Fahrzeug aus")
    else:
        st.warning("Keine Daten für die Kartendarstellung verfügbar")