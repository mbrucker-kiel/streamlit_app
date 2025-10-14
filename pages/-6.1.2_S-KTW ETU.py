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


# Load Feiertage (holidays) early for use in filters and weekday assignment
wochenfeiertage = data_loading("Feiertage", limit=100)
if not wochenfeiertage.empty:
    holiday_col = wochenfeiertage.columns[0]
    holiday_dates = pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date.dropna().unique()
else:
    holiday_dates = []


# Load configuration from environment variables
DEFAULT_VEHICLES = os.getenv("DEFAULT_SKTW_VEHICLES").split(",")

VEHICLE_CONFIG = os.getenv("VEHICLE_CONFIG")
VEHICLE_SCHEDULES = {}

for config in VEHICLE_CONFIG.split(","):
    if ":" in config:
        vehicle, hours = config.split(":", 1)
        VEHICLE_SCHEDULES[f"Ret SL {vehicle.strip()}"] = int(hours.strip())

st.markdown(
    """
# 🚑 S-KTW ETÜ Analyse

Dieses Dashboard analysiert die ETÜ-Daten für S-KTWs (Sofort-Krankentransportwagen).
"""
)

# --- Wochenfeiertage Markdown Table (inside main markdown element) ---
if not wochenfeiertage.empty:
    holiday_col = wochenfeiertage.columns[0]
    if len(wochenfeiertage.columns) > 1:
        holiday_name_col = wochenfeiertage.columns[1]
    else:
        holiday_name_col = None

    # Use date range from above
    try:
        holidays_in_range_df = wochenfeiertage[
            (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date >= start_date_only)
            & (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date <= end_date_only)
        ].copy()
    except Exception:
        holidays_in_range_df = pd.DataFrame()

    if not holidays_in_range_df.empty:
        holidays_in_range_df["Datum"] = pd.to_datetime(holidays_in_range_df[holiday_col], errors="coerce").dt.strftime("%d.%m.%Y")
        if holiday_name_col:
            holidays_in_range_df["Feiertag"] = holidays_in_range_df[holiday_name_col]
            display_cols = ["Datum", "Feiertag"]
        else:
            display_cols = ["Datum"]
        # Build markdown table
        table_md = "| Datum | Feiertag |\n|---|---|\n" if holiday_name_col else "| Datum |\n|---|\n"
        for _, row in holidays_in_range_df.iterrows():
            if holiday_name_col:
                table_md += f"| {row['Datum']} | {row['Feiertag']} |\n"
            else:
                table_md += f"| {row['Datum']} |\n"
        st.markdown(f"""
> **Hinweis:** Im ausgewählten Zeitraum sind folgende Wochenfeiertage enthalten ({len(holidays_in_range_df)}):

{table_md}
""")
    else:
        st.markdown(
            "> **Hinweis:** Keine Wochenfeiertage im ausgewählten Zeitraum."
        )
else:
    st.markdown(
        "> **Hinweis:** Keine Wochenfeiertage-Daten geladen."
    )

etu_df = data_loading("ETÜ", limit=25000)

# Filter für Einsatzdatum Intervall
st.date_input(
    "Einsatzdatum von-bis",
    value=(pd.to_datetime("2025-01-01T00:00:00"), pd.Timestamp.today()),
    key="date_range",
)

# Get date range from session state
start_date, end_date = st.session_state["date_range"]

# Convert dates to datetime for comparison, handling timezone
start_dt = pd.to_datetime(start_date)
end_dt = (
    pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
)  # Include entire end date

# Filter ETÜ data based on date range first
if "EINSATZDATUM" in etu_df.columns:
    etu_df["EINSATZDATUM"] = pd.to_datetime(etu_df["EINSATZDATUM"], errors="coerce")
    start_date_only = pd.to_datetime(start_date).date()
    end_date_only = pd.to_datetime(end_date).date()
    filtered_df = etu_df[
        (etu_df["EINSATZDATUM"].dt.date >= start_date_only)
        & (etu_df["EINSATZDATUM"].dt.date <= end_date_only)
    ].copy()
else:
    filtered_df = etu_df.copy()
    st.warning("EINSATZDATUM Spalte nicht gefunden - verwende alle Daten")

# --- Wochenfeiertage Note Below Markdown Container (moved after date range vars) ---
if not wochenfeiertage.empty:
    holiday_col = wochenfeiertage.columns[0]
    if len(wochenfeiertage.columns) > 1:
        holiday_name_col = wochenfeiertage.columns[1]
    else:
        holiday_name_col = None

    holidays_in_range_df = wochenfeiertage[
        (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date >= start_date_only)
        & (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date <= end_date_only)
    ].copy()

    if not holidays_in_range_df.empty:
        holidays_in_range_df["Datum"] = pd.to_datetime(holidays_in_range_df[holiday_col], errors="coerce").dt.strftime("%d.%m.%Y")
        if holiday_name_col:
            holidays_in_range_df["Feiertag"] = holidays_in_range_df[holiday_name_col]
            display_cols = ["Datum", "Feiertag"]
        else:
            display_cols = ["Datum"]
        st.markdown(
            f"""
> **Hinweis:** Im ausgewählten Zeitraum sind folgende Wochenfeiertage enthalten ({len(holidays_in_range_df)}):
"""
        )
        st.dataframe(holidays_in_range_df[display_cols].reset_index(drop=True))
    else:
        st.markdown(
            "> **Hinweis:** Keine Wochenfeiertage im ausgewählten Zeitraum."
        )
else:
    st.markdown(
        "> **Hinweis:** Keine Wochenfeiertage-Daten geladen."
    )

etu_df = data_loading("ETÜ", limit=25000)

# Filter für Einsatzdatum Intervall
st.date_input(
    "Einsatzdatum von-bis",
    value=(pd.to_datetime("2025-01-01T00:00:00"), pd.Timestamp.today()),
    key="date_range_2",
)

# Get date range from session state
start_date, end_date = st.session_state["date_range"]

# Convert dates to datetime for comparison, handling timezone
start_dt = pd.to_datetime(start_date)
end_dt = (
    pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
)  # Include entire end date

# Filter ETÜ data based on date range first
if "EINSATZDATUM" in etu_df.columns:
    etu_df["EINSATZDATUM"] = pd.to_datetime(etu_df["EINSATZDATUM"], errors="coerce")
    start_date_only = pd.to_datetime(start_date).date()
    end_date_only = pd.to_datetime(end_date).date()
    filtered_df = etu_df[
        (etu_df["EINSATZDATUM"].dt.date >= start_date_only)
        & (etu_df["EINSATZDATUM"].dt.date <= end_date_only)
    ].copy()
else:
    filtered_df = etu_df.copy()
    st.warning("EINSATZDATUM Spalte nicht gefunden - verwende alle Daten")

# Select S-KTW based on EINSATZMITTEL
if "EINSATZMITTEL" in filtered_df.columns:
    available_vehicles = sorted(filtered_df["EINSATZMITTEL"].dropna().unique())
    selected_vehicles = st.multiselect(
        "S-KTW auswählen",
        options=available_vehicles,
        default=[
            v.strip() for v in DEFAULT_VEHICLES if v.strip() in available_vehicles
        ],
    )

    if selected_vehicles:
        filtered_df = filtered_df[filtered_df["EINSATZMITTEL"].isin(selected_vehicles)]
else:
    st.warning("EINSATZMITTEL column not found")
    selected_vehicles = []

st.write(f"Gefilterte ETÜ-Daten: {len(filtered_df)} Einträge")


st.subheader("Auslastung der S-KTW Fahrzeuge")

# Define schedules (hours per week)
schedules = VEHICLE_SCHEDULES

# please display the auslastung like in the following Mon-Thu, Fri, Sat, Sun
weekday_groups = {
    "Monday": "Mon-Thu",
    "Tuesday": "Mon-Thu",
    "Wednesday": "Mon-Thu",
    "Thursday": "Mon-Thu",
    "Friday": "Fri",
    "Saturday": "Sat",
    "Sunday": "Sun",
}

