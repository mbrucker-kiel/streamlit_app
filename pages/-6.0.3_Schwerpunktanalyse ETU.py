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

st.markdown(
    """
Aufgrund wiederkehrender Anfragen ist aufgefallen, dass die Adresse häufig als Einsatz ohne Transportindikation auftaucht.  
Mithilfe dieser Auswertung sollen tiefere Einblicke in die Daten gewonnen werden, um mögliche Ursachen zu identifizieren.  

**Filteroptionen:**  
In dem folgenden Dropdown-Menü können gezielt Einsätze nach Stadt, Straße und Hausnummer gefiltert werden.
"""
)

color = ["#8ea9db", "#ffc000", "#ffff00", "#92d050", "#7030a0"]
color_brighter = ["#a8c0f0", "#ffd966", "#ffff99", "#b6d7a8", "#8a4fbf"]
color_darker = ["#6d8ac9", "#e6b800", "#e6e600", "#6aa84f", "#4a1d6a"]

etu_df = data_loading("ETÜ")
index_df = data_loading("Index")


# filter for patient address use env variables as placeholders
with st.expander("Filteroptionen"):
    st.write("Filteroptionen für die Schwerpunktanalyse")

    # City filter with "Alle" option
    city_options = ["Alle"] + list(etu_df["EO_ORT"].dropna().unique())
    st.selectbox("Stadt", options=city_options, key="city_filter")

    # Filter by city first to get streets
    temp_filtered = etu_df
    if st.session_state["city_filter"] != "Alle":
        temp_filtered = temp_filtered[
            temp_filtered["EO_ORT"] == st.session_state["city_filter"]
        ]

    # Street filter with "Alle" option, dynamic based on city
    street_options = ["Alle"] + list(temp_filtered["EO_STRASSE"].dropna().unique())
    st.selectbox("Straße", options=street_options, key="street_filter")

    # Filter by street to get house numbers
    if st.session_state["street_filter"] != "Alle":
        temp_filtered = temp_filtered[
            temp_filtered["EO_STRASSE"] == st.session_state["street_filter"]
        ]

    # House number filter with "Alle" option, dynamic based on city and street
    house_options = ["Alle"] + list(
        temp_filtered["EO_STRASSE_ZUSATZ"].dropna().unique()
    )
    st.selectbox("Hausnummer", options=house_options, key="house_number_filter")

    # Patient Lastname filter with "Alle" option
    # Get patient lastnames from Index data
    patient_lastname_options = ["Alle"] + list(
        index_df["patientLastname"].dropna().unique()
    )
    st.selectbox("Patient Nachname", options=patient_lastname_options, key="patient_lastname_filter")

filtered_df = etu_df

if st.session_state["city_filter"] != "Alle":
    filtered_df = filtered_df[
        filtered_df["EO_ORT"] == st.session_state["city_filter"]
    ]

if st.session_state["street_filter"] != "Alle":
    filtered_df = filtered_df[
        filtered_df["EO_STRASSE"] == st.session_state["street_filter"]
    ]

if st.session_state["house_number_filter"] != "Alle":
    filtered_df = filtered_df[
        filtered_df["EO_STRASSE_ZUSATZ"] == st.session_state["house_number_filter"]
    ]

# Filter für Einsatzdatum Intervall
st.date_input(
    "Einsatzdatum von-bis",
    value=(pd.to_datetime("2025-01-01T00:00:00"), pd.to_datetime("2025-12-31")),
    key="date_range",
)

# filter df based on etu_df["EINSATZDATUM"]
start_date, end_date = st.session_state["date_range"]

# Fix: Convert to timezone-aware datetime in UTC to match the column's dtype
start_date_utc = pd.to_datetime(start_date).tz_localize("UTC")
end_date_utc = pd.to_datetime(end_date).tz_localize("UTC")

# Handle timezone conversion for EINSATZDATUM - localize if naive, convert if already localized
if filtered_df["EINSATZBEGINN"].dt.tz is None:
    # Data is tz-naive, localize to UTC
    filtered_df["EINSATZBEGINN"] = pd.to_datetime(filtered_df["EINSATZBEGINN"]).dt.tz_localize("UTC")
else:
    # Data is already timezone-aware, convert to UTC
    filtered_df["EINSATZBEGINN"] = pd.to_datetime(filtered_df["EINSATZBEGINN"]).dt.tz_convert("UTC")

mask = (filtered_df["EINSATZBEGINN"] >= start_date_utc) & (
    filtered_df["EINSATZBEGINN"] <= end_date_utc
)
filtered_df = filtered_df.loc[mask]

merged_df = pd.merge(
    filtered_df, index_df, left_on="EINSATZ_NR", right_on="missionNumber", how="left"
)

# Apply patient lastname filter after merge
if st.session_state["patient_lastname_filter"] != "Alle":
    merged_df = merged_df[
        merged_df["patientLastname"] == st.session_state["patient_lastname_filter"]
    ]

# i want to display big the total number of filtered_df and display a pie chart with missionType

st.markdown(f"### Gesamtanzahl der Einsätze: {len(merged_df)}")

# Display pie chart for missionType distribution
if "staticMissionType" in merged_df.columns:
    mission_counts = merged_df["staticMissionType"].value_counts().reset_index()
    mission_counts.columns = ["staticMissionType", "count"]

    # Group small categories into "Sonstige" after top 10
    if len(mission_counts) > 10:
        # Sort by count descending
        mission_counts = mission_counts.sort_values("count", ascending=False)

        # Keep top 10
        top_10 = mission_counts.head(10)

        # Sum the rest into "Sonstige"
        other_count = mission_counts.iloc[10:]["count"].sum()

        # Create new dataframe with top 10 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame(
                {"staticMissionType": ["Sonstige"], "count": [other_count]}
            )
            mission_counts = pd.concat([top_10, other_row], ignore_index=True)

    st.write("**Verteilung der Einsatztypen:**")
    st.write(mission_counts)

    fig = px.pie(
        mission_counts,
        names="staticMissionType",
        values="count",
        title="Verteilung der Einsatztypen (Top 10 + Sonstige)",
        color_discrete_sequence=color,
    )
    st.plotly_chart(fig)

# Filter for Krankentransport missions
if "staticMissionType" in merged_df.columns:
    # Get unique types for filtering
    unique_types = merged_df["staticMissionType"].unique()

    # Filter for Krankentransport only (exclude RTW and other emergency transports)
    krankentransport_values = [
        val
        for val in unique_types
        if "krankentransport" in str(val).lower() and "rtw" not in str(val).lower()
    ]
    if krankentransport_values:
        merged_df = merged_df[
            merged_df["staticMissionType"].isin(krankentransport_values)
        ]
        st.write(f"**Gefiltert nach: {krankentransport_values}**")
    else:
        # Fallback to exact match if no values found
        merged_df = merged_df[
            merged_df["staticMissionType"] == "Krankentransport"
        ]

    st.write(f"**Nach Filter: {len(merged_df)} Krankentransport-Einsätze gefunden**")

# Note: KTW-specific filtering will be applied only for the anamnesis analysis below

st.dataframe(merged_df)

# display Einsätze pro Woche differentiated by emergencyCareType
st.subheader("Einsätze pro Woche nach emergencyCareType")
if "emergencyCareType" in merged_df.columns and "missionDate" in merged_df.columns:
    # Filter out rows with NaT missionDate before creating periods
    valid_dates_df = merged_df.dropna(subset=["missionDate"])
    if not valid_dates_df.empty:
        valid_dates_df["week"] = (
            valid_dates_df["missionDate"]
            .dt.to_period("W")
            .apply(lambda r: r.start_time)
        )
        weekly_counts = (
            valid_dates_df.groupby(["week", "emergencyCareType"])
            .size()
            .reset_index(name="counts")
        )

        # Apply color scheme based on vehicle types
        fig = px.bar(
            weekly_counts,
            x="week",
            y="counts",
            color="emergencyCareType",
            title="Einsätze pro Woche nach Einsatzart",
            color_discrete_sequence=color,
            labels={"week": "Woche", "counts": "Anzahl je Woche"},
        )
        st.plotly_chart(fig)
    else:
        st.warning("Keine gültigen Einsatzdaten für die Wochenanalyse verfügbar.")
else:
    st.warning(
        "Spalte 'emergencyCareType' oder 'missionDate' nicht gefunden im Datensatz."
    )

