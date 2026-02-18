import streamlit as st
import pandas as pd
from data_loading import data_loading
from data_filtering import reduce_etu_eckpunktevereinbarung
import geopandas as gpd

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


# Parse German decimal comma coordinates to float
def _parse_coord(series):
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def _is_vehicle_available_at_time(availability_dict, alarm_datetime):
    """
    Check if a vehicle is within its scheduled working hours at the given time.
    
    Args:
        availability_dict: Dict with weekday keys (monday, tuesday, etc.) containing start/end times
        alarm_datetime: pandas Timestamp of when to check availability
    
    Returns:
        bool: True if vehicle should be working at this time, False otherwise
    """
    if pd.isna(alarm_datetime) or not isinstance(availability_dict, dict):
        return True  # If no availability data, assume always available
    
    # Get day of week (Monday=0, Sunday=6)
    weekday_num = alarm_datetime.weekday()
    weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    weekday_name = weekday_names[weekday_num]
    
    if weekday_name not in availability_dict:
        return True  # No schedule for this day, assume available
    
    day_schedule = availability_dict[weekday_name]
    if not isinstance(day_schedule, dict) or 'start' not in day_schedule or 'end' not in day_schedule:
        return True  # Invalid schedule, assume available
    
    try:
        start_time_str = str(day_schedule['start'])
        end_time_str = str(day_schedule['end'])
        
        # Parse times
        alarm_time = alarm_datetime.time()
        start_time = pd.to_datetime(start_time_str, format='%H:%M:%S').time()
        end_time = pd.to_datetime(end_time_str, format='%H:%M:%S').time()
        
        # Handle overnight shifts (e.g., start > end or end is 00:00:00)
        if end_time_str == '00:00:00':
            # Works until midnight - check if current time is >= start
            return alarm_time >= start_time
        elif start_time_str == '00:00:00':
            # Works from midnight - check if current time is <= end
            return alarm_time <= end_time
        elif start_time > end_time:
            # Overnight shift (e.g., 22:00 to 06:00)
            return alarm_time >= start_time or alarm_time <= end_time
        else:
            # Normal shift
            return start_time <= alarm_time <= end_time
    except Exception:
        return True  # If parsing fails, assume available


@st.cache_data(show_spinner=False)
def _load_etu():
    return data_loading("ETÜ")


@st.cache_data(show_spinner=False, hash_funcs={"builtins.function": lambda x: None})
def _prepare_geodata(df_etu_source, start_date_val, end_date_val):
    # Define _parse_coord locally to avoid scoping issues with cache (v2)
    def parse_coord_local(series):
        return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    
    df_reduced = reduce_etu_eckpunktevereinbarung(df_etu_source, start_date_val, end_date_val)

    wachbereiche_local = gpd.read_file("data/Wachbereiche_RD_SL-FL_2025.shp")
    if wachbereiche_local.crs is None:
        wachbereiche_local = wachbereiche_local.set_crs("EPSG:25832")

    x_coords = parse_coord_local(df_reduced["ZEIT_AN_E_X_KOORD"])
    y_coords = parse_coord_local(df_reduced["ZEIT_AN_E_Y_KOORD"])

    points_df_local = df_reduced.copy()
    points_df_local = points_df_local.assign(_x=x_coords, _y=y_coords).dropna(subset=["_x", "_y"])
    gdf_points_local = gpd.GeoDataFrame(
        points_df_local,
        geometry=gpd.points_from_xy(points_df_local["_x"], points_df_local["_y"]),
        crs=wachbereiche_local.crs,
    )

    if gdf_points_local.crs != wachbereiche_local.crs:
        gdf_points_local = gdf_points_local.to_crs(wachbereiche_local.crs)

    points_with_area_local = gpd.sjoin(
        gdf_points_local, wachbereiche_local, how="left", predicate="within"
    )
    df_inside_local = points_with_area_local[points_with_area_local["index_right"].notna()].copy()
    df_outside_local = points_with_area_local[points_with_area_local["index_right"].isna()].copy()
    df_inside_local["_wach_index"] = df_inside_local["index_right"]
    df_outside_local["_wach_index"] = df_outside_local["index_right"]
    df_inside_local = df_inside_local.drop(columns=["index_right"])
    df_outside_local = df_outside_local.drop(columns=["index_right"])

    return df_reduced, wachbereiche_local, df_inside_local, df_outside_local


df_etu = _load_etu()

# create data filter
start_date = st.date_input("Startdatum", value=pd.to_datetime("2025-01-01"))
end_date = st.date_input("Enddatum", value=pd.to_datetime("2025-12-31"))

# fahrzeuge based on ETÜ "EINSATZMITTEL", make this preselected
all_fahrzeuge = [
    "Ret SL 01-83-01",
    "Ret SL 01-83-02",
    "Ret SL 01-83-03",
    "Ret SL 01-83-04",
    "Ret SL 01-83-05",
    "Ret SL 01-83-06",
    "Ret SL 01-83-07",
    "Ret SL 01-83-08",
    "Ret SL 01-83-09",
    "Ret SL 01-83-10",
    "Ret SL 10-82-01",
    "Ret SL 10-83-01",
    "Ret SL 10-83-02",
    "Ret SL 10-85-01",
    "Ret SL 10-85-02",
    "Ret SL 10-85-03",
    "Ret SL 10-85-11",
    "Ret SL 11-83-01",
    "Ret SL 11-83-02",
    "Ret SL 11-83-03",
    "Ret SL 11-85-01",
    "Ret SL 11-85-10",
    "Ret SL 11-85-11",
    "Ret SL 12-83-01",
    "Ret SL 12-83-02",
    "Ret SL 12-83-05",
    "Ret SL 12-83-06",
    "Ret SL 12-85-11",
    "Ret SL 12-85-15",
    "Ret SL 13-82-01",
    "Ret SL 13-83-05",
    "Ret SL 20-82-01",
    "Ret SL 20-83-01",
    "Ret SL 20-83-02",
    "Ret SL 20-83-03",
    "Ret SL 20-85-11",
    "Ret SL 22-83-01",
    "Ret SL 22-85-01",
    "Ret SL 23-83-01",
    "Ret SL 30-83-01",
    "Ret SL 30-83-02",
    "Ret SL 40-83-01",
    "Ret SL 44-83-01",
    "Ret SL 44-83-02",
]

fahrzeuge = st.multiselect(
    "Eigene Fahrzeuge auswählen",
    options=all_fahrzeuge,
    default=all_fahrzeuge,
    placeholder="Wählen Sie ein oder mehrere Fahrzeuge...",
)



df_etu_reduced, wachbereiche, df_inside, df_outside = _prepare_geodata(df_etu, start_date, end_date)
if wachbereiche.crs is None:
    wachbereiche = wachbereiche.set_crs("EPSG:25832")


# Spatial join and inside/outside split are cached in _prepare_geodata


# Auswertung: Eigene vs Fremdfahrzeuge inside/outside je SZENARIO_BEGINN
import re

if "df_inside" not in locals() or "df_outside" not in locals():
    raise RuntimeError("df_inside/df_outside fehlt. Fuehre die Wachbereich-Analyse zuerst aus.")
if "fahrzeuge" not in locals():
    raise RuntimeError("fahrzeuge-Liste fehlt. Fuehre die Fahrzeugliste-Zelle zuerst aus.")

exclude_szenarios = {"DF", "G-AMT", "POL", "NIL", "ALARMUEB", "ALARMÜB"}