# Calculate utilization for selected vehicles
if selected_vehicles and not filtered_df.empty:
    # Ensure we have the required columns
    required_cols = ["EINSATZBEGINN", "EINSATZENDE", "EINSATZMITTEL"]
    if all(col in filtered_df.columns for col in required_cols):

        # Convert datetime columns if needed
        filtered_df = filtered_df.copy()
        filtered_df["EINSATZBEGINN"] = pd.to_datetime(
            filtered_df["EINSATZBEGINN"], errors="coerce"
        )
        filtered_df["EINSATZENDE"] = pd.to_datetime(
            filtered_df["EINSATZENDE"], errors="coerce"
        )

        # Remove rows with invalid datetime data
        valid_missions = filtered_df.dropna(
            subset=["EINSATZBEGINN", "EINSATZENDE"]
        ).copy()

        if not valid_missions.empty:
            # Calculate mission duration in hours
            valid_missions["mission_duration_hours"] = (
                valid_missions["EINSATZENDE"] - valid_missions["EINSATZBEGINN"]
            ).dt.total_seconds() / 3600

            # Filter out negative or unrealistic durations 
            valid_missions = valid_missions[
                valid_missions["mission_duration_hours"] > 0
            ]

            # Add weekday information, treat holidays as 'Wochenfeiertag'
            valid_missions["mission_date"] = valid_missions["EINSATZBEGINN"].dt.date
            valid_missions["weekday"] = valid_missions["EINSATZBEGINN"].dt.day_name()
            valid_missions["weekday_group"] = valid_missions.apply(
                lambda row: "Wochenfeiertag" if row["mission_date"] in holiday_dates else weekday_groups.get(row["weekday"], row["weekday"]),
                axis=1
            )

            # Calculate total available hours for the selected period
            date_range_days = (end_date - start_date).days + 1

            # Calculate utilization by vehicle and weekday group
            utilization_data = []

            for vehicle in selected_vehicles:
                vehicle_data = valid_missions[
                    valid_missions["EINSATZMITTEL"] == vehicle
                ]

                if not vehicle_data.empty:
                    # Get vehicle schedule (hours per week)
                    vehicle_short = vehicle
                    weekly_hours = schedules.get(
                        vehicle_short, 168
                    )  # Default to 24/7 if not found

                    # Calculate total available hours for the period
                    total_available_hours = (weekly_hours / 7) * date_range_days

                    # Calculate total mission hours
                    total_mission_hours = vehicle_data["mission_duration_hours"].sum()

                    # Calculate utilization percentage
                    utilization_pct = (
                        (total_mission_hours / total_available_hours * 100)
                        if total_available_hours > 0
                        else 0
                    )

                    # Group by weekday for detailed analysis
                    weekday_stats = (
                        vehicle_data.groupby("weekday_group")
                        .agg({"mission_duration_hours": "sum", "AUFTRAGS_NR": "count"})
                        .round(2)
                    )

                    utilization_data.append(
                        {
                            "vehicle": vehicle,
                            "total_available_hours": round(total_available_hours, 1),
                            "total_mission_hours": round(total_mission_hours, 1),
                            "utilization_pct": round(utilization_pct, 1),
                            "total_missions": len(vehicle_data),
                            "weekday_stats": weekday_stats,
                        }
                    )

            if utilization_data:
                # Display overall utilization summary
                st.write("### Gesamtauslastung")
                summary_cols = st.columns(len(utilization_data))

                for i, data in enumerate(utilization_data):
                    with summary_cols[i]:
                        st.metric(
                            label=f"{data['vehicle']}",
                            value=f"{data['utilization_pct']}%",
                            delta=f"{data['total_mission_hours']}h / {data['total_available_hours']}h verfügbar",
                        )

                # Display detailed weekday breakdown
                st.write("### Wochentag-Auslastung")

                for data in utilization_data:
                    with st.expander(f"📊 {data['vehicle']} - Detailansicht"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Stunden nach Wochentag:**")
                            # Calculate available hours per weekday group
                            vehicle_short = data["vehicle"]
                            weekly_hours = schedules.get(vehicle_short, 168)

                            # Ensure all comparisons are between date objects
                            holiday_dates_set = set(pd.to_datetime(holiday_dates).date)
                            start_date_obj = start_dt.date()
                            end_date_obj = end_dt.date()
                            # Filter holidays in range
                            holidays_in_range = [d for d in holiday_dates_set if start_date_obj <= d <= end_date_obj]
                            num_holidays = len(holidays_in_range)
                            # Count number of each weekday in the selected range
                            date_range = pd.date_range(start=start_dt, end=end_dt)
                            weekday_counts = date_range.day_name().value_counts().to_dict()
                            # Remove holidays from their respective weekday count
                            holiday_weekdays = [d.strftime("%A") for d in holidays_in_range]
                            weekday_counts_holiday = weekday_counts.copy()
                            for hw in holiday_weekdays:
                                if hw in weekday_counts_holiday:
                                    weekday_counts_holiday[hw] -= 1
                            # Calculate available hours per group
                            weekday_available = {
                                "Mon-Thu": (weekly_hours / 7) * sum(weekday_counts_holiday.get(day, 0) for day in ["Monday", "Tuesday", "Wednesday", "Thursday"]),
                                "Fri": (weekly_hours / 7) * weekday_counts_holiday.get("Friday", 0),
                                "Sat": (weekly_hours / 7) * weekday_counts_holiday.get("Saturday", 0),
                                "Sun": (weekly_hours / 7) * weekday_counts_holiday.get("Sunday", 0),
                                "Wochenfeiertag": (weekly_hours / 7) * num_holidays,  # treat as Saturday
                            }

                            weekday_df = data["weekday_stats"].copy()
                            for weekday in ["Mon-Thu", "Fri", "Sat", "Sun", "Wochenfeiertag"]:
                                if weekday in weekday_df.index:
                                    available = weekday_available.get(weekday, 0)
                                    used = weekday_df.loc[weekday, "mission_duration_hours"]
                                    pct = (used / available * 100) if available > 0 else 0
                                    weekday_df.loc[weekday, "available_hours"] = round(available, 1)
                                    weekday_df.loc[weekday, "utilization_pct"] = round(pct, 1)
                                else:
                                    weekday_df.loc[weekday, "available_hours"] = round(weekday_available.get(weekday, 0), 1)
                                    weekday_df.loc[weekday, "utilization_pct"] = 0
                                    weekday_df.loc[weekday, "mission_duration_hours"] = 0
                                    weekday_df.loc[weekday, "AUFTRAGS_NR"] = 0

                            # Reorder columns
                            weekday_df = weekday_df[[
                                "mission_duration_hours",
                                "available_hours",
                                "utilization_pct",
                                "AUFTRAGS_NR",
                            ]]
                            weekday_df.columns = [
                                "Einsatz-Stunden",
                                "Verfügbare Stunden",
                                "Auslastung %",
                                "Anzahl Einsätze",
                            ]


                            st.dataframe(
                                weekday_df.style.format({
                                    "Einsatz-Stunden": "{:.1f}",
                                    "Verfügbare Stunden": "{:.1f}",
                                    "Auslastung %": "{:.1f}%",
                                    "Anzahl Einsätze": "{:.0f}",
                                })
                            )

                            # Group missions by hour of day and for Feiertage detail
                            valid_missions_vehicle = valid_missions[
                                valid_missions["EINSATZMITTEL"] == data["vehicle"]
                            ].copy()

                            # Feiertage detail: show mission hours per holiday for this vehicle
                            if not wochenfeiertage.empty and num_holidays > 0:
                                with st.expander("🗓️ Wochenfeiertage - Detailansicht"):
                                    # Prepare holiday detail table for selected vehicle
                                    holiday_col = wochenfeiertage.columns[0]
                                    if len(wochenfeiertage.columns) > 1:
                                        holiday_name_col = wochenfeiertage.columns[1]
                                    else:
                                        holiday_name_col = None
                                    holidays_in_range_df = wochenfeiertage[
                                        (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date >= start_date_obj)
                                        & (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date <= end_date_obj)
                                    ].copy()
                                    holidays_in_range_df["Datum"] = pd.to_datetime(holidays_in_range_df[holiday_col], errors="coerce").dt.strftime("%d.%m.%Y")
                                    if holiday_name_col:
                                        holidays_in_range_df["Feiertag"] = holidays_in_range_df[holiday_name_col]
                                    # For each holiday, calculate total mission hours for this vehicle
                                    holiday_mission_hours = []
                                    for _, hrow in holidays_in_range_df.iterrows():
                                        h_date = pd.to_datetime(hrow[holiday_col], errors="coerce").date()
                                        missions_on_holiday = valid_missions_vehicle[
                                            valid_missions_vehicle["EINSATZBEGINN"].dt.date == h_date
                                        ]
                                        total_hours = missions_on_holiday["mission_duration_hours"].sum()
                                        holiday_mission_hours.append({
                                            "Datum": hrow["Datum"],
                                            "Feiertag": hrow["Feiertag"] if holiday_name_col else "",
                                            "Einsatz-Stunden": round(total_hours, 2),
                                            "Anzahl Einsätze": len(missions_on_holiday),
                                        })
                                    # Display as dataframe
                                    feiertag_df = pd.DataFrame(holiday_mission_hours)
                                    if not feiertag_df.empty:
                                        st.write("**Einsatzstunden je Wochenfeiertag für dieses Fahrzeug:**")
                                        st.dataframe(feiertag_df)
                                    else:
                                        st.info("Keine Einsätze an Wochenfeiertagen für dieses Fahrzeug im Zeitraum.")

                        with col2:
                            st.write("**Einsätze nach Stunde:**")
                            valid_missions_vehicle["hour"] = valid_missions_vehicle[
                                "EINSATZBEGINN"
                            ].dt.hour

                            hourly_missions = (
                                valid_missions_vehicle.groupby("hour")
                                .size()
                                .reset_index(name="count")
                            )
                            hourly_missions.columns = ["Stunde", "Anzahl Einsätze"]

                            # Fill missing hours with 0
                            all_hours = pd.DataFrame({"Stunde": range(24)})
                            hourly_missions = all_hours.merge(
                                hourly_missions, on="Stunde", how="left"
                            ).fillna(0)

                            st.bar_chart(hourly_missions.set_index("Stunde"))
            else:
                st.warning(
                    "Keine gültigen Einsatzdaten für die ausgewählten Fahrzeuge gefunden."
                )
        else:
            st.warning(
                "Keine gültigen Einsatzdaten mit Beginn- und Endzeiten gefunden."
            )
    else:
        st.warning(
            f"Erforderliche Spalten fehlen: {', '.join([col for col in required_cols if col not in filtered_df.columns])}"
        )
else:
    st.info("Wählen Sie Fahrzeuge aus, um die Auslastungsanalyse zu sehen.")

# Display Feiertage dataframe after utilization analysis (optional)

# --- Wochenfeiertage Context & Calculation ---
st.subheader("Wochenfeiertage im ausgewählten Zeitraum")

# Try to extract holiday name column if present (assume second column is name)
if not wochenfeiertage.empty:
    holiday_col = wochenfeiertage.columns[0]
    if len(wochenfeiertage.columns) > 1:
        holiday_name_col = wochenfeiertage.columns[1]
    else:
        holiday_name_col = None

    # Filter holidays in selected date range
    holidays_in_range_df = wochenfeiertage[
        (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date >= start_date_only)
        & (pd.to_datetime(wochenfeiertage[holiday_col], errors="coerce").dt.date <= end_date_only)
    ].copy()

    # Prepare display table
    if not holidays_in_range_df.empty:
        holidays_in_range_df["Datum"] = pd.to_datetime(holidays_in_range_df[holiday_col], errors="coerce").dt.strftime("%d.%m.%Y")
        if holiday_name_col:
            holidays_in_range_df["Feiertag"] = holidays_in_range_df[holiday_name_col]
            display_cols = ["Datum", "Feiertag", "weekday"]
        else:
            display_cols = ["Datum"]
        st.write(f"Im ausgewählten Zeitraum sind folgende Wochenfeiertage enthalten ({len(holidays_in_range_df)}):")
        st.dataframe(holidays_in_range_df[display_cols].reset_index(drop=True))
    else:
        st.info("Keine Wochenfeiertage im ausgewählten Zeitraum.")
else:
    st.info("Keine Wochenfeiertage-Daten geladen.")

st.subheader("Einsatzstichworte")

# sankey diagramm SZENARIO_BEGINN, SZENARIO_ABSCHLUSS
if not filtered_df.empty and selected_vehicles:
    # Check for scenario columns
    if (
        "SZENARIO_BEGINN" in filtered_df.columns
        and "SZENARIO_ABSCHLUSS" in filtered_df.columns
    ):
        # Prepare data for Sankey diagram
        sankey_data = filtered_df[["SZENARIO_BEGINN", "SZENARIO_ABSCHLUSS"]].copy()
        sankey_data = sankey_data.dropna()  # Remove rows with missing scenario data
        if not sankey_data.empty:
            # Count transitions between scenarios
            transitions = (
                sankey_data.groupby(["SZENARIO_BEGINN", "SZENARIO_ABSCHLUSS"])
                .size()
                .reset_index(name="count")
            )

            # Create unique list of all scenarios for node indices
            all_scenarios = list(
                set(
                    transitions["SZENARIO_BEGINN"].tolist()
                    + transitions["SZENARIO_ABSCHLUSS"].tolist()
                )
            )
            scenario_to_index = {
                scenario: i for i, scenario in enumerate(all_scenarios)
            }

            # Prepare Sankey diagram data
            source_indices = [
                scenario_to_index[scenario]
                for scenario in transitions["SZENARIO_BEGINN"]
            ]
            target_indices = [
                scenario_to_index[scenario]
                for scenario in transitions["SZENARIO_ABSCHLUSS"]
            ]
            values = transitions["count"].tolist()

            # Create node labels with counts
            node_labels = []
            for scenario in all_scenarios:
                begin_count = transitions[transitions["SZENARIO_BEGINN"] == scenario][
                    "count"
                ].sum()
                end_count = transitions[transitions["SZENARIO_ABSCHLUSS"] == scenario][
                    "count"
                ].sum()
                total_count = begin_count + end_count
                node_labels.append(f"{scenario}<br>({total_count} Einsätze)")

            # Create Sankey diagram
            fig = dict(
                type="sankey",
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=node_labels,
                    color="lightblue",
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=values,
                    label=[f"{count} Einsätze" for count in values],
                ),
            )

            layout = dict(
                title="Szenario-Veränderungen von Beginn zu Abschluss",
                font=dict(size=10),
            )

            # Sankey diagram removed - keeping only the transition table

            # Show summary statistics
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Häufigste Einsatzstichworte (Beginn):**")
                begin_counts = sankey_data["SZENARIO_BEGINN"].value_counts().head(10)
                st.dataframe(begin_counts.to_frame("Anzahl"))

            with col2:
                st.write("**Häufigste Einsatzstichworte (Abschluss):**")
                end_counts = sankey_data["SZENARIO_ABSCHLUSS"].value_counts().head(10)
                st.dataframe(end_counts.to_frame("Anzahl"))

            # Show most common transitions
            st.write("**Häufigste Szenario-Übergänge:**")
            top_transitions = transitions.nlargest(10, "count")
            top_transitions.columns = ["Von", "Nach", "Anzahl"]
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
    available_colors = [
        "blue",
        "red",
        "green",
        "purple",
        "orange",
        "darkred",
        "lightred",
        "beige",
        "darkblue",
        "darkgreen",
        "cadetblue",
        "darkpurple",
        "white",
        "pink",
        "lightblue",
        "lightgreen",
        "gray",
        "black",
        "lightgray",
    ]

    # Create color mapping dictionary
    color_map = {}
    color_columns = st.columns(len(selected_vehicles))

    for i, vehicle in enumerate(selected_vehicles):
        with color_columns[i]:
            default_color = available_colors[i % len(available_colors)]
            color_map[vehicle] = st.selectbox(
                f"Farbe für {vehicle}",
                options=available_colors,
                index=(
                    available_colors.index(default_color)
                    if default_color in available_colors
                    else 0
                ),
                key=f"color_{vehicle}",
            )


# create filter for STATUS_BEI_ALARMIERUNG
if "STATUS_BEI_ALARMIERUNG" in filtered_df.columns:
    status_options = sorted(filtered_df["STATUS_BEI_ALARMIERUNG"].dropna().unique())
    selected_status = st.multiselect(
        "STATUS_BEI_ALARMIERUNG filtern (optional)",
        options=status_options,
        default=[],
        key="status_filter",
    )

    if selected_status:
        filtered_df = filtered_df[
            filtered_df["STATUS_BEI_ALARMIERUNG"].isin(selected_status)
        ]
        st.write(
            "Gefilterte ETÜ-Daten nach STATUS_BEI_ALARMIERUNG: "
            f"{len(filtered_df)} Einträge"
        )
else:
    st.warning("STATUS_BEI_ALARMIERUNG Spalte nicht gefunden - verwende alle Daten")

# create filter for CEDUS_CODE
if "CEDUS_CODE" in filtered_df.columns:
    cedus_codes = sorted(filtered_df["CEDUS_CODE"].dropna().unique())
    selected_cedus = st.multiselect(
        "CEDUS_CODE filtern (optional)",
        options=cedus_codes,
        default=[],
        key="cedus_filter",
    )

    if selected_cedus:
        filtered_df = filtered_df[filtered_df["CEDUS_CODE"].isin(selected_cedus)]
        st.write(f"Gefilterte ETÜ-Daten nach CEDUS_CODE: {len(filtered_df)} Einträge")