# display Einsätze pro Woche differentiated by missionType
st.subheader("Einsätze pro Woche nach missionType")
if "missionType" in merged_df.columns and "missionDate" in merged_df.columns:
    # Filter out rows with NaT missionDate before creating periods
    valid_dates_df = merged_df.dropna(subset=["missionDate"])
    if not valid_dates_df.empty:
        valid_dates_df["week"] = (
            valid_dates_df["missionDate"]
            .dt.to_period("W")
            .apply(lambda r: r.start_time)
        )
        weekly_counts = (
            valid_dates_df.groupby(["week", "missionType"])
            .size()
            .reset_index(name="counts")
        )

        # Apply color scheme and use darker colors for "kein Transport" missions
    def get_color_for_mission(mission_type):
        if pd.isna(mission_type):
            return color[4]  # default - unterstützer color for unknown
        mission_str = str(mission_type).lower()

        # Check for "kein Transport" first (these get darker shades)
        if "kein transport" in mission_str or "keine versorgung" in mission_str:
            if "nef" in mission_str:
                return color_darker[0]  # nef keine versorgung - darker blue
            elif "ktw" in mission_str:
                return color_darker[1]  # ktw - darker orange
            elif "rtw" in mission_str:
                return color_darker[3]  # rtw - darker green
            elif "s-ktw" in mission_str:
                return color_darker[2]  # sktw - darker yellow
            else:
                return color_darker[4]  # default darker for unknown vehicle

        # Regular missions (normal colors)
        if "nef" in mission_str:
            return color[0]  # nef - blue
        elif "rtw" in mission_str:
            return color[3]  # rtw - green
        elif "s-ktw" in mission_str:
            return color[2]  # sktw - yellow
        elif "ktw" in mission_str:
            return color[1]  # ktw - orange
        elif (
            "unterstützer" in mission_str
            or "dienstfahrt" in mission_str
            or "werkstattfahrt" in mission_str
            or "sonstige" in mission_str
        ):
            return color[4]  # unterstützer/sonstige - purple
        else:
            return color[4]  # default - purple for other types

    # Create custom color mapping
    unique_missions = weekly_counts["missionType"].unique()
    color_mapping = {
        mission: get_color_for_mission(mission) for mission in unique_missions
    }

    # Define custom category order for legend
    category_order = []

    # Helper function to check if mission contains "kein transport" or similar
    def has_kein_transport(mission):
        if pd.isna(mission):
            return False
        mission_str = str(mission).lower()
        return "kein" in mission_str or "keine" in mission_str or "ohne" in mission_str

    # Add NEF types first (without "kein transport")
    nef_types = [
        m
        for m in unique_missions
        if "nef" in str(m).lower() and not has_kein_transport(m)
    ]
    category_order.extend(sorted(nef_types))

    # Add NEF keine Versorgung
    nef_keine = [
        m for m in unique_missions if "nef" in str(m).lower() and has_kein_transport(m)
    ]
    category_order.extend(sorted(nef_keine))

    # Add RTW types (without "kein transport")
    rtw_types = [
        m
        for m in unique_missions
        if "rtw" in str(m).lower()
        and not has_kein_transport(m)
        and "s-ktw" not in str(m).lower()
    ]
    category_order.extend(sorted(rtw_types))

    # Add RTW keine Versorgung
    rtw_keine = [
        m
        for m in unique_missions
        if "rtw" in str(m).lower()
        and has_kein_transport(m)
        and "s-ktw" not in str(m).lower()
    ]
    category_order.extend(sorted(rtw_keine))

    # Add S-KTW types (without "kein transport")
    sktw_types = [
        m
        for m in unique_missions
        if "s-ktw" in str(m).lower()
        or ("sktw" in str(m).lower() and not has_kein_transport(m))
    ]
    category_order.extend(sorted(sktw_types))

    # Add S-KTW keine Versorgung
    sktw_keine = [
        m
        for m in unique_missions
        if ("s-ktw" in str(m).lower() or "sktw" in str(m).lower())
        and has_kein_transport(m)
    ]
    category_order.extend(sorted(sktw_keine))

    # Add KTW types (without "kein transport" and not S-KTW)
    ktw_types = [
        m
        for m in unique_missions
        if "ktw" in str(m).lower()
        and "s-ktw" not in str(m).lower()
        and not has_kein_transport(m)
    ]
    category_order.extend(sorted(ktw_types))

    # Add KTW keine Versorgung
    ktw_keine = [
        m
        for m in unique_missions
        if "ktw" in str(m).lower()
        and "s-ktw" not in str(m).lower()
        and has_kein_transport(m)
    ]
    category_order.extend(sorted(ktw_keine))

    # Add remaining types (unterstützer, sonstige, etc.)
    remaining = [m for m in unique_missions if m not in category_order]
    category_order.extend(sorted(remaining))

    fig = px.bar(
        weekly_counts,
        x="week",
        y="counts",
        color="missionType",
        title="Einsätze pro Woche nach Einsatztyp",
        color_discrete_map=color_mapping,
        category_orders={"missionType": category_order},
        labels={"week": "Woche", "counts": "Anzahl je Woche"},
    )
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'missionType' nicht gefunden im Datensatz.")

