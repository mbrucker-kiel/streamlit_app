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

# Load Index data and merge
index_df = data_loading("Index", limit=50000)

merged_df = pd.merge(
    filtered_df, index_df, left_on="EINSATZ_NR", right_on="missionNumber", how="left"
)

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

df_freetext = data_loading("Freetext")

# Explode the data array to get individual freetext entries
if not df_freetext.empty and "data" in df_freetext.columns:
    df_freetext = df_freetext.explode("data").reset_index(drop=True)
    # Extract fields from the nested data structure
    freetext_expanded = pd.json_normalize(df_freetext["data"])
    # Combine with the original dataframe (excluding the data column and duplicate protocolId)
    df_freetext = pd.concat(
        [df_freetext.drop(columns=["data", "protocolId"]), freetext_expanded], axis=1
    )

# Filter for anamnesis data (all transports for general analysis)
anamnesis_df = df_freetext[
    df_freetext["description"].str.contains("Anamnese", na=False, case=False)
]

# Filter anamnesis data to only include protocols from the filtered Krankentransport missions (all transports)
anamnesis_df = anamnesis_df[anamnesis_df["protocolId"].isin(merged_df["protocolId"])]

st.write(
    f"**Anamnesis-Daten: {len(anamnesis_df)} Protokolle gefunden für die gefilterten Einsätze**"
)

st.subheader("Anamnesetext ")
st.dataframe(anamnesis_df[anamnesis_df["protocolId"].isin(merged_df["protocolId"])])