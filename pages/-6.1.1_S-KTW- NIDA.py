import streamlit as st
import pandas as pd
import plotly.express as px
import os
from data_loading import data_loading

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

# Load configuration from environment variables
DEFAULT_NIDA_VEHICLES = os.getenv("DEFAULT_NIDA_SKTW_VEHICLES").split(",")

# Load vehicle schedules from environment variables (format: vehicle1:hours,vehicle2:hours,...)
VEHICLE_CONFIG = os.getenv("VEHICLE_CONFIG")
VEHICLE_SCHEDULES = {}
for config in VEHICLE_CONFIG.split(","):
    if ":" in config:
        vehicle, hours = config.split(":", 1)
        VEHICLE_SCHEDULES[vehicle.strip()] = int(hours.strip())

st.markdown(
    """
# 🚑 S-KTW Auslastung

Dieses Dashboard analysiert die Auslastung von S-KTWs (Sofort-Krankentransportwagen).

## Berechnung der Auslastung
Für die Analyse der Auslastung wird die Zeit zwischen **StatusAlarm** und **StatusEnd** der NIDA-Protokolle verwendet.
Um die Auslastung korrekt zu berechnen, wird die Verfügbarkeit in Stunden durch den folgenden Datums-Filter berechnet.
"""
)


# Load data
index_df = data_loading("Index")
details_df = data_loading("Details")

# Merge dataframes on protocolId
if not details_df.empty and not index_df.empty:
    merged_df = pd.merge(
        index_df.drop(columns=["_id"], errors="ignore"),
        details_df.drop(columns=["_id"], errors="ignore"),
        on="protocolId",
        how="outer",
        suffixes=("", "_y"),
    )
else:
    merged_df = index_df if not index_df.empty else details_df
    st.write("One of the dataframes is empty, using the non-empty one")


# Add vehicle type classification to merged_df
def classify_vehicle_type(callsign):
    if pd.isna(callsign):
        return "Unbekannt"
    callsign_str = str(callsign)
    if "-83-" in callsign_str:
        return "RTW"
    elif "-85-" in callsign_str:
        return "S-KTW"
    else:
        return callsign_str


merged_df["vehicleType"] = merged_df["callSign"].apply(classify_vehicle_type)


# Filter für Einsatzdatum Intervall

# Filter für Einsatzdatum Intervall
st.date_input(
    "Einsatzdatum von-bis",
    value=(pd.to_datetime("2025-01-01T00:00:00"), pd.Timestamp.today()),
    key="date_range",
)

# Get date range from session state
start_date, end_date = st.session_state["date_range"]
# Filter data based on missionDate
if "missionDate" in merged_df.columns:
    # Convert dates to datetime for comparison, handling timezone
    start_dt = pd.to_datetime(start_date)
    end_dt = (
        pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    )  # Include entire end date

    # Strip timezone if present for comparison
    mission_dates = merged_df["missionDate"]
    if mission_dates.dt.tz is not None:
        mission_dates = mission_dates.dt.tz_localize(None)

    filtered_df = merged_df[
        (mission_dates >= start_dt) & (mission_dates <= end_dt)
    ].copy()
else:
    filtered_df = merged_df.copy()
    st.warning("missionDate column not found")

# Select S-KTW based on callSign
if "callSign" in filtered_df.columns:
    available_callsigns = sorted(filtered_df["callSign"].dropna().unique())
    selected_callsigns = st.multiselect(
        "S-KTW auswählen",
        options=available_callsigns,
        default=[
            v.strip() for v in DEFAULT_NIDA_VEHICLES if v.strip() in available_callsigns
        ],
    )

    if selected_callsigns:
        filtered_df = filtered_df[filtered_df["callSign"].isin(selected_callsigns)]
else:
    st.warning("callSign column not found")
    selected_callsigns = []

st.write(f"Gefilterte Daten: {len(filtered_df)} Einträge")
st.write(
    "Berechnung der Auslastung basierend auf StatusAlarm und StatusEnd der NIDA-Protokolle."
)

# Quick view of longest mission durations
if "duration_hours" in filtered_df.columns:
    st.subheader("📊 Top Einsatzdauern (sortiert nach Dauer)")
    longest_missions = filtered_df[
        [
            "protocolId",
            "callSign",
            "StatusAlarm",
            "StatusEnd",
            "duration_hours",
            "statisticMissionType",
        ]
    ].copy()
    longest_missions["duration_hours"] = longest_missions["duration_hours"].round(2)
    longest_missions = longest_missions.sort_values("duration_hours", ascending=False)
    st.dataframe(longest_missions.head(10))

# Show top 10 longest mission durations to identify outliers
if "duration_hours" in filtered_df.columns:
    st.subheader("🔍 Top 10 längste Einsatzdauern (Ausreißer-Check)")
    top_10_longest = filtered_df.nlargest(10, "duration_hours")[
        [
            "protocolId",
            "callSign",
            "StatusAlarm",
            "StatusEnd",
            "duration_hours",
            "statisticMissionType",
        ]
    ].copy()
    top_10_longest["duration_minutes"] = top_10_longest["duration_hours"] * 60
    top_10_longest["duration_hours"] = top_10_longest["duration_hours"].round(2)
    top_10_longest["duration_minutes"] = top_10_longest["duration_minutes"].round(1)

    st.dataframe(
        top_10_longest[
            [
                "protocolId",
                "callSign",
                "StatusAlarm",
                "StatusEnd",
                "duration_hours",
                "duration_minutes",
                "statisticMissionType",
            ]
        ]
    )

    # Show some statistics about durations
    valid_durations = filtered_df["duration_hours"][filtered_df["duration_hours"] > 0]
    if not valid_durations.empty:
        st.write(f"**Statistik der Einsatzdauern:**")
        st.write(f"- Anzahl gültiger Einsätze: {len(valid_durations)}")
        st.write(
            f"- Durchschnittliche Dauer: {valid_durations.mean():.2f} Stunden ({valid_durations.mean()*60:.1f} Minuten)"
        )
        st.write(
            f"- Median Dauer: {valid_durations.median():.2f} Stunden ({valid_durations.median()*60:.1f} Minuten)"
        )
        st.write(
            f"- Maximale Dauer: {valid_durations.max():.2f} Stunden ({valid_durations.max()*60:.1f} Minuten)"
        )
        st.write(
            f"- Minimale Dauer: {valid_durations.min():.2f} Stunden ({valid_durations.min()*60:.1f} Minuten)"
        )

        # Flag suspicious durations
        suspicious = filtered_df[
            filtered_df["duration_hours"] > 24
        ]  # Missions longer than 24 hours
        if not suspicious.empty:
            st.warning(
                f"⚠️ {len(suspicious)} Einsätze dauern länger als 24 Stunden - mögliche Datenfehler!"
            )