# display Einsätze per Weekday and hour of day
st.subheader("Einsätze nach Wochentag und Uhrzeit")
if "alarmTime" in merged_df.columns:
    # Filter out rows with NaT alarmTime before applying dt operations
    valid_times_df = merged_df.dropna(subset=["alarmTime"])
    if not valid_times_df.empty:
        # Ensure alarmTime is datetime
        valid_times_df["alarmTime"] = pd.to_datetime(valid_times_df["alarmTime"], errors='coerce')
        valid_times_df = valid_times_df.dropna(subset=["alarmTime"])  # Remove any rows that couldn't be converted

        if not valid_times_df.empty:
            valid_times_df["weekday"] = valid_times_df["alarmTime"].dt.day_name()
            valid_times_df["hour"] = valid_times_df["alarmTime"].dt.hour
            heatmap_data = (
                valid_times_df.groupby(["weekday", "hour"]).size().reset_index(name="counts")
            )
            heatmap_data = heatmap_data.pivot(
                index="weekday", columns="hour", values="counts"
            ).fillna(0)
            # Ensure all hours from 0 to 23 are included
            all_hours = list(range(24))
            heatmap_data = heatmap_data.reindex(columns=all_hours, fill_value=0)
            # Reorder weekdays
            weekdays_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            heatmap_data = heatmap_data.reindex(weekdays_order)
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Hour of Day", y="Weekday", color="Number of Missions"),
                x=heatmap_data.columns,
                y=heatmap_data.index,
                title="Einsätze nach Wochentag und Uhrzeit",
            )
            st.plotly_chart(fig)
        else:
            st.warning("Keine gültigen Alarmzeiten nach Bereinigung verfügbar.")
    else:
        st.warning("Keine gültigen Alarmzeiten für die Wochentag/Uhrzeit-Analyse verfügbar.")
else:
    st.warning("Spalte 'alarmTime' nicht gefunden im Datensatz.")

# pie chart displaying leadingDiagnosis distribution
st.subheader("Verteilung der NIDA-Einsatzdiagnosen")
if "leadingDiagnosis" in merged_df.columns:
    diagnosis_counts = merged_df["leadingDiagnosis"].value_counts().reset_index()
    diagnosis_counts.columns = ["leadingDiagnosis", "count"]

    # Group small categories into "Sonstige" after top 10
    if len(diagnosis_counts) > 10:
        # Sort by count descending
        diagnosis_counts = diagnosis_counts.sort_values("count", ascending=False)

        # Keep top 10
        top_10 = diagnosis_counts.head(10)

        # Sum the rest into "Sonstige"
        other_count = diagnosis_counts.iloc[10:]["count"].sum()

        # Create new dataframe with top 10 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame(
                {"leadingDiagnosis": ["Sonstige"], "count": [other_count]}
            )
            diagnosis_counts = pd.concat([top_10, other_row], ignore_index=True)

    st.write(diagnosis_counts)

    fig = px.pie(
        diagnosis_counts,
        names="leadingDiagnosis",
        values="count",
        title="Verteilung der Einsatzdiagnosen (Top 10 + Sonstige)",
        color_discrete_sequence=color,
    )
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'leadingDiagnosis' nicht gefunden im Datensatz.")

# Check merging quality
st.subheader("Überprüfung der Datenverknüpfung (Index ↔ ETU)")
st.write(
    "Aufgrund von mehrfach allamierungen existieren zu einzelnen "
    "NIDA-Protokollen mehrere ETÜ-Datensätze."
)

st.write("Merge über NIDA-Protokoll['missionNumber'] und ETÜ['EINSATZ_NR']")

# Show sample of merged data
st.dataframe(merged_df.head())

total_filtered = len(filtered_df)
total_index = len(index_df)
total_merged = len(merged_df)
# Count unique missions that have Index data
# (since multiple vehicles can be assigned to same mission)
matched = merged_df.dropna(subset=["protocolId"])["EINSATZ_NR"].nunique()
missing_index = total_filtered - matched

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Gesamt gefilterte ETÜ-Einsätze", total_filtered)
with col2:
    st.metric("Index-Datensätze", total_index)
with col3:
    st.metric("Verknüpfte Einsätze", matched)
with col4:
    st.metric("Fehlende Index-Daten", missing_index)

if missing_index > 0:
    st.warning(
        f"{missing_index} ETÜ-Einsätze konnten nicht mit Index-Daten "
        "verknüpft werden."
    )

# Sankey diagram: Flow from ETU CEDUS_CODE to leadingDiagnosis
st.subheader("Sankey-Diagramm: Von ETU-Diagnose zu endgültiger Diagnose")

# Prepare data for Sankey (only rows with both CEDUS_CODE and leadingDiagnosis)
sankey_data = merged_df.dropna(subset=["CEDUS_CODE", "leadingDiagnosis"])

if not sankey_data.empty:
    # Group by CEDUS_CODE and leadingDiagnosis to count flows
    flow_counts = (
        sankey_data.groupby(["CEDUS_CODE", "leadingDiagnosis"])
        .size()
        .reset_index(name="count")
    )

    # Create nodes (unique CEDUS_CODE + unique leadingDiagnosis)
    cedus_codes = flow_counts["CEDUS_CODE"].unique()
    diagnoses = flow_counts["leadingDiagnosis"].unique()
    nodes = list(cedus_codes) + list(diagnoses)

    # Create node index mapping
    node_dict = {node: i for i, node in enumerate(nodes)}

    # Create links
    links = []
    for _, row in flow_counts.iterrows():
        source = node_dict[row["CEDUS_CODE"]]
        target = node_dict[row["leadingDiagnosis"]]
        value = row["count"]
        links.append({"source": source, "target": target, "value": value})

    # Create Sankey diagram
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=nodes,
                ),
                link=dict(
                    source=[link["source"] for link in links],
                    target=[link["target"] for link in links],
                    value=[link["value"] for link in links],
                ),
            )
        ]
    )

    fig.update_layout(
        title_text="Datenfluss: ETU-Diagnose (CEDUS_CODE) → "
                   "Endgültige Diagnose (leadingDiagnosis)",
        font_size=10,
    )

    st.plotly_chart(fig)

    # Display flow counts table
    st.write("**Detaillierte Flüsse:**")
    st.dataframe(flow_counts.sort_values("count", ascending=False))
else:
    st.warning(
        "Keine Daten mit sowohl ETU-Diagnose als auch endgültiger "
        "Diagnose verfügbar für das Sankey-Diagramm."
    )

# ===== ETÜ-SPEZIFISCHE ANALYSEN =====
st.subheader("ETÜ-spezifische Analysen")

# CEDUS_CODE Analysis
st.subheader("Verteilung der ETÜ-Diagnosen (CEDUS_CODE)")
if "CEDUS_CODE" in filtered_df.columns:
    cedus_counts = filtered_df["CEDUS_CODE"].value_counts().reset_index()
    cedus_counts.columns = ["CEDUS_CODE", "count"]

    # Group small categories into "Sonstige" after top 15
    if len(cedus_counts) > 15:
        # Sort by count descending
        cedus_counts = cedus_counts.sort_values("count", ascending=False)

        # Keep top 15
        top_15 = cedus_counts.head(15)

        # Sum the rest into "Sonstige"
        other_count = cedus_counts.iloc[15:]["count"].sum()

        # Create new dataframe with top 15 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame(
                {"CEDUS_CODE": ["Sonstige"], "count": [other_count]}
            )
            cedus_counts = pd.concat([top_15, other_row], ignore_index=True)

    st.write("**Verteilung der ETÜ-Diagnosen:**")
    st.write(cedus_counts)

    fig = px.pie(
        cedus_counts,
        names="CEDUS_CODE",
        values="count",
        title="Verteilung der ETÜ-Diagnosen (CEDUS_CODE - Top 15 + Sonstige)",
        color_discrete_sequence=color,
    )
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'CEDUS_CODE' nicht gefunden im ETÜ-Datensatz.")