else:
    st.warning("CEDUS_CODE Spalte nicht gefunden - verwende alle Daten")


# Geo-Mapping section using filtered data (only selected vehicles)
if not filtered_df.empty and selected_vehicles:
    # Check for coordinate columns
    if "EO_X_KOORD" in filtered_df.columns and "EO_Y_KOORD" in filtered_df.columns:
        # Remove rows with missing coordinates
        geo_valid_df = filtered_df.dropna(subset=["EO_X_KOORD", "EO_Y_KOORD"]).copy()

        if not geo_valid_df.empty:
            # Try to convert coordinates to lat/lon for mapping
            # Assuming UTM Zone 32N (common for Germany) - adjust zone if needed
            import pyproj

            try:
                # Define UTM to WGS84 transformer (Zone 32N)
                utm_to_wgs84 = pyproj.Transformer.from_crs(
                    "EPSG:32632", "EPSG:4326", always_xy=True
                )

                # Convert coordinates
                lon_coords, lat_coords = utm_to_wgs84.transform(
                    geo_valid_df["EO_X_KOORD"].values, geo_valid_df["EO_Y_KOORD"].values
                )

                geo_valid_df = geo_valid_df.copy()
                geo_valid_df["latitude"] = lat_coords
                geo_valid_df["longitude"] = lon_coords

                # Use folium for colored map based on vehicle type
                st.subheader("🗺️ Karte der Einsatzorte")

                try:
                    import folium
                    from streamlit_folium import st_folium
                    from folium.features import DivIcon

                    # Debug: Show unique vehicle names
                    unique_vehicles = geo_valid_df["EINSATZMITTEL"].unique()

                    # Calculate center of all points
                    center_lat = geo_valid_df["latitude"].mean()
                    center_lon = geo_valid_df["longitude"].mean()

                    # Create folium map
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

                    # Add markers for each mission location
                    for idx, row in geo_valid_df.iterrows():
                        vehicle = str(row["EINSATZMITTEL"])
                        color = color_map.get(
                            vehicle, "red"
                        )  # Use user-defined colors, default to red

                        # Get status for marker shape differentiation
                        status = str(row.get("STATUS_BEI_ALARMIERUNG", "Unknown"))
                        
                        # Create popup with protocol ID and other details
                        lat_str = f"{row['latitude']:.4f}" if 'latitude' in row and pd.notnull(row['latitude']) else "N/A"
                        lon_str = f"{row['longitude']:.4f}" if 'longitude' in row and pd.notnull(row['longitude']) else "N/A"
                        popup_text = f"""
                        <b>Fahrzeug:</b> {vehicle}<br>
                        <b>AUFTRAGS_NR:</b> {row.get('AUFTRAGS_NR')}<br>
                        <b>Datum</b> {row.get('EINSATZDATUM', 'N/A')}<br>
                        <b>Stichwort</b> {row.get('SZENARIO_BEGINN', 'N/A')}<br>
                        <b>CDUS_CODE:</b> {row.get('CEDUS_CODE', 'N/A')}<br>
                        <b>Lat:</b> {lat_str}<br>
                        <b>Lon:</b> {lon_str}
                        """
                        
                        # Define marker shapes based on status
                        if status == "1 Einsatzbereit Funk":  # triangle marker
                            # Create a triangle div icon using CSS borders
                            icon_html = (
                                f'<div style="width: 0; height: 0; '
                                f'border-left: 8px solid transparent; '
                                f'border-right: 8px solid transparent; '
                                f'border-bottom: 16px solid {color};"></div>'
                            )
                            icon = DivIcon(html=icon_html)
                            marker = folium.Marker(
                                location=[row["latitude"], row["longitude"]],
                                icon=icon,
                                popup=popup_text,
                                tooltip=f"{vehicle} - {status}",
                            )
                        elif status == "2 Einsatzbereit Wache":  # circle marker
                            marker = folium.CircleMarker(
                                location=[row["latitude"], row["longitude"]],
                                radius=6,
                                color=color,
                                fill=True,
                                fill_color=color,
                                fill_opacity=0.9,
                                popup=popup_text,
                                tooltip=f"{vehicle} - {status}",
                            )
                        else:  # Default to rectangle marker for other statuses
                            # Create a rectangle div icon
                            icon_html = (
                                '<div style="width: 12px; height: 8px; '
                                f'background-color: {color}; border: 1px solid black;"></div>'
                            )
                            icon = DivIcon(html=icon_html)
                            marker = folium.Marker(
                                location=[row["latitude"], row["longitude"]],
                                icon=icon,
                                popup=popup_text,
                                tooltip=f"{vehicle} - {status}",
                            )
                        
                        marker.add_to(m)

                    # Create dynamic legend based on user color selections
                    legend_html = (
                        "<div style='position: fixed; bottom: 5px; left: 5px; width: 200px; height: auto; background-color: white; border: 2px solid grey; z-index: 9999; font-size: 12px; padding: 10px; border-radius: 5px; color: black;'>"
                        "<div style='font-weight: bold; margin-bottom: 8px; color: black;'>Fahrzeug-Farben:</div>"
                    )

                    for vehicle, color in color_map.items():
                        vehicle_short = vehicle
                        legend_html += f"<div style='display: flex; align-items: center; margin-bottom: 4px;'><div style='width: 12px; height: 12px; background-color: {color}; border-radius: 50%; margin-right: 8px;'></div><span style='color: black;'>{vehicle_short}</span></div>"

                    # Add status/shape legend
                    legend_html += "<div style='font-weight: bold; margin-top: 12px; margin-bottom: 8px; color: black;'>Status bei Alarmierung:</div>"
                    legend_html += "<div style='display: flex; align-items: center; margin-bottom: 4px;'><div style='width: 12px; height: 12px; background-color: gray; border-radius: 50%; margin-right: 8px;'></div><span style='color: black;'>2 Einsatzbereit Wache</span></div>"
                    legend_html += "<div style='display: flex; align-items: center; margin-bottom: 4px;'><div style='width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-bottom: 16px solid gray; margin-right: 8px;'></div><span style='color: black;'>1 Einsatzbereit Funk</span></div>"
                    legend_html += "<div style='display: flex; align-items: center; margin-bottom: 4px;'><div style='width: 12px; height: 8px; background-color: gray; border: 1px solid black; margin-right: 8px;'></div><span>Andere Status</span></div>"
                    legend_html += "</div>"
                    m.get_root().html.add_child(folium.Element(legend_html))

                    # Display the map - PREVENT RERUNS when zooming/panning
                    st_folium(m, height=800, returned_objects=[], use_container_width=True)
                    st.write(
                        f"**Einsatzorte auf Karte:** {len(geo_valid_df)} Punkte angezeigt"
                    )

                except ImportError:
                    st.warning(
                        "folium oder streamlit-folium nicht verfügbar - verwende Streamlit-Karte ohne Farbcodierung"
                    )
                    # Fallback to st.map without colors
                    map_data = (
                        geo_valid_df[["latitude", "longitude"]]
                        .rename(columns={"latitude": "lat", "longitude": "lon"})
                        .dropna()
                    )
                    if not map_data.empty:
                        st.map(map_data)
                        st.write(
                            f"**Einsatzorte auf Karte:** {len(map_data)} Punkte angezeigt"
                        )
                    else:
                        st.warning("Keine gültigen Koordinaten für Kartenanzeige")

            except ImportError:
                st.warning(
                    "pyproj nicht verfügbar - verwende Scatter-Plot anstelle von Karte"
                )
            except Exception as e:
                st.warning(
                    f"Koordinatenkonvertierung fehlgeschlagen: {e} - verwende Scatter-Plot"
                )
                st.write(
                    "Falls die Koordinaten bereits in WGS84 sind, können wir sie direkt verwenden."
                )

                # Fallback: check if coordinates might already be lat/lon
                # German lat/lon ranges: lat 47-55, lon 5-16
                if (
                    geo_valid_df["EO_Y_KOORD"].between(47, 55).any()
                    and geo_valid_df["EO_X_KOORD"].between(5, 16).any()
                ):
                    st.write(
                        "Koordinaten scheinen bereits in WGS84 zu sein - verwende st.map"
                    )
                    map_data = (
                        geo_valid_df[["EO_Y_KOORD", "EO_X_KOORD"]]
                        .rename(columns={"EO_Y_KOORD": "lat", "EO_X_KOORD": "lon"})
                        .dropna()
                    )
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