# Calculate utilization based on StatusAlarm and StatusEnd
if "StatusAlarm" in filtered_df.columns and "StatusEnd" in filtered_df.columns:
    # Ensure datetime columns
    filtered_df["StatusAlarm"] = pd.to_datetime(
        filtered_df["StatusAlarm"], errors="coerce"
    )
    filtered_df["StatusEnd"] = pd.to_datetime(filtered_df["StatusEnd"], errors="coerce")

    # Calculate duration in hours
    filtered_df["duration_hours"] = (
        filtered_df["StatusEnd"] - filtered_df["StatusAlarm"]
    ).dt.total_seconds() / 3600
    # Filter out invalid durations (negative or NaN)
    filtered_df = filtered_df[filtered_df["duration_hours"] > 0]

    # Define schedules (hours per week)
    schedules = VEHICLE_SCHEDULES

    # Calculate available hours for the selected date range
    date_range = pd.date_range(start=start_date, end=end_date)
    total_days = len(date_range)

    # Calculate daily utilization
    if "StatusAlarm" in filtered_df.columns:
        filtered_df["weekday"] = filtered_df["StatusAlarm"].dt.day_name()

        # Group by callsign and weekday, sum durations
        daily_util = (
            filtered_df.groupby(["callSign", "weekday"])["duration_hours"]
            .sum()
            .reset_index()
        )

        # Define weekday groups: Mon-Thu, Fri, Sat, Sun
        weekday_groups = {
            "Monday": "Mon-Thu",
            "Tuesday": "Mon-Thu",
            "Wednesday": "Mon-Thu",
            "Thursday": "Mon-Thu",
            "Friday": "Fri",
            "Saturday": "Sat",
            "Sunday": "Sun",
        }

        daily_util["group"] = daily_util["weekday"].map(weekday_groups)
        grouped_daily = (
            daily_util.groupby(["callSign", "group"])["duration_hours"]
            .sum()
            .reset_index()
        )

        # Calculate available hours per group
        date_range = pd.date_range(start=start_date, end=end_date)
        weekday_counts = pd.Series(date_range).dt.day_name().value_counts()

        def get_available_hours(group, callsign):
            if callsign not in schedules:
                return 24 * 7  # default
            daily_hours = schedules[callsign] / 7
            if group == "Mon-Thu":
                return daily_hours * (
                    weekday_counts.get("Monday", 0)
                    + weekday_counts.get("Tuesday", 0)
                    + weekday_counts.get("Wednesday", 0)
                    + weekday_counts.get("Thursday", 0)
                )
            elif group == "Fri":
                return daily_hours * weekday_counts.get("Friday", 0)
            elif group == "Sat":
                return daily_hours * weekday_counts.get("Saturday", 0)
            elif group == "Sun":
                return daily_hours * weekday_counts.get("Sunday", 0)
            return 0

        # Create daily dataframe with available and actual hours
        daily_available = []
        for callsign in selected_callsigns:
            for group in ["Mon-Thu", "Fri", "Sat", "Sun"]:
                available = get_available_hours(group, callsign)
                actual_row = grouped_daily[
                    (grouped_daily["callSign"] == callsign)
                    & (grouped_daily["group"] == group)
                ]
                actual = (
                    actual_row["duration_hours"].sum() if not actual_row.empty else 0
                )
                percentage = (actual / available * 100) if available > 0 else 0
                daily_available.append(
                    {
                        "callSign": callsign,
                        "group": group,
                        "available_hours": available,
                        "actual_hours": actual,
                        "percentage": percentage,
                    }
                )

        daily_df = pd.DataFrame(daily_available)

        st.subheader("Tägliche Auslastung")
        st.dataframe(daily_df)

        # Bar chart for daily utilization
        if not daily_df.empty:
            try:
                fig_daily = px.bar(
                    daily_df,
                    x="group",
                    y="percentage",
                    color="callSign",
                    title="Tägliche Auslastung in Prozent",
                    barmode="group",
                )
                st.plotly_chart(fig_daily)
            except Exception as e:
                st.error(f"Fehler beim Erstellen des Diagramms: {e}")
                st.write("Daten für tägliche Auslastung:", daily_df)
else:
    st.warning("StatusAlarm or StatusEnd columns not found")


# Display Einsätze per Weekday and hour of day
st.subheader("Einsätze nach Wochentag und Uhrzeit")

# Mission type filter for this section only
st.write(
    "**Filter für diese Sektion:** Mission Types (Dienstfahrt default ausgeschlossen)"
)
if "missionType" in filtered_df.columns:
    available_mission_types = sorted(filtered_df["missionType"].dropna().unique())
    # Default selection excludes "dienstfahrt"
    default_selected = [
        mt for mt in available_mission_types if "dienstfahrt" not in str(mt).lower()
    ]
    selected_mission_types = st.multiselect(
        "Mission Types für Heatmap filtern",
        options=available_mission_types,
        default=default_selected,  # Exclude Dienstfahrt by default
        key="heatmap_mission_filter",
    )

    if selected_mission_types:
        heatmap_df = filtered_df[
            filtered_df["missionType"].isin(selected_mission_types)
        ].copy()
    else:
        heatmap_df = filtered_df.copy()
        st.info("Alle Mission Types verwendet.")
else:
    heatmap_df = filtered_df.copy()

if "StatusAlarm" in heatmap_df.columns and not heatmap_df.empty:
    filtered_df["weekday"] = filtered_df["StatusAlarm"].dt.day_name()
    filtered_df["hour"] = filtered_df["StatusAlarm"].dt.hour
    heatmap_data = (
        filtered_df.groupby(["weekday", "hour"]).size().reset_index(name="counts")
    )
    if not heatmap_data.empty:
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
    st.warning("StatusAlarm column not found or no data for heatmap")

# Display distribution of statisticMissionType
if "statisticMissionType" in filtered_df.columns:
    mission_type_counts = (
        filtered_df["statisticMissionType"].value_counts().reset_index()
    )
    mission_type_counts.columns = ["Mission Type", "Count"]

    st.subheader("Verteilung nach statisticMissionType")
    if not mission_type_counts.empty:
        fig_mission = px.bar(
            mission_type_counts,
            x="Mission Type",
            y="Count",
            title="Verteilung der statisticMissionType",
        )
        st.plotly_chart(fig_mission)