# EINSATZMITTELTYP Analysis
st.subheader("Verteilung der Einsatzmitteltypen (EINSATZMITTELTYP)")
if "EINSATZMITTELTYP" in filtered_df.columns:
    mitteltyp_counts = filtered_df["EINSATZMITTELTYP"].value_counts().reset_index()
    mitteltyp_counts.columns = ["EINSATZMITTELTYP", "count"]

    # Group small categories into "Sonstige" after top 10
    if len(mitteltyp_counts) > 10:
        # Sort by count descending
        mitteltyp_counts = mitteltyp_counts.sort_values("count", ascending=False)

        # Keep top 10
        top_10 = mitteltyp_counts.head(10)

        # Sum the rest into "Sonstige"
        other_count = mitteltyp_counts.iloc[10:]["count"].sum()

        # Create new dataframe with top 10 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame(
                {"EINSATZMITTELTYP": ["Sonstige"], "count": [other_count]}
            )
            mitteltyp_counts = pd.concat([top_10, other_row], ignore_index=True)

    st.write("**Verteilung der Einsatzmitteltypen:**")
    st.write(mitteltyp_counts)

    fig = px.pie(
        mitteltyp_counts,
        names="EINSATZMITTELTYP",
        values="count",
        title="Verteilung der Einsatzmitteltypen (Top 10 + Sonstige)",
        color_discrete_sequence=color,
    )
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'EINSATZMITTELTYP' nicht gefunden im ETÜ-Datensatz.")

# Patient Lastname Analysis
st.subheader("Verteilung der Patientennachnamen")
if "patientLastname" in merged_df.columns:
    lastname_counts = merged_df["patientLastname"].value_counts().reset_index()
    lastname_counts.columns = ["patientLastname", "count"]

    # Group small categories into "Sonstige" after top 15
    if len(lastname_counts) > 15:
        # Sort by count descending
        lastname_counts = lastname_counts.sort_values("count", ascending=False)

        # Keep top 15
        top_15 = lastname_counts.head(15)

        # Sum the rest into "Sonstige"
        other_count = lastname_counts.iloc[15:]["count"].sum()

        # Create new dataframe with top 15 + Sonstige
        if other_count > 0:
            other_row = pd.DataFrame(
                {"patientLastname": ["Sonstige"], "count": [other_count]}
            )
            lastname_counts = pd.concat([top_15, other_row], ignore_index=True)

    st.write("**Verteilung der Patientennachnamen:**")
    st.write(lastname_counts)

    fig = px.pie(
        lastname_counts,
        names="patientLastname",
        values="count",
        title="Verteilung der Patientennachnamen (Top 15 + Sonstige)",
        color_discrete_sequence=color,
    )
    st.plotly_chart(fig)
else:
    st.warning("Spalte 'patientLastname' nicht gefunden im Datensatz.")

df_freetext = data_loading("Freetext", limit=500000)

# merge nida_df[protocolId] with etu EINSATZ_NR
if not filtered_df.empty and not index_df.empty:
    # Merge ETÜ data with Index data based on mission numbers
    merged_df = filtered_df.merge(
        index_df,
        left_on="EINSATZ_NR",
        right_on="missionNumber",
        how="left",
        suffixes=("_ETÜ", "_Index")
    )

    # If Freetext data is available, merge it too
    if not df_freetext.empty:
        merged_with_freetext = merged_df.merge(
            df_freetext,
            left_on="protocolId",
            right_on="protocolId",
            how="left",
            suffixes=("", "_Freetext")
        )
else:
    st.warning("Keine Daten zum Zusammenführen verfügbar")

# Display Anamnese data from freetext
st.subheader("🏥 Anamnesis-Daten")

if not merged_with_freetext.empty and 'data' in merged_with_freetext.columns:
    # Extract Anamnese data from the nested data column of MERGED freetext data
    anamnese_data = []

    for idx, row in merged_with_freetext.iterrows():
        if row['data'] and isinstance(row['data'], list):
            for item in row['data']:
                if isinstance(item, dict) and item.get('description') == 'Anamnese':
                    # Add protocolId from the row and merge with item data
                    anamnese_item = {
                        'protocolId': row.get('protocolId'),
                        'EINSATZ_NR': row.get('EINSATZ_NR'),
                        **item
                    }
                    anamnese_data.append(anamnese_item)

    if anamnese_data:
        st.write(f"**Anamnesis-Daten: {len(anamnese_data)} Einträge gefunden**")

        # Convert to DataFrame for display
        anamnese_df = pd.DataFrame(anamnese_data)

        # Reorder columns to show AUFTRAGS_NR and protocolId first
        cols = ["EINSATZ_NR", "protocolId"] + [
            col for col in anamnese_df.columns
            if col not in ["EINSATZ_NR", "protocolId"]
        ]
        anamnese_df = anamnese_df[cols]

        st.dataframe(anamnese_df)
    else:
        st.warning("Keine Anamnese-Daten in den gefilterten Einsätzen gefunden")
else:
    st.warning("Keine Freetext-Daten verfügbar oder keine Übereinstimmungen gefunden")