def _norm_szenario(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.upper()
    s = s.replace({"": "UNBEKANNT", "NAN": "UNBEKANNT", "NONE": "UNBEKANNT"})
    return s

def _fahrzeuge_mask(series: pd.Series, fahrzeuge_list: list) -> pd.Series:
    if not fahrzeuge_list:
        return pd.Series(False, index=series.index)
    pattern = "|".join(re.escape(v) for v in fahrzeuge_list)
    return series.astype(str).str.contains(pattern, regex=True, na=False)

def _counts_by_szenario(df: pd.DataFrame) -> pd.DataFrame:
    required = ["SZENARIO_BEGINN", "EINSATZMITTEL"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Fehlende Spalten: {missing}")
    szen = _norm_szenario(df["SZENARIO_BEGINN"])
    mask_keep = ~szen.isin(exclude_szenarios)
    szen = szen[mask_keep]
    own_mask = _fahrzeuge_mask(df.loc[mask_keep, "EINSATZMITTEL"], fahrzeuge)
    tmp = pd.DataFrame({"szenario": szen, "own": own_mask})
    counts = (
        tmp.groupby(["szenario", "own"])
        .size()
        .unstack(fill_value=0)
        .rename(columns={False: "external", True: "own"})
        .reset_index()
    )
    if "own" not in counts.columns:
        counts["own"] = 0
    if "external" not in counts.columns:
        counts["external"] = 0
    return counts

inside_counts = _counts_by_szenario(df_inside)
outside_counts = _counts_by_szenario(df_outside)

result = inside_counts.merge(outside_counts, on="szenario", how="outer", suffixes=("_inside", "_outside")).fillna(0)
result = result.rename(columns={
    "own_inside": "own_inside",
    "external_inside": "external_inside",
    "own_outside": "own_outside",
    "external_outside": "external_outside",
})

for col in ["own_inside", "external_inside", "own_outside", "external_outside"]:
    if col not in result.columns:
        result[col] = 0
    result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)

result["inside_total"] = result["own_inside"] + result["external_inside"]
result["outside_total"] = result["own_outside"] + result["external_outside"]
result["own_total"] = result["own_inside"] + result["own_outside"]
result["external_total"] = result["external_inside"] + result["external_outside"]
result["overall_total"] = result["inside_total"] + result["outside_total"]

result["own_outside_share_pct"] = (result["own_outside"] / result["own_total"] * 100).fillna(0).round(1)
result["external_inside_share_pct"] = (result["external_inside"] / result["inside_total"] * 100).fillna(0).round(1)

result = result.sort_values("overall_total", ascending=False).reset_index(drop=True)

st.subheader("Auswertung nach Szenario")
st.write(result)

# Map: inside/outside points colored by EINSATZMITTEL in list vs not in list
st.subheader("Kartenübersicht")

preselected_vehicles = [
    "Ret SL 44-83-01",
    "Ret SL 44-83-02",
    "Ret SL 12-83-01",
    "Ret SL 12-83-02",
    "Ret SL 12-83-05",
    "Ret SL 12-83-06",
    "Ret SL 13-82-01",
    "Ret SL 13-83-05",
]

col1, col2 = st.columns(2)

with col1:
    # Get unique scenarios from the data
    all_scenarios = pd.concat([
        pd.Series(df_inside["SZENARIO_BEGINN"].dropna()),
        pd.Series(df_outside["SZENARIO_BEGINN"].dropna())
    ])
    all_scenarios = _norm_szenario(all_scenarios)
    all_scenarios = sorted([s for s in all_scenarios.unique() if pd.notna(s)])
    
    default_scenarios = [
        "NOTF 01",
        "NOTF 11",
        "NOTF K",
        "AKUT 01",
        "FEU",
        "FEU BMA",
        "NOTF 11 REA",
        "TH",
    ]
    default_scenarios = [s for s in default_scenarios if s in all_scenarios]
    if not default_scenarios:
        default_scenarios = all_scenarios

    selected_scenarios = st.multiselect(
        "Szenarien filtern",
        options=all_scenarios,
        default=default_scenarios,
        placeholder="Alle Szenarien...",
    )

with col2:
    all_einsatzmittel = pd.concat([
        pd.Series(df_inside["EINSATZMITTEL"].dropna()),
        pd.Series(df_outside["EINSATZMITTEL"].dropna())
    ])
    all_einsatzmittel = sorted(all_einsatzmittel.astype(str).str.strip().unique())
    map_fahrzeuge = st.multiselect(
        "Fahrzeuge auf Karte",
        options=all_einsatzmittel,
        default=preselected_vehicles,
        placeholder="Fahrzeuge auswählen...",
    )

# Filter data by selected scenarios
def filter_by_scenarios(df, scenarios):
    if not scenarios:
        return df.iloc[0:0]
    szen = _norm_szenario(df["SZENARIO_BEGINN"])
    scenario_set = set(_norm_szenario(pd.Series(scenarios)).tolist())
    mask = szen.isin(scenario_set)
    return df[mask]


def _fahrzeuge_mask_exact(series, fahrzeuge_list):
    if not fahrzeuge_list:
        return pd.Series(False, index=series.index)
    fahrzeuge_set = {str(v).strip() for v in fahrzeuge_list if pd.notna(v)}
    return series.astype(str).str.strip().isin(fahrzeuge_set)

# Convert to WGS84 for folium display
# Ensure all GeoDataFrames have CRS set before conversion
if wachbereiche.crs is None:
    wachbereiche = wachbereiche.set_crs("EPSG:25832")
if df_inside.crs is None:
    df_inside = df_inside.set_crs("EPSG:25832")
if df_outside.crs is None:
    df_outside = df_outside.set_crs("EPSG:25832")

wachbereiche_map = wachbereiche.to_crs(epsg=4326)
df_inside_map = df_inside.to_crs(epsg=4326)
df_outside_map = df_outside.to_crs(epsg=4326)

df_inside_filtered = filter_by_scenarios(df_inside_map, selected_scenarios)
df_outside_filtered = filter_by_scenarios(df_outside_map, selected_scenarios)

# Apply vehicle filter (only show selected vehicles on the map)
inside_display_mask = _fahrzeuge_mask_exact(df_inside_filtered["EINSATZMITTEL"], map_fahrzeuge)
outside_display_mask = _fahrzeuge_mask_exact(df_outside_filtered["EINSATZMITTEL"], map_fahrzeuge)
df_inside_display = df_inside_filtered[inside_display_mask].copy()
df_outside_display = df_outside_filtered[outside_display_mask].copy()

# Color distinction uses "Eigene Fahrzeuge auswählen"
inside_own_mask = _fahrzeuge_mask_exact(df_inside_display["EINSATZMITTEL"], fahrzeuge)
outside_own_mask = _fahrzeuge_mask_exact(df_outside_display["EINSATZMITTEL"], fahrzeuge)
inside_own = df_inside_display[inside_own_mask].copy()
inside_external = df_inside_display[~inside_own_mask].copy()
outside_own = df_outside_display[outside_own_mask].copy()
outside_external = df_outside_display[~outside_own_mask].copy()

# Create folium map
import folium
from streamlit_folium import st_folium

# Get bounds from wachbereiche (WGS84)
bounds = wachbereiche_map.total_bounds
center_lon = (bounds[0] + bounds[2]) / 2
center_lat = (bounds[1] + bounds[3]) / 2

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=9,
    tiles="OpenStreetMap"
)

# Add fullscreen button
from folium.plugins import Fullscreen
Fullscreen().add_to(m)

# Add wachbereiche boundaries
for idx, row in wachbereiche_map.iterrows():
    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda x: {"color": "#333333", "weight": 1.5, "opacity": 0.7},
    ).add_to(m)

# Color mapping
colors = {
    "inside_own": "#1b9e77",      # green
    "inside_external": "#d95f02",  # orange
    "outside_own": "#7570b3",      # purple
    "outside_external": "#e7298a", # pink
}

legend_text = {
    "inside_own": "Inside: Eigene Fahrzeuge",
    "inside_external": "Inside: Fremdfahrzeuge",
    "outside_own": "Outside: Eigene Fahrzeuge",
    "outside_external": "Outside: Fremdfahrzeuge",
}

# Add points for each category
categories_to_plot = [
    ("inside_own", inside_own),
    ("inside_external", inside_external),
    ("outside_own", outside_own),
    ("outside_external", outside_external),
]