else:
    st.warning("statisticMissionType column not found")

# Display distribution of statisticMissionType
if "missionType" in filtered_df.columns:
    mission_type_counts = filtered_df["missionType"].value_counts().reset_index()
    mission_type_counts.columns = ["Mission Type", "Count"]

    st.subheader("Verteilung der Mission Types")
    if not mission_type_counts.empty:
        fig_mission = px.bar(
            mission_type_counts,
            x="Mission Type",
            y="Count",
            title="Verteilung der missionType",
        )
        st.plotly_chart(fig_mission)
else:
    st.warning("missionType column not found")

# 🚑 Mission Types für S-KTW Transporte (inkl. RTW)
st.subheader("🚑 S-KTW Mission Types (inkl. RTW-Fahrzeuge)")

# Create broader filter including RTW vehicles for S-KTW mission analysis
if "callSign" in merged_df.columns and "missionType" in merged_df.columns:
    # Filter for date range first (using merged_df to include RTW vehicles)
    if "missionDate" in merged_df.columns:
        mission_dates = merged_df["missionDate"]
        if mission_dates.dt.tz is not None:
            mission_dates = mission_dates.dt.tz_localize(None)

        sktw_analysis_df = merged_df[
            (mission_dates >= start_dt) & (mission_dates <= end_dt)
        ].copy()
    else:
        sktw_analysis_df = merged_df.copy()

    # Filter for S-KTW related mission types
    sktw_missions = sktw_analysis_df[
        sktw_analysis_df["missionType"].str.contains("S-KTW", case=False, na=False)
    ].copy()

    if not sktw_missions.empty:
        # Classify vehicle types based on callSign pattern
        sktw_missions["vehicle_type"] = sktw_missions["callSign"].apply(
            classify_vehicle_type
        )

        # Classify mission types
        def classify_mission_type(mission_type):
            if pd.isna(mission_type):
                return "Unbekannt"
            mission_str = str(mission_type).lower()
            if "s-ktw - transport" in mission_str:
                return "S-KTW – Transport"
            elif (
                "s-ktw - kein transport" in mission_str
                or "kein-transport" in mission_str
            ):
                return "S-KTW – Kein Transport"
            else:
                return "Andere S-KTW"

        sktw_missions["mission_category"] = sktw_missions["missionType"].apply(
            classify_mission_type
        )

        # Create summary table
        summary_df = (
            sktw_missions.groupby(["vehicle_type", "mission_category"])
            .size()
            .reset_index(name="count")
        )

        # Display results
        st.write(f"**Gesamt S-KTW Missionen im Zeitraum:** {len(sktw_missions)}")

        # Table view
        st.subheader("Verteilung nach Fahrzeugtyp und Mission-Art")
        pivot_table = summary_df.pivot_table(
            index="vehicle_type",
            columns="mission_category",
            values="count",
            fill_value=0,
            aggfunc="sum",
        ).reset_index()

        # Add totals
        pivot_table["Gesamt"] = pivot_table.select_dtypes(include=[int, float]).sum(
            axis=1
        )
        st.dataframe(pivot_table)

        # Bar chart
        if not summary_df.empty:
            fig_sktw = px.bar(
                summary_df,
                x="vehicle_type",
                y="count",
                color="mission_category",
                title="S-KTW Missionen nach Fahrzeugtyp und Kategorie",
                barmode="group",
                labels={
                    "vehicle_type": "Fahrzeugtyp",
                    "count": "Anzahl Missionen",
                    "mission_category": "Mission-Kategorie",
                },
            )
            st.plotly_chart(fig_sktw)
    else:
        st.warning("Keine S-KTW Missionen im ausgewählten Zeitraum gefunden")
else:
    st.warning("callSign oder missionType Spalten nicht gefunden für S-KTW Analyse")


st.subheader("Hypothesentests")

st.write(
    "Durch die Einführung von S-KTW werden Notfallsanitäter auf RTW häufiger (in Relation zu ihrer Arbeitszeit) mit erweiterten Versorgungsmaßnehmen (EVM) beaufschlagt."
)

st.write(
    "**Hinweis:** Die detaillierte EVM-Analyse wurde in die separate Seite '6.2 EVM Analyse' verschoben."
)