for category, gdf in categories_to_plot:
    color = colors[category]
    if not gdf.empty:
        for idx, row in gdf.iterrows():
            if pd.notna(row.geometry):
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5,
                    popup=f"{row.get('EINSATZMITTEL', 'N/A')} - {row.get('SZENARIO_BEGINN', 'N/A')}",
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=1,
                    opacity=0.8,
                ).add_to(m)

# Add legend
legend_html = '''
<div style="position: fixed;
     bottom: 30px; right: 30px; width: 260px; height: auto;
     background-color: rgba(255, 255, 255, 0.95);
     border: 1px solid #444; border-radius: 6px; z-index: 9999;
     font-size: 13px; color: #111; padding: 10px 12px;
     box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);">
<p style="margin: 0 0 8px 0; font-weight: 700; color: #111;">Legende</p>
'''
for category in ["inside_own", "inside_external", "outside_own", "outside_external"]:
    legend_html += (
        f'<p style="margin: 6px 0; color: #111;">'
        f'<span style="background-color: {colors[category]}; width: 14px; height: 14px; '
        f'display: inline-block; margin-right: 6px; border: 1px solid #333;"></span>'
        f'{legend_text[category]}</p>'
    )
legend_html += '</div>'
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width=1200, height=600, key="map", returned_objects=[])


st.subheader("Hilfsfrist-Analyse RTW-Verfuegbarkeit")

df_rtm = data_loading("RTM_Vorhaltung")

def _find_col(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None

def _norm_station(val):
    text = str(val).lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = text.replace("wachbereich", " ")
    text = text.replace("rd", " ")
    text = text.replace("2025", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

if df_rtm.empty:
    st.warning("Keine Fahrzeugdaten gefunden. Pruefe RTM_Vorhaltung.")
else:
    col_vehicle = _find_col(df_rtm, ["vehicle", "vehicle_identifier", "fahrzeug", "einsatzmittel", "rtm"])
    col_vehicle_type = _find_col(df_rtm, ["vehicle_type", "type", "fahrzeugtyp"])
    col_station = _find_col(df_rtm, ["station", "wache", "standort"])
    col_start = _find_col(df_rtm, ["start_date", "start", "valid_from"])
    col_end = _find_col(df_rtm, ["end_date", "end", "valid_to"])

    missing_cols = [
        name
        for name, col in [
            ("vehicle", col_vehicle),
            ("vehicle_type", col_vehicle_type),
            ("station", col_station),
        ]
        if col is None
    ]
    if missing_cols:
        st.warning(f"Fehlende Spalten in RTM_Vorhaltung: {missing_cols}")
    else:
        df_rtm_local = df_rtm.copy()
        df_rtm_local[col_vehicle_type] = df_rtm_local[col_vehicle_type].astype(str).str.upper()
        df_rtm_local = df_rtm_local[df_rtm_local[col_vehicle_type].str.contains("RTW", na=False)]

        if col_start and col_end:
            df_rtm_local[col_start] = pd.to_datetime(df_rtm_local[col_start], errors="coerce")
            df_rtm_local[col_end] = pd.to_datetime(df_rtm_local[col_end], errors="coerce")

        df_rtm_local["_station_key"] = df_rtm_local[col_station].apply(_norm_station)
        
        # Normalize vehicle names to match outside mission format
        def _normalize_vehicle_name(v):
            v_str = str(v).strip()
            # If it doesn't already start with Ret, add the prefix based on first digit
            if not v_str.upper().startswith('RET'):
                # Extract region number and add Ret prefix
                # e.g., "12-83-01" -> "Ret SL 12-83-01"
                # e.g., "60-83-01" -> "Ret NF 60-83-01"
                parts = v_str.split('-')
                if len(parts) >= 1:
                    first_num = parts[0]
                    # Map based on first digit: 01-44 = SL, 60+ = NF, 90+ = RD, etc.
                    if first_num.startswith('9'):
                        prefix = "Ret RD"
                    elif first_num.startswith('6'):
                        prefix = "Ret NF"
                    else:
                        prefix = "Ret SL"
                    v_str = f"{prefix} {v_str}"
            return v_str
        
        df_rtm_local[col_vehicle] = df_rtm_local[col_vehicle].apply(_normalize_vehicle_name)
        
        # Build station_to_vehicles with availability data (deduplicated by vehicle name)
        # Structure: {station_key: [{"vehicle": "Ret SL 12-83-01", "availability": {...}}, ...]}
        station_to_vehicles = {}
        for station_key, group in df_rtm_local.groupby("_station_key"):
            vehicles_seen = {}  # Track unique vehicles
            for _, row in group.iterrows():
                vehicle_name = str(row[col_vehicle]).strip()
                # Only add if not seen before (takes first occurrence)
                if vehicle_name not in vehicles_seen:
                    availability = row.get('availability', {})
                    vehicles_seen[vehicle_name] = {
                        "vehicle": vehicle_name,
                        "availability": availability,
                    }
            station_to_vehicles[station_key] = list(vehicles_seen.values())

        join_col = None
        for candidate in ["NAME", "Name", "name"]:
            if candidate in df_inside.columns:
                join_col = candidate
                break
        if join_col is None:
            name_like_cols = [
                col for col in df_inside.columns
                if "name" in col.lower() and col in wachbereiche.columns
            ]
            if name_like_cols:
                join_col = name_like_cols[0]

        df_inside_local = df_inside.copy()

        if join_col is None and "_wach_index" in df_inside_local.columns:
            wb_name_col = None
            for candidate in ["NAME", "Name", "name"]:
                if candidate in wachbereiche.columns:
                    wb_name_col = candidate
                    break
            if wb_name_col is None:
                name_like_cols = [
                    col for col in wachbereiche.columns
                    if "name" in col.lower()
                ]
                if name_like_cols:
                    wb_name_col = name_like_cols[0]
            if wb_name_col is not None:
                wb_names = wachbereiche[wb_name_col]
                df_inside_local["_station_key"] = df_inside_local["_wach_index"].map(wb_names).apply(_norm_station)
        elif join_col is not None:
            df_inside_local["_station_key"] = df_inside_local[join_col].apply(_norm_station)

        if "_station_key" not in df_inside_local.columns:
            st.warning(
                "Wachbereich-Name nicht gefunden. Bitte pruefe Spalten in df_inside und Shapefile."
            )
        else:

            for col in ["ALARMIERT", "ZEIT_AN_E", "ZEIT_AB_D_1", "EINSATZBEGINN", "ZEIT_AB_Z"]:
                if col in df_inside_local.columns:
                    df_inside_local[col] = pd.to_datetime(df_inside_local[col], errors="coerce")

            if "ZEIT_AB_D_1" in df_inside_local.columns:
                alarm_end_col = "ZEIT_AB_D_1"
            elif "ZEIT_AB_D" in df_inside_local.columns:
                alarm_end_col = "ZEIT_AB_D"
            else:
                alarm_end_col = "ZEIT_AN_E"

            df_inside_local["_alarm_start"] = df_inside_local["ALARMIERT"]
            df_inside_local["_alarm_end"] = df_inside_local[alarm_end_col]

            df_inside_local["_hilfsfrist_min"] = (
                df_inside_local["ZEIT_AN_E"] - df_inside_local["ALARMIERT"]
            ).dt.total_seconds() / 60
            late_mask = df_inside_local["_hilfsfrist_min"] > 12
            late_df = df_inside_local[late_mask].copy()

            df_outside_local = df_outside.copy()
            for col in ["EINSATZBEGINN", "ZEIT_AB_Z"]:
                if col in df_outside_local.columns:
                    df_outside_local[col] = pd.to_datetime(df_outside_local[col], errors="coerce")

            if "EINSATZMITTELTYP" in df_outside_local.columns:
                outside_rtw = df_outside_local[
                    df_outside_local["EINSATZMITTELTYP"].astype(str).str.contains("RTW", na=False)
                ].copy()
            else:
                outside_rtw = df_outside_local.copy()

            # Prepare outside RTW data with station keys and time conversion
            df_outside_rtw = df_outside_local.copy()
            if "EINSATZMITTELTYP" in df_outside_rtw.columns:
                df_outside_rtw = df_outside_rtw[
                    df_outside_rtw["EINSATZMITTELTYP"].astype(str).str.contains("RTW", na=False)
                ]
            for col in ["EINSATZBEGINN", "ZEIT_AB_Z"]:
                if col in df_outside_rtw.columns:
                    df_outside_rtw[col] = pd.to_datetime(df_outside_rtw[col], errors="coerce")
            
            # Add station keys to outside RTW data
            if "_station_key" not in df_outside_rtw.columns:
                if "EINSATZMITTEL" in df_outside_rtw.columns:
                    # For outside missions, we need to infer station or use vehicle mapping
                    df_outside_rtw["_station_key"] = df_outside_rtw["EINSATZMITTEL"].apply(
                        lambda x: x if isinstance(x, str) else str(x)
                    )
            
            # Improved busy check: ALL station vehicles must be busy OR all available-by-schedule vehicles must be busy
            # With at least one outside in either case
            def _check_rtw_busy_outside(row):
                station_vehicles_info = station_to_vehicles.get(row.get("_station_key"), [])
                if not station_vehicles_info:
                    return False
                
                alarm_time = row.get("ALARMIERT")  # Check at exact alarm moment
                
                if pd.isna(alarm_time):
                    return False
                
                # Get all station vehicles (ensure unique)
                all_station_vehicles = list(set([vinfo["vehicle"] for vinfo in station_vehicles_info]))
                
                # Filter to only vehicles that should be working at this time
                available_vehicles = []
                for vinfo in station_vehicles_info:
                    vehicle_name = vinfo["vehicle"]
                    availability = vinfo.get("availability", {})
                    if _is_vehicle_available_at_time(availability, alarm_time):
                        available_vehicles.append(vehicle_name)
                
                # Track which vehicles are busy (inside or outside) at alarm moment
                busy_vehicles = set()
                busy_outside_vehicles = set()
                
                # Check outside missions at alarm moment (for ALL station vehicles, not just scheduled)
                # Use EINSATZBEGINN and EINSATZENDE if available, otherwise ZEIT_AB_Z
                end_col_outside = "EINSATZENDE" if "EINSATZENDE" in df_outside_rtw.columns else "ZEIT_AB_Z"
                
                outside_busy = df_outside_rtw[
                    df_outside_rtw["EINSATZMITTEL"].astype(str).str.strip().isin(all_station_vehicles) &
                    df_outside_rtw["EINSATZBEGINN"].notna() &
                    df_outside_rtw[end_col_outside].notna() &
                    (df_outside_rtw["EINSATZBEGINN"] <= alarm_time) &
                    (df_outside_rtw[end_col_outside] >= alarm_time)
                ]
                
                for vehicle in outside_busy["EINSATZMITTEL"].astype(str).str.strip().unique():
                    busy_vehicles.add(vehicle)
                    busy_outside_vehicles.add(vehicle)
                
                # Check inside missions at alarm moment (for ALL station vehicles)
                # Use EINSATZBEGINN and EINSATZENDE if available
                if "EINSATZBEGINN" in df_inside_local.columns and "EINSATZENDE" in df_inside_local.columns:
                    inside_busy = df_inside_local[
                        df_inside_local["EINSATZMITTEL"].astype(str).str.strip().isin(all_station_vehicles) &
                        df_inside_local["EINSATZBEGINN"].notna() &
                        df_inside_local["EINSATZENDE"].notna() &
                        (df_inside_local["EINSATZBEGINN"] <= alarm_time) &
                        (df_inside_local["EINSATZENDE"] >= alarm_time)
                    ]
                    
                    for vehicle in inside_busy["EINSATZMITTEL"].astype(str).str.strip().unique():
                        busy_vehicles.add(vehicle)
                
                # Check TWO conditions:
                # 1. Are ALL station vehicles busy? (regardless of schedule)
                all_vehicles_busy = len(busy_vehicles) == len(all_station_vehicles)
                
                # 2. Are ALL vehicles that should be working busy?
                all_available_busy = len(available_vehicles) > 0 and len(busy_vehicles.intersection(set(available_vehicles))) == len(available_vehicles)
                
                # Check if at least one is outside
                at_least_one_outside = len(busy_outside_vehicles) > 0
                
                # Count as problem if (all vehicles busy OR all available vehicles busy) AND at least one outside
                return (all_vehicles_busy or all_available_busy) and at_least_one_outside
            
            # DEBUG: Show step-by-step filtering
            with st.expander("🔍 Debug: Hilfsfrist-Analyse", expanded=False):
                st.write("**Schritt 1: Datenvorbereitung**")
                st.write(f"- Inside Missionen gesamt: {len(df_inside_local)}")
                
                st.write("**Schritt 2: Verspätete Missionen (> 12 min)**")
                st.write(f"- Verspätet gesamt: {len(late_df)}")
                if len(late_df) > 0:
                    st.write(f"- Hilfsfrist min: {late_df['_hilfsfrist_min'].min():.1f} - {late_df['_hilfsfrist_min'].max():.1f} min")
                    if "EINSATZENDE" in late_df.columns:
                        st.write(f"- Mit EINSATZENDE: {late_df['EINSATZENDE'].notna().sum()}/{len(late_df)}")
                    if "EINSATZBEGINN" in late_df.columns:
                        st.write(f"- Mit EINSATZBEGINN: {late_df['EINSATZBEGINN'].notna().sum()}/{len(late_df)}")
                    st.write("**Beispiele verspätete Missionen:**")
                    st.dataframe(late_df[["EINSATZMITTEL", "_station_key", "ALARMIERT", "ZEIT_AN_E", "_hilfsfrist_min"]].head(10))
                else:
                    st.write("⚠️ KEINE verspäteten Missionen gefunden!")
                
                st.write("**Schritt 3: Station-zu-Fahrzeugen Mapping**")
                st.write(f"- Stationen mit RTW-Zuordnung: {len(station_to_vehicles)}")
                for station_key, vehicles_info in list(station_to_vehicles.items())[:5]:
                    vehicle_names = [v["vehicle"] for v in vehicles_info]
                    st.write(f"  - {station_key}: {vehicle_names}")
                if len(station_to_vehicles) > 5:
                    st.write(f"  ... und {len(station_to_vehicles) - 5} weitere")
                
                st.write("**Schritt 4: Verspätete Missionen - Station Key Zuordnung**")
                late_with_station = late_df[late_df["_station_key"].notna()]
                st.write(f"- Verspätete mit Station Key: {len(late_with_station)}")
                if len(late_with_station) > 0:
                    st.write(f"- Einzigartige Stationen: {late_with_station['_station_key'].nunique()}")
                    st.write(f"- Station Keys: {late_with_station['_station_key'].unique()[:10].tolist()}")
                else:
                    st.write("⚠️ Keine verspäteten Missionen mit Station Keys!")
                
                st.write("**Schritt 5: Verspätete Missionen - Fahrzeug-Zuordnung check**")
                late_with_vehicles = late_df[
                    late_df["_station_key"].isna() == False
                ].copy()
                if len(late_with_vehicles) > 0:
                    late_with_vehicles["has_station_vehicles"] = late_with_vehicles["_station_key"].apply(
                        lambda x: x in station_to_vehicles and len(station_to_vehicles.get(x, [])) > 0
                    )
                    st.write(f"- Mit matched Fahrzeugen: {late_with_vehicles['has_station_vehicles'].sum()}")
                    st.write(f"- Ohne matched Fahrzeuge: {(~late_with_vehicles['has_station_vehicles']).sum()}")
                    
                    if (~late_with_vehicles['has_station_vehicles']).sum() > 0:
                        st.write("**Stationen OHNE Fahrzeuge-Match:**")
                        unmatched_stations = late_with_vehicles[~late_with_vehicles['has_station_vehicles']]["_station_key"].unique()
                        st.write(unmatched_stations[:10].tolist())
                else:
                    st.write("⚠️ Keine verspäteten Missionen mit gültigen Station Keys!")
                
                st.write("**Schritt 6: Außeneinsätze mit RTW**")
                st.write(f"- Außeneinsätze gesamt: {len(df_outside_rtw)}")
                st.write(f"- Mit Fahrzeugtyp: {df_outside_rtw['EINSATZMITTEL'].notna().sum()}")
                st.write(f"- Mit Start-Zeit: {df_outside_rtw['EINSATZBEGINN'].notna().sum()}")
                if "EINSATZENDE" in df_outside_rtw.columns:
                    st.write(f"- Mit End-Zeit (EINSATZENDE): {df_outside_rtw['EINSATZENDE'].notna().sum()}")
                st.write(f"- Mit End-Zeit (ZEIT_AB_Z): {df_outside_rtw['ZEIT_AB_Z'].notna().sum()}")
                end_col_check = "EINSATZENDE" if "EINSATZENDE" in df_outside_rtw.columns else "ZEIT_AB_Z"
                st.write(f"- Using end column: **{end_col_check}**")
                st.write(f"- Mit vollen Zeitdaten: {(df_outside_rtw['EINSATZBEGINN'].notna() & df_outside_rtw[end_col_check].notna()).sum()}")
                
                if len(df_outside_rtw) > 0:
                    st.write("**Beispiele Außeneinsätze:**")
                    st.dataframe(df_outside_rtw[["EINSATZMITTEL", "EINSATZBEGINN", "ZEIT_AB_Z"]].head(10))
                else:
                    st.write("⚠️ Keine Außeneinsätze gefunden!")
                
                st.write("**Schritt 7: Fahrzeug-Namen Vergleich**")
                if len(late_with_vehicles) > 0 and len(df_outside_rtw) > 0:
                    outside_vehicles_unique = set(df_outside_rtw["EINSATZMITTEL"].astype(str).str.strip().dropna().unique())
                    inside_station_vehicles = set()
                    for vehicles_info_list in station_to_vehicles.values():
                        for vinfo in vehicles_info_list:
                            inside_station_vehicles.add(vinfo["vehicle"])
                    
                    st.write(f"- Einzigartige Fahrzeuge im Außen-Datensatz: {len(outside_vehicles_unique)}")
                    st.write(f"  Beispiele: {list(outside_vehicles_unique)[:5]}")
                    st.write(f"- Einzigartige Fahrzeuge im RTM (Stationen): {len(inside_station_vehicles)}")
                    st.write(f"  Beispiele: {list(inside_station_vehicles)[:5]}")
                    
                    matching = outside_vehicles_unique.intersection(inside_station_vehicles)
                    st.write(f"- **Übereinstimmende Fahrzeuge: {len(matching)}**")
                    if matching:
                        st.write(f"  {list(matching)[:10]}")
                    else:
                        st.write("⚠️ KEINE übereinstimmenden Fahrzeuge!")
                
                st.write("**Schritt 8: Neue Logik - ALLE Fahrzeuge ODER alle verfügbaren beschäftigt**")
                st.write("*(Prüft: alle Station-Fahrzeuge beschäftigt ODER alle nach Arbeitszeit verfügbaren beschäftigt)*")
                
                # Detailed availability analysis
                st.write("---")
                st.write("**🔬 Detaillierte Verfügbarkeits-Analyse**")
                
                availability_categories = {
                    "keine_station_zuordnung": [],  # No station mapping found
                    "keine_verfuegbar": [],  # No vehicles should be working at alarm time
                    "alle_verfuegbar_frei": [],  # All available vehicles are free
                    "teilweise_beschaeftigt": [],  # Some available vehicles busy
                    "alle_beschaeftigt_innen": [],  # All available busy but all inside
                    "alle_beschaeftigt_aussen": [],  # All available busy, at least one outside ✓
                }
                
                overlap_details = []
                no_match_details = []
                
                for idx, late_row in late_df.iterrows():
                    station_key = late_row.get("_station_key")
                    station_vehicles_info = station_to_vehicles.get(station_key, [])
                    alarm_time = late_row.get("ALARMIERT")
                    alarmiert = late_row.get("ALARMIERT")
                    einsatz_nr = late_row.get("EINSATZ_NR")
                    
                    if not station_vehicles_info or pd.isna(alarm_time):
                        # No station mapping found
                        availability_categories["keine_station_zuordnung"].append({
                            "EINSATZ_NR": einsatz_nr,
                            "ALARMIERT": alarmiert,
                            "station": station_key if station_key else "Keine",
                            "reason": "Keine Station-Zuordnung" if not station_vehicles_info else "Kein ALARMIERT"
                        })
                        continue
                    
                    # Get all vehicles (ensure unique)
                    all_station_vehicles = list(set([vinfo["vehicle"] for vinfo in station_vehicles_info]))
                    
                    # Filter to vehicles that should be working at alarm time
                    available_vehicle_names = []
                    unavailable_vehicle_names = []
                    for vinfo in station_vehicles_info:
                        vehicle_name = vinfo["vehicle"]
                        if _is_vehicle_available_at_time(vinfo.get("availability", {}), alarm_time):
                            available_vehicle_names.append(vehicle_name)
                        else:
                            unavailable_vehicle_names.append(vehicle_name)
                    
                    # Track busy vehicles
                    busy_vehicles = set()
                    busy_outside_vehicles = set()
                    busy_inside_vehicles = set()
                    
                    # Check outside missions at exact alarm moment (ALL station vehicles)
                    end_col = "EINSATZENDE" if "EINSATZENDE" in df_outside_rtw.columns else "ZEIT_AB_Z"
                    outside_at_alarm = df_outside_rtw[
                        df_outside_rtw["EINSATZMITTEL"].astype(str).str.strip().isin(all_station_vehicles) &
                        df_outside_rtw["EINSATZBEGINN"].notna() &
                        df_outside_rtw[end_col].notna() &
                        (df_outside_rtw["EINSATZBEGINN"] <= alarm_time) &
                        (df_outside_rtw[end_col] >= alarm_time)
                    ]
                    
                    for vehicle in outside_at_alarm["EINSATZMITTEL"].astype(str).str.strip().unique():
                        busy_vehicles.add(vehicle)
                        busy_outside_vehicles.add(vehicle)
                    
                    # Check inside missions at exact alarm moment (ALL station vehicles)
                    if "EINSATZBEGINN" in df_inside_local.columns and "EINSATZENDE" in df_inside_local.columns:
                        inside_at_alarm = df_inside_local[
                            df_inside_local["EINSATZMITTEL"].astype(str).str.strip().isin(all_station_vehicles) &
                            df_inside_local["EINSATZBEGINN"].notna() &
                            df_inside_local["EINSATZENDE"].notna() &
                            (df_inside_local["EINSATZBEGINN"] <= alarm_time) &
                            (df_inside_local["EINSATZENDE"] >= alarm_time)
                        ]
                        
                        for vehicle in inside_at_alarm["EINSATZMITTEL"].astype(str).str.strip().unique():
                            if vehicle not in busy_outside_vehicles:
                                busy_vehicles.add(vehicle)
                                busy_inside_vehicles.add(vehicle)
                    
                    # Categorize this case
                    available_busy = busy_vehicles.intersection(set(available_vehicle_names))
                    
                    case_info = {
                        "EINSATZ_NR": einsatz_nr,
                        "ALARMIERT": alarmiert,
                        "station": station_key,
                        "total_vehicles": len(all_station_vehicles),
                        "available_vehicles": len(available_vehicle_names),
                        "unavailable_vehicles": len(unavailable_vehicle_names),
                        "busy_total": len(busy_vehicles),
                        "busy_outside": len(busy_outside_vehicles),
                        "busy_inside": len(busy_inside_vehicles),
                        "available_busy_count": len(available_busy),
                    }
                    
                    if len(available_vehicle_names) == 0:
                        availability_categories["keine_verfuegbar"].append(case_info)
                    elif len(available_busy) == 0:
                        availability_categories["alle_verfuegbar_frei"].append(case_info)
                    elif len(available_busy) < len(available_vehicle_names):
                        availability_categories["teilweise_beschaeftigt"].append(case_info)
                    elif len(busy_outside_vehicles) == 0:
                        availability_categories["alle_beschaeftigt_innen"].append(case_info)
                    else:
                        availability_categories["alle_beschaeftigt_aussen"].append(case_info)
                    
                    # Check both conditions
                    all_vehicles_busy = len(busy_vehicles) == len(all_station_vehicles)
                    all_available_busy = len(available_vehicle_names) > 0 and len(available_busy) == len(available_vehicle_names)
                    at_least_one_outside = len(busy_outside_vehicles) > 0
                    
                    if (all_vehicles_busy or all_available_busy) and at_least_one_outside:
                        overlap_details.append({
                            "EINSATZ_NR": einsatz_nr,
                            "ALARMIERT": alarmiert,
                            "station": station_key,
                            "total_vehicles": len(all_station_vehicles),
                            "available_vehicles": len(available_vehicle_names),
                            "busy_total": len(busy_vehicles),
                            "busy_outside": len(busy_outside_vehicles),
                            "busy_inside": len(busy_inside_vehicles),
                            "all_busy": all_vehicles_busy,
                            "all_avail_busy": all_available_busy,
                        })
                    else:
                        if len(no_match_details) < 10:
                            no_match_details.append({
                                "EINSATZ_NR": einsatz_nr,
                                "ALARMIERT": alarmiert,
                                "station": station_key,
                                "total_vehicles": len(all_station_vehicles),
                                "available_vehicles": len(available_vehicle_names),
                                "busy_count": len(busy_vehicles),
                                "available_busy": len(available_busy),
                                "all_vehicles_busy": all_vehicles_busy,
                                "all_available_busy": all_available_busy,
                                "reason": "Keine außen" if not at_least_one_outside else "Nicht alle beschäftigt"
                            })
                
                # Display category statistics
                st.write("---")
                st.write("**📊 Gesamte Missionen - Übersicht**")
                
                ontime_count = len(df_inside_local) - len(late_df)
                col1a, col2a, col3a = st.columns(3)
                
                with col1a:
                    st.metric("📍 Gesamt Inside-Missionen", 
                             len(df_inside_local),
                             help="Alle Missionen im Wachbereich (inside)")
                
                with col2a:
                    st.metric("✅ Hilfsfrist OK (≤12 min)", 
                             ontime_count,
                             help=f"{(ontime_count/len(df_inside_local)*100):.1f}% der Missionen")
                
                with col3a:
                    st.metric("⚠️ Verspätet (>12 min)", 
                             len(late_df),
                             delta=f"{(len(late_df)/len(df_inside_local)*100):.1f}%",
                             help="Missionen über der 12-Minuten-Schwelle")
                
                st.write("---")
                st.write("**Kategorisierung aller verspäteten Einsätze:**")
                st.write(f"*(Von den {len(late_df)} verspäteten Missionen)*")
                
                col1, col2, col3 = st.columns(3)
                
                # Calculate totals - 5 with-data categories + 1 without
                categorized_with_data = (len(availability_categories["keine_verfuegbar"]) +
                                        len(availability_categories["alle_verfuegbar_frei"]) +
                                        len(availability_categories["teilweise_beschaeftigt"]) +
                                        len(availability_categories["alle_beschaeftigt_innen"]) +
                                        len(availability_categories["alle_beschaeftigt_aussen"]))
                uncategorized_no_data = len(availability_categories["keine_station_zuordnung"])
                
                with col1:
                    st.metric("❌ Keine Fahrzeuge verfügbar", 
                             len(availability_categories["keine_verfuegbar"]),
                             help="Alle Fahrzeuge außerhalb ihrer Arbeitszeit")
                    st.metric("✅ Alle verfügbar frei", 
                             len(availability_categories["alle_verfuegbar_frei"]),
                             help="Fahrzeuge sollten arbeiten, aber keine beschäftigt")
                
                with col2:
                    st.metric("🟡 Teilweise beschäftigt", 
                             len(availability_categories["teilweise_beschaeftigt"]),
                             help="Einige verfügbare Fahrzeuge beschäftigt, aber nicht alle")
                    st.metric("🟢 Alle beschäftigt (innen)", 
                             len(availability_categories["alle_beschaeftigt_innen"]),
                             help="Alle verfügbaren Fahrzeuge beschäftigt, aber alle innen")
                
                with col3:
                    st.metric("🔴 Alle beschäftigt (≥1 außen)", 
                             len(availability_categories["alle_beschaeftigt_aussen"]),
                             delta="← PROBLEM!",
                             help="Alle verfügbaren Fahrzeuge beschäftigt, mind. 1 außen")
                    st.metric("❓ Keine Station-Zuordnung", 
                             uncategorized_no_data,
                             help="Missionen ohne Fahrzeuginformationen in DB")
                
                st.metric("📋 Mit Fahrzeuginformationen", 
                         f"{categorized_with_data}/{len(late_df)}",
                         delta=f"{(categorized_with_data/len(late_df)*100):.1f}%",
                         help="Verspätete Missionen, die in RTM-Fahrzeuginformationen abgebildet sind")
                
                # Show sample cases from each category
                st.write("---")
                st.write("**Beispiele aus jeder Kategorie:**")
                
                for category_key, category_name in [
                    ("keine_station_zuordnung", "❓ Keine Station-Zuordnung (Datenlücke)"),
                    ("keine_verfuegbar", "❌ Keine Fahrzeuge verfügbar (außerhalb Arbeitszeit)"),
                    ("alle_verfuegbar_frei", "✅ Alle verfügbaren Fahrzeuge frei"),
                    ("teilweise_beschaeftigt", "🟡 Nur teilweise beschäftigt"),
                    ("alle_beschaeftigt_innen", "🟢 Alle beschäftigt, aber nur innen"),
                    ("alle_beschaeftigt_aussen", "🔴 Alle beschäftigt + mind. 1 außen (GEZÄHLT)"),
                ]:
                    cases = availability_categories[category_key]
                    if cases:
                        with st.expander(f"{category_name} ({len(cases)} Fälle)", expanded=(category_key == "alle_beschaeftigt_aussen")):
                            st.dataframe(pd.DataFrame(cases[:20]), use_container_width=True)
                
                st.write("---")
                st.write("---")
                
                if overlap_details:
                    st.write(f"✅ **{len(overlap_details)} Fälle: ALLE Fahrzeuge ODER alle verfügbaren beschäftigt + mind. 1 außen!**")
                    st.dataframe(pd.DataFrame(overlap_details))
                    
                    # Additional debug: Show some details
                    st.write("**Beispiel-Details (erste 3 Fälle):**")
                    for i, detail in enumerate(overlap_details[:3]):
                        st.write(f"Fall {i+1}: {detail.get('station')} - {detail.get('total_vehicles')} Fahrzeuge, " 
                                f"{detail.get('available_vehicles')} sollten arbeiten, "
                                f"{detail.get('busy_total')} beschäftigt ({detail.get('busy_outside')} außen)")
                else:
                    st.write("⚠️ Keine Fälle gefunden mit neuer strikter Logik")
            
            # Apply busy check
            late_df["_busy_outside"] = late_df.apply(_check_rtw_busy_outside, axis=1)

            total_missions = len(df_inside_local)
            late_missions = len(late_df)
            late_due_to_busy = int(late_df["_busy_outside"].sum())

            current_rate = (1 - late_missions / total_missions) * 100 if total_missions else 0
            improved_rate = (
                1 - (late_missions - late_due_to_busy) / total_missions
            ) * 100 if total_missions else 0
            improvement = improved_rate - current_rate

            st.write(
                f"Im Rettungsdienstbereich SL-FL kam es im Jahr 2025 zu **{late_due_to_busy} Einsätzen**, "
                "in denen die Hilfsfrist nicht gehalten werden konnte, **weil zum Alarmzeitpunkt ALLE RTW "
                "dieser Station beschäftigt waren und mindestens einer außerhalb von SL-FL im Einsatz war**. "
                "Wären diese RTW in dieser Zeit verfügbar gewesen, "
                f"hätte sich der Hilfsfristerreichungsgrad im Ergebnis um **{improvement:.1f}%** verbessern können."
            )

            st.write(
                pd.DataFrame([
                    {
                        "missions_total_inside": total_missions,
                        "missions_late": late_missions,
                        "missions_late_busy_outside": late_due_to_busy,
                        "hilfsfrist_rate_current_pct": round(current_rate, 1),
                        "hilfsfrist_rate_improved_pct": round(improved_rate, 1),
                        "hilfsfrist_improvement_pct": round(improvement, 1),
                    }
                ])
            )
            
            # Store analysis results for later use in detailed analysis
            st.session_state["analysis_results"] = {
                "late_df": late_df,
                "station_to_vehicles": station_to_vehicles,
                "df_outside_rtw": df_outside_rtw,
                "df_inside_local": df_inside_local,
            }



# ============ DETAILED PER-MISSION ANALYSIS ============
# Now that wachbereiche_map is defined, we can use it in the detailed analysis

if "analysis_results" in st.session_state:
    st.subheader("📋 Detailanalyse: Verspätete Einsätze durch fehlende Fahrzeuge")
    
    late_df = st.session_state["analysis_results"]["late_df"]
    station_to_vehicles = st.session_state["analysis_results"]["station_to_vehicles"]
    df_outside_rtw = st.session_state["analysis_results"]["df_outside_rtw"]

    
    # Create mapping from station keys to wachbereich names
    wb_name_col = None
    for candidate in ["NAME", "Name", "name"]:
        if candidate in wachbereiche.columns:
            wb_name_col = candidate
            break
    
    station_to_wachbereich = {}
    if wb_name_col:
        for station_key, vehicles in station_to_vehicles.items():
            # Find matching wachbereich by normalizing names
            for idx, wb_row in wachbereiche.iterrows():
                wb_normalized = _norm_station(str(wb_row.get(wb_name_col, "")))
                if wb_normalized == station_key:
                    station_to_wachbereich[station_key] = wb_row.get(wb_name_col)
                    break
    
    # Get all late missions with busy outside vehicles (new strict logic)
    problem_missions = []
    busy_count = 0
    
    # Need to access df_inside_local to check which vehicles were busy inside
    # Get it from session state if available
    df_inside_local = st.session_state["analysis_results"].get("df_inside_local", late_df)
    
    for idx, late_row in late_df.iterrows():
        if not late_row.get("_busy_outside"):
            continue
        
        busy_count += 1
        station_key = late_row.get("_station_key")
        station_vehicles_info = station_to_vehicles.get(station_key, [])
        alarm_time = late_row.get("ALARMIERT")  # Using exact alarm moment per new logic
        responding_vehicle = late_row.get("EINSATZMITTEL", "Unbekannt")
        
        if not station_vehicles_info or pd.isna(alarm_time):
            continue
        
        # Get ALL station vehicles (ensure unique, not filtered by schedule for display purposes)
        station_vehicles = list(set([vinfo["vehicle"] for vinfo in station_vehicles_info]))
        
        # Also get which vehicles should be working at this time for reference
        available_vehicles = list(set([vinfo["vehicle"] for vinfo in station_vehicles_info 
                             if _is_vehicle_available_at_time(vinfo.get("availability", {}), alarm_time)]))
        
        if not station_vehicles:
            continue
        
        # Track which station vehicles are busy where at alarm moment
        busy_outside = []
        busy_inside = []
        
        # Find which vehicles from this station were busy outside at alarm moment
        end_col = "EINSATZENDE" if "EINSATZENDE" in df_outside_rtw.columns else "ZEIT_AB_Z"
        outside_busy_df = df_outside_rtw[
            (df_outside_rtw["EINSATZMITTEL"].astype(str).str.strip().isin(station_vehicles)) &
            df_outside_rtw["EINSATZBEGINN"].notna() &
            df_outside_rtw[end_col].notna() &
            (df_outside_rtw["EINSATZBEGINN"] <= alarm_time) &
            (df_outside_rtw[end_col] >= alarm_time)
        ]
        
        for vehicle in outside_busy_df["EINSATZMITTEL"].astype(str).str.strip().unique():
            busy_outside.append(vehicle)
        
        # Find which vehicles from this station were busy inside at alarm moment
        if "EINSATZBEGINN" in df_inside_local.columns and "EINSATZENDE" in df_inside_local.columns:
            inside_busy_df = df_inside_local[
                df_inside_local["EINSATZMITTEL"].astype(str).str.strip().isin(station_vehicles) &
                df_inside_local["EINSATZBEGINN"].notna() &
                df_inside_local["EINSATZENDE"].notna() &
                (df_inside_local["EINSATZBEGINN"] <= alarm_time) &
                (df_inside_local["EINSATZENDE"] >= alarm_time)
            ]
            
            for vehicle in inside_busy_df["EINSATZMITTEL"].astype(str).str.strip().unique():
                if vehicle not in busy_outside:  # Avoid duplicates
                    busy_inside.append(vehicle)
        
        # Get coordinates for the alarm location (inside)
        inside_lat = None
        inside_lon = None
        if hasattr(late_row, 'geometry') and late_row.geometry is not None:
            try:
                geom = late_row.geometry
                if late_df.crs and late_df.crs.to_string() != "EPSG:4326":
                    import geopandas as gpd
                    temp_series = gpd.GeoSeries([geom], crs=late_df.crs)
                    geom_wgs84 = temp_series.to_crs(epsg=4326)[0]
                    inside_lat = float(geom_wgs84.y)
                    inside_lon = float(geom_wgs84.x)
                else:
                    inside_lat = float(geom.y)
                    inside_lon = float(geom.x)
            except Exception as e:
                pass
        
        # Get coordinates for first outside busy vehicle (for map connection)
        outside_lat = None
        outside_lon = None
        if len(outside_busy_df) > 0:
            first_outside = outside_busy_df.iloc[0]
            if hasattr(first_outside, 'geometry') and first_outside.geometry is not None:
                try:
                    geom = first_outside.geometry
                    if df_outside_rtw.crs and df_outside_rtw.crs.to_string() != "EPSG:4326":
                        import geopandas as gpd
                        temp_series = gpd.GeoSeries([geom], crs=df_outside_rtw.crs)
                        geom_wgs84 = temp_series.to_crs(epsg=4326)[0]
                        outside_lat = float(geom_wgs84.y)
                        outside_lon = float(geom_wgs84.x)
                    else:
                        outside_lat = float(geom.y)
                        outside_lon = float(geom.x)
                except Exception as e:
                    pass
        
        problem_missions.append({
            "EINSATZ_NR": late_row.get("EINSATZ_NR"),
            "ALARMIERT": late_row.get("ALARMIERT"),
            "Wachbereich": station_to_wachbereich.get(station_key, station_key),
            "Fahrzeug_Station": station_key,
            "Station_Vehicles": ", ".join(station_vehicles),
            "Available_Vehicles": ", ".join(available_vehicles) if available_vehicles else "Keine (außerhalb Arbeitszeit)",
            "Busy_Outside": ", ".join(busy_outside) if busy_outside else "Keine",
            "Busy_Inside": ", ".join(busy_inside) if busy_inside else "Keine",
            "Responding_Vehicle": responding_vehicle,
            "Fahrzeug_außen_von": outside_busy_df.iloc[0]["EINSATZBEGINN"] if len(outside_busy_df) > 0 else None,
            "Fahrzeug_außen_bis": outside_busy_df.iloc[0][end_col] if len(outside_busy_df) > 0 else None,
            "Hilfsfrist_min": late_row.get("_hilfsfrist_min"),
            "inside_lat": inside_lat,
            "inside_lon": inside_lon,
            "outside_lat": outside_lat,
            "outside_lon": outside_lon,
        })

    
    if problem_missions:
        problem_df = pd.DataFrame(problem_missions)
        
        st.write(f"**Gefundene Fälle: {len(problem_df)}**")
        
        # Create tabs for list view and map view
        tab_list, tab_map = st.tabs(["📊 Listenansicht", "🗺️ Kartenansicht"])
        
        with tab_list:
            st.dataframe(
                problem_df[[
                    "EINSATZ_NR",
                    "ALARMIERT",
                    "Responding_Vehicle",
                    "Wachbereich",
                    "Station_Vehicles",
                    "Available_Vehicles",
                    "Busy_Outside",
                    "Busy_Inside",
                    "Hilfsfrist_min",
                ]],
                use_container_width=True,
                hide_index=True,
            )
        
        with tab_map:
            # Get bounds
            bounds = wachbereiche_map.total_bounds
            center_lon = (bounds[0] + bounds[2]) / 2
            center_lat = (bounds[1] + bounds[3]) / 2
            
            m_problems = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=9,
                tiles="OpenStreetMap"
            )
            
            # Add fullscreen button
            from folium.plugins import Fullscreen
            Fullscreen().add_to(m_problems)
            
            # Add wachbereiche boundaries
            for idx, row in wachbereiche_map.iterrows():
                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x: {"color": "#cccccc", "weight": 1, "opacity": 0.5},
                ).add_to(m_problems)
            
            # Debug coordinates
            valid_inside = problem_df[
                (problem_df["inside_lat"].notna()) & 
                (problem_df["inside_lon"].notna())
            ]
            valid_outside = problem_df[
                (problem_df["outside_lat"].notna()) & 
                (problem_df["outside_lon"].notna())
            ]
                        
            # Add problem missions with lines connecting inside to outside locations
            markers_added = 0
            for idx, mission in problem_df.iterrows():
                inside_lat = mission["inside_lat"]
                inside_lon = mission["inside_lon"]
                outside_lat = mission["outside_lat"]
                outside_lon = mission["outside_lon"]
                
                if pd.isna(inside_lat) or pd.isna(inside_lon):
                    continue
                
                markers_added += 1
                
                # Inside mission point (red)
                popup_html = f"""
                <div style='font-family: Arial; min-width: 300px;'>
                    <b style='font-size: 14px;'>🚨 ALARM INSIDE (ZU SPÄT)</b><br>
                    <hr style='margin:6px 0; border-top: 2px solid #d62728;'>
                    <b>Einsatz-NR:</b> {mission["EINSATZ_NR"]}<br>
                    <b>Alarmiert:</b> {mission["ALARMIERT"]}<br>
                    <b>Hilfsfrist:</b> {mission["Hilfsfrist_min"]:.1f} min<br>
                    <b>Wachbereich:</b> {mission["Wachbereich"]}<br>
                    <hr style='margin:6px 0;'>
                    <b>Tatsächlich gefahren:</b><br>
                    <span style='color: #d62728; font-weight: bold;'>{mission["Responding_Vehicle"]}</span><br>
                    <hr style='margin:6px 0;'>
                    <b>Station-Fahrzeuge (alle):</b><br>
                    <span style='font-size: 11px;'>{mission["Station_Vehicles"]}</span><br>
                    <b style='color: #1f77b4;'>Sollten arbeiten:</b><br>
                    <span style='font-size: 11px;'>{mission["Available_Vehicles"]}</span><br>
                    <b style='color: #ff7f0e;'>Beschäftigt Außen:</b><br>
                    <span style='font-size: 11px;'>{mission["Busy_Outside"]}</span><br>
                    <b style='color: #2ca02c;'>Beschäftigt Innen:</b><br>
                    <span style='font-size: 11px;'>{mission["Busy_Inside"]}</span>
                </div>
                """
                folium.CircleMarker(
                    location=[inside_lat, inside_lon],
                    radius=8,
                    popup=folium.Popup(popup_html, max_width=400),
                    color="#d62728",  # red
                    fill=True,
                    fillColor="#d62728",
                    fillOpacity=0.8,
                    weight=2,
                    opacity=1,
                ).add_to(m_problems)
                
                # If outside location available, add it and draw line
                if not pd.isna(outside_lat) and not pd.isna(outside_lon):
                    # Outside mission point (orange)
                    outside_popup_html = f"""
                    <div style='font-family: Arial; min-width: 280px;'>
                        <b style='font-size: 14px;'>🚑 FAHRZEUG UNTERWEGS (OUTSIDE)</b><br>
                        <hr style='margin:6px 0; border-top: 2px solid #ff7f0e;'>
                        <b>Station-Fahrzeuge außen:</b><br>
                        <span style='font-size: 11px; color: #ff7f0e; font-weight: bold;'>{mission["Busy_Outside"]}</span><br>
                        <hr style='margin:6px 0;'>
                        <b>Von:</b> {mission["Fahrzeug_außen_von"]}<br>
                        <b>Bis:</b> {mission["Fahrzeug_außen_bis"]}
                    </div>
                    """
                    folium.CircleMarker(
                        location=[outside_lat, outside_lon],
                        radius=6,
                        popup=folium.Popup(outside_popup_html, max_width=350),
                        color="#ff7f0e",  # orange
                        fill=True,
                        fillColor="#ff7f0e",
                        fillOpacity=0.6,
                        weight=2,
                        opacity=0.8,
                    ).add_to(m_problems)
                    
                    # Draw line connecting inside to outside
                    line_popup_html = f"""
                    <div style='font-family: Arial; min-width: 250px;'>
                        <b>🔗 Verbindung</b><br>
                        <b>Einsatz:</b> {mission['EINSATZ_NR']}<br>
                        <b>Beschäftigte Fahrzeuge:</b><br>
                        <span style='font-size: 11px; color: #ff7f0e;'>{mission['Busy_Outside']}</span>
                    </div>
                    """
                    folium.PolyLine(
                        locations=[
                            [inside_lat, inside_lon],
                            [outside_lat, outside_lon],
                        ],
                        color="#ff0000",
                        weight=2,
                        opacity=0.6,
                        popup=folium.Popup(line_popup_html, max_width=300),
                    ).add_to(m_problems)
            
            
            # Add legend
            legend_html = '''
            <div style="position: fixed;
                 bottom: 30px; right: 30px; width: auto; height: auto;
                 background-color: rgba(255, 255, 255, 0.95);
                 border: 1px solid #444; border-radius: 6px; z-index: 9999;
                 font-size: 12px; color: #111; padding: 12px 14px;
                 box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);">
            <p style="margin: 0 0 8px 0; font-weight: 700; color: #111;">Problem-Einsätze</p>
            <p style="margin: 4px 0; color: #111;">
                <span style="background-color: #d62728; width: 12px; height: 12px; 
                display: inline-block; margin-right: 6px; border-radius: 50%;"></span>
                Alarm Inside (zu spät)
            </p>
            <p style="margin: 4px 0; color: #111;">
                <span style="background-color: #ff7f0e; width: 12px; height: 12px; 
                display: inline-block; margin-right: 6px; border-radius: 50%;"></span>
                Fahrzeug außen (beschäftigt)
            </p>
            <p style="margin: 4px 0; color: #111;">
                <span style="background-color: #ff0000; height: 2px; width: 12px;
                display: inline-block; margin-right: 6px;"></span>
                Fahrzeug nicht verfügbar
            </p>
            </div>
            '''
            m_problems.get_root().html.add_child(folium.Element(legend_html))
            
            st_folium(m_problems, width=1200, height=600, key="problem_map", returned_objects=[])
    else:
        st.info("✅ Keine Fälle gefunden, bei denen stationszugeordnete Fahrzeuge außerhalb waren.")
