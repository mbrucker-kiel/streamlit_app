import streamlit as st
import pandas as pd
import plotly.express as px
import os
from data_loading import data_loading

st.header("In Arbeit - noch nicht fertig")

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

st.markdown("# 📊 EVM Analyse")

st.write(
    "Diese Seite analysiert erweiterte Versorgungsmaßnahmen (EVM) in Notfalleinsätzen."
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

st.subheader("Hypothesentests")

st.write(
    "Durch die Einführung von S-KTW werden Notfallsanitäter auf RTW häufiger (in Relation zu ihrer Arbeitszeit) mit erweiterten Versorgungsmaßnehmen (EVM) beaufschlagt."
)

# steps to do this:
# check if nida_index["evmCount"] > 0
# protocols_details -> driverId, driverNumber  ,driverQualification
# details -> codriverId, codriverNumber,codriverQualification
# details -> vehicleType
# matching nida_measures value_11 == "EVM"
# get the driverNumber from measures value_10
# calculate evm per vehicleType and co/driver
# calculate working hours per vehicleType co/driver
# -> evm per 100 working hours for RTW and S-KTW

# Load EVM data
evm_df = data_loading("EVM")

# Filter protocols with EVM count > 0
evm_protocols = index_df[index_df["evmCount"] >= 0]["protocolId"].unique()

# Filter merged_df to EVM protocols with date range filtering (but no vehicle selection)
# Apply the same date filtering as used for filtered_df
if "missionDate" in merged_df.columns:
    mission_dates = merged_df["missionDate"]
    if mission_dates.dt.tz is not None:
        mission_dates = mission_dates.dt.tz_localize(None)

    date_filtered_df = merged_df[
        (mission_dates >= start_dt) & (mission_dates <= end_dt)
    ].copy()

    # Also filter on alarmTime using the same date range
    if "alarmTime" in date_filtered_df.columns:
        alarm_times = pd.to_datetime(date_filtered_df["alarmTime"], errors="coerce")
        if alarm_times.dt.tz is not None:
            alarm_times = alarm_times.dt.tz_localize(None)
        date_filtered_df = date_filtered_df[
            (alarm_times >= start_dt) & (alarm_times <= end_dt)
        ].copy()
else:
    date_filtered_df = merged_df.copy()

evm_merged_df = date_filtered_df[
    date_filtered_df["protocolId"].isin(evm_protocols)
].copy()


evm_merged_df["vehicleType"] = evm_merged_df["callSign"].apply(classify_vehicle_type)

# Differences in descriptions between RTW and S-KTW
evm_with_vehicle = evm_df.merge(
    evm_merged_df[["protocolId", "vehicleType"]], on="protocolId", how="left"
)
rtw_evm = evm_with_vehicle[evm_with_vehicle["vehicleType"] == "RTW"]
sktw_evm = evm_with_vehicle[evm_with_vehicle["vehicleType"] == "S-KTW"]

# Combined comparison chart
if (
    not rtw_evm.empty
    and not sktw_evm.empty
    and "description" in rtw_evm.columns
    and "description" in sktw_evm.columns
):
    st.subheader("Vergleich EVM Beschreibungen: RTW vs S-KTW")
    st.write("RTW Percentage = (Count of EVM description / Total RTW missions) × 100")
    st.write(
        "SKTW Percentage = (Count of EVM description / Total S-KTW missions) × 100"
    )
    # Get description counts for both vehicle types
    rtw_desc_counts = rtw_evm["description"].value_counts().reset_index()
    rtw_desc_counts.columns = ["Description", "Count"]

    sktw_desc_counts = sktw_evm["description"].value_counts().reset_index()
    sktw_desc_counts.columns = ["Description", "Count"]

    # Get top descriptions from both
    rtw_top = rtw_desc_counts.head(15).copy()
    rtw_top["vehicleType"] = "RTW"

    sktw_top = sktw_desc_counts.head(15).copy()
    sktw_top["vehicleType"] = "S-KTW"

    # Combine
    combined_desc = pd.concat([rtw_top, sktw_top], ignore_index=True)

    # Create combined bar chart
    fig_combined = px.bar(
        combined_desc,
        x="Description",
        y="Count",
        color="vehicleType",
        title="EVM Beschreibungen Vergleich: RTW vs S-KTW (Absolut)",
        barmode="group",
        labels={
            "Count": "Anzahl",
            "Description": "Beschreibung",
            "vehicleType": "Fahrzeugtyp",
        },
    )
    fig_combined.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_combined)

    # Alternative: Percentage view (percentage of ALL missions that have this EVM type)
    # Get total missions for each vehicle type in the date range
    total_rtw_missions = date_filtered_df[
        date_filtered_df["callSign"]
        .apply(lambda x: str(x) if pd.notna(x) else "")
        .str.contains("-83-", na=False)
    ].shape[0]

    total_sktw_missions = date_filtered_df[
        date_filtered_df["callSign"]
        .apply(lambda x: str(x) if pd.notna(x) else "")
        .str.contains("-85-", na=False)
    ].shape[0]

    combined_desc["Percentage"] = combined_desc.apply(
        lambda row: (
            (row["Count"] / total_rtw_missions * 100)
            if row["vehicleType"] == "RTW"
            else (row["Count"] / total_sktw_missions * 100)
        ),
        axis=1,
    )

    fig_percent = px.bar(
        combined_desc,
        x="Description",
        y="Percentage",
        color="vehicleType",
        title="EVM Beschreibungen Vergleich: RTW vs S-KTW (Prozentual)",
        barmode="group",
        labels={
            "Percentage": "Prozent (%)",
            "Description": "Beschreibung",
            "vehicleType": "Fahrzeugtyp",
        },
    )
    fig_percent.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_percent)


st.dataframe(evm_with_vehicle)

# EVM Time Series Analysis: Trends and Seasonal Patterns
st.subheader("📈 EVM Zeitreihenanalyse: Trends und saisonale Muster")

if "missionDate" in merged_df.columns:
    # Create time series data for EVM analysis
    mission_dates = merged_df["missionDate"]
    if mission_dates.dt.tz is not None:
        mission_dates = mission_dates.dt.tz_localize(None)

    # Get EVM protocols
    evm_protocols_all = index_df[index_df["evmCount"] > 0]["protocolId"].unique()

    # Filter merged_df to include only EVM protocols
    evm_time_df = merged_df[merged_df["protocolId"].isin(evm_protocols_all)].copy()

    # Add mission type filter for time series
    if "missionType" in evm_time_df.columns:
        available_ts_mission_types = sorted(
            evm_time_df["missionType"].dropna().unique()
        )
        selected_ts_mission_types = st.multiselect(
            "Mission Types für Zeitreihenanalyse filtern",
            options=available_ts_mission_types,
            default=available_ts_mission_types,  # All selected by default
            key="mission_type_time_series_filter",
        )

        if selected_ts_mission_types:
            evm_time_df = evm_time_df[
                evm_time_df["missionType"].isin(selected_ts_mission_types)
            ].copy()
            # Also filter the total missions dataframe to match selected mission types
            total_missions_filtered = merged_df[
                merged_df["missionType"].isin(selected_ts_mission_types)
            ].copy()
        else:
            total_missions_filtered = merged_df.copy()
    else:
        total_missions_filtered = merged_df.copy()

    # Add vehicle type classification
    evm_time_df["vehicleType"] = evm_time_df["callSign"].apply(classify_vehicle_type)

    # Extract time components
    evm_time_df["year"] = evm_time_df["missionDate"].dt.year
    evm_time_df["month"] = evm_time_df["missionDate"].dt.month
    evm_time_df["year_month"] = evm_time_df["missionDate"].dt.to_period("M").astype(str)

    # Group by time periods and vehicle type
    monthly_evm = (
        evm_time_df.groupby(["year_month", "vehicleType"])
        .size()
        .reset_index(name="evm_count")
    )
    monthly_total = (
        total_missions_filtered.assign(
            year_month=total_missions_filtered["missionDate"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby(["year_month", "vehicleType"])["protocolId"]
        .count()
        .reset_index(name="total_missions")
    )
    monthly_evm = monthly_evm.merge(
        monthly_total, on=["year_month", "vehicleType"], how="left"
    )
    monthly_evm["evm_percentage"] = (
        monthly_evm["evm_count"] / monthly_evm["total_missions"] * 100
    )

    fig_monthly = px.line(
        monthly_evm,
        x="year_month",
        y="evm_percentage",
        color="vehicleType",
        title="Monatliche EVM-Rate Entwicklung (gefiltert nach Mission Type)",
        labels={
            "evm_percentage": "EVM-Rate (%)",
            "year_month": "Monat",
            "vehicleType": "Fahrzeugtyp",
        },
    )
    fig_monthly.update_xaxes(tickangle=45)
    st.plotly_chart(fig_monthly)

    # Seasonal analysis
    st.write("### Saisonale Analyse")

    # Add month names for better readability
    monthly_evm["month_name"] = (
        monthly_evm["year_month"]
        .str[-2:]
        .astype(int)
        .map(
            {
                1: "Januar",
                2: "Februar",
                3: "März",
                4: "April",
                5: "Mai",
                6: "Juni",
                7: "Juli",
                8: "August",
                9: "September",
                10: "Oktober",
                11: "November",
                12: "Dezember",
            }
        )
    )

    # Seasonal box plot
    fig_seasonal = px.box(
        monthly_evm,
        x="month_name",
        y="evm_percentage",
        color="vehicleType",
        title="Saisonale EVM-Rate Verteilung nach Monaten (gefiltert nach Mission Type)",
        labels={
            "evm_percentage": "EVM-Rate (%)",
            "month_name": "Monat",
            "vehicleType": "Fahrzeugtyp",
        },
        category_orders={
            "month_name": [
                "Januar",
                "Februar",
                "März",
                "April",
                "Mai",
                "Juni",
                "Juli",
                "August",
                "September",
                "Oktober",
                "November",
                "Dezember",
            ]
        },
    )
    fig_seasonal.update_xaxes(tickangle=45)
    st.plotly_chart(fig_seasonal)

# EVM Percentage by Mission Type
st.write("### EVM-Rate nach Mission Type")

# Filter index_df for date range and calculate EVM percentages by missionType
if (
    "missionDate" in index_df.columns
    and "missionType" in index_df.columns
    and "evmCount" in index_df.columns
):
    # Apply date filtering to index_df
    index_mission_dates = index_df["missionDate"]
    if index_mission_dates.dt.tz is not None:
        index_mission_dates = index_mission_dates.dt.tz_localize(None)

    index_filtered = index_df[
        (index_mission_dates >= start_dt) & (index_mission_dates <= end_dt)
    ].copy()

    if not index_filtered.empty:
        # Use all mission types (no filter needed)
        chart_data = index_filtered.copy()

        # Group by missionType and calculate EVM statistics
        mission_evm_stats = (
            chart_data.groupby("missionType")
            .agg(
                {
                    "evmCount": [
                        "count",
                        lambda x: (x > 0).sum(),
                    ],  # Total missions, missions with EVM
                }
            )
            .reset_index()
        )

        # Flatten column names
        mission_evm_stats.columns = ["missionType", "total_missions", "evm_missions"]

        # Calculate EVM percentage
        mission_evm_stats["evm_percentage"] = (
            mission_evm_stats["evm_missions"]
            / mission_evm_stats["total_missions"]
            * 100
        ).round(2)

        # Sort by EVM percentage descending
        mission_evm_stats = mission_evm_stats.sort_values(
            "evm_percentage", ascending=False
        )

        # Create bar chart
        fig_mission_evm = px.bar(
            mission_evm_stats,
            x="missionType",
            y="evm_percentage",
            title="EVM-Rate nach Mission Type (%)",
            labels={"missionType": "Mission Type", "evm_percentage": "EVM-Rate (%)"},
            color="evm_percentage",
            color_continuous_scale="Reds",
        )
        fig_mission_evm.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig_mission_evm)

        # Display the data table
        st.write("**EVM-Statistiken nach Mission Type:**")
        display_stats = mission_evm_stats.copy()
        display_stats["evm_missions"] = display_stats["evm_missions"].astype(int)
        display_stats["total_missions"] = display_stats["total_missions"].astype(int)
        st.dataframe(display_stats)
    else:
        st.warning("Keine Daten im ausgewählten Zeitraum gefunden.")
else:
    st.warning(
        "Erforderliche Spalten (missionDate, missionType, evmCount) nicht in index_df gefunden."
    )


# EVM Analysis for "Kein Transport" Missions
st.write("### EVM bei 'Kein Transport' Missionen")

# Filter for mission types containing "kein Transport" and analyze EVM usage
if (
    "missionDate" in index_df.columns
    and "missionType" in index_df.columns
    and "evmCount" in index_df.columns
):
    # Apply date filtering to index_df
    index_mission_dates = index_df["missionDate"]
    if index_mission_dates.dt.tz is not None:
        index_mission_dates = index_mission_dates.dt.tz_localize(None)

    index_filtered = index_df[
        (index_mission_dates >= start_dt) & (index_mission_dates <= end_dt)
    ].copy()

    if not index_filtered.empty:
        # Filter for mission types containing "kein Transport"
        kein_transport_missions = index_filtered[
            index_filtered["missionType"].str.contains(
                "kein.?transport", case=False, na=False, regex=True
            )
        ].copy()

        if not kein_transport_missions.empty:
            st.write(
                f"**'Kein Transport' Missionen im Zeitraum:** {len(kein_transport_missions)}"
            )

            # Get EVM data for these missions
            evm_kein_transport = evm_df[
                evm_df["protocolId"].isin(kein_transport_missions["protocolId"])
            ].copy()

            if not evm_kein_transport.empty:
                # Merge with vehicle information
                evm_kein_transport_with_vehicle = evm_kein_transport.merge(
                    merged_df[["protocolId", "callSign", "vehicleType"]],
                    on="protocolId",
                    how="left",
                )

                # Group by vehicle type and calculate EVM statistics
                vehicle_evm_stats = (
                    evm_kein_transport_with_vehicle.groupby("vehicleType")
                    .agg(
                        {
                            "protocolId": "count",  # Total EVM entries per vehicle type
                        }
                    )
                    .reset_index()
                )

                vehicle_evm_stats = vehicle_evm_stats.rename(
                    columns={"protocolId": "evm_entries"}
                )

                # Get total "kein transport" missions per vehicle type
                total_kein_transport_by_vehicle = (
                    kein_transport_missions.merge(
                        merged_df[["protocolId", "vehicleType"]],
                        on="protocolId",
                        how="left",
                    )
                    .groupby("vehicleType")
                    .size()
                    .reset_index(name="total_missions")
                )

                # Merge EVM stats with total missions
                vehicle_evm_stats = vehicle_evm_stats.merge(
                    total_kein_transport_by_vehicle, on="vehicleType", how="right"
                ).fillna(0)

                # Calculate percentage
                vehicle_evm_stats["evm_percentage"] = (
                    vehicle_evm_stats["evm_entries"]
                    / vehicle_evm_stats["total_missions"]
                    * 100
                ).round(2)

                # Display results
                st.write(
                    "**EVM-Nutzung bei 'Kein Transport' Missionen nach Fahrzeugtyp:**"
                )
                st.dataframe(vehicle_evm_stats)

                # Calculate overall percentage
                total_evm_entries = vehicle_evm_stats["evm_entries"].sum()
                total_kein_transport_missions = vehicle_evm_stats[
                    "total_missions"
                ].sum()
                overall_percentage = (
                    (total_evm_entries / total_kein_transport_missions * 100)
                    if total_kein_transport_missions > 0
                    else 0
                )

                st.write(
                    f"**Gesamt EVM-Rate bei 'Kein Transport' Missionen:** {overall_percentage:.2f}%"
                )
                st.write(
                    f"({total_evm_entries} von {total_kein_transport_missions} Missionen hatten EVM-Maßnahmen)"
                )

                # Show detailed EVM descriptions for "kein transport" missions
                if not evm_kein_transport_with_vehicle.empty:
                    st.write("**EVM-Beschreibungen bei 'Kein Transport' Missionen:**")
                    evm_descriptions = (
                        evm_kein_transport_with_vehicle["description"]
                        .value_counts()
                        .reset_index()
                    )
                    evm_descriptions.columns = ["EVM-Beschreibung", "Anzahl"]
                    st.dataframe(evm_descriptions.head(10))  # Show top 10

                    # Display detailed dataframe of missions with EVM but no transport
                    st.write(
                        "**Detailansicht: Missionen mit EVM-Maßnahmen (kein Transport):**"
                    )
                    st.write(
                        "Diese Tabelle zeigt alle Missionen, bei denen erweiterte "
                        "Versorgungsmaßnahmen (EVM) durchgeführt wurden, obwohl "
                        " missionType 'kein Transport' ausgewählt wurde."
                    )

                    # Create detailed dataframe with mission information
                    # First, create a summary of all EVM measures per protocol
                    evm_summary = (
                        evm_kein_transport.groupby("protocolId")
                        .agg(
                            {
                                "description": lambda x: ", ".join(
                                    sorted(set(x.dropna()))
                                ),
                                "type": lambda x: ", ".join(sorted(set(x.dropna()))),
                            }
                        )
                        .reset_index()
                    )
                    evm_summary = evm_summary.rename(
                        columns={
                            "description": "all_evm_measures",
                            "type": "evm_categories",
                        }
                    )

                    detailed_evm_missions = evm_kein_transport_with_vehicle.merge(
                        merged_df[
                            [
                                "protocolId",
                                "missionType",
                                "missionDate",
                                "callSign",
                                "content_destinationFacility",
                            ]
                        ],
                        on="protocolId",
                        how="left",
                    ).merge(evm_summary, on="protocolId", how="left")

                    # Select and reorder columns for display
                    display_columns = [
                        "protocolId",
                        "missionDate",
                        "callSign",
                        "vehicleType",
                        "missionType",
                        "content_destinationFacility",
                        "all_evm_measures",
                        "evm_categories",
                        "description",
                        "applicant",
                        "timestamp",
                    ]
                    available_columns = [
                        col
                        for col in display_columns
                        if col in detailed_evm_missions.columns
                    ]

                    detailed_display = detailed_evm_missions[available_columns].copy()
                    detailed_display = detailed_display.sort_values(
                        "missionDate", ascending=False
                    )

                    st.dataframe(detailed_display)

                    # Summary of EVM types performed
                    st.write(
                        "**Zusammenfassung der EVM-Maßnahmen bei 'Kein Transport' Missionen:**"
                    )

                    # Group by description and vehicle type
                    evm_by_type_vehicle = (
                        detailed_evm_missions.groupby(["description", "vehicleType"])
                        .size()
                        .reset_index(name="count")
                    )

                    evm_by_type_vehicle = evm_by_type_vehicle.sort_values(
                        "count", ascending=False
                    )

                    st.dataframe(evm_by_type_vehicle)

            else:
                st.info("Keine EVM-Daten für 'Kein Transport' Missionen gefunden.")
        else:
            st.info(
                "Keine 'Kein Transport' Missionen im ausgewählten Zeitraum gefunden."
            )
    else:
        st.warning("Keine Daten im ausgewählten Zeitraum gefunden.")
else:
    st.warning("Erforderliche Spalten nicht in index_df gefunden.")


# Vehicle and Mission Type Comparison for EVM %
st.subheader("🚑 Vergleich von Fahrzeugen und Mission Types bezüglich EVM %")

st.write(
    "Vergleichen Sie die EVM-Rate (Prozentsatz der Missionen mit erweiterten "
    "Versorgungsmaßnahmen) zwischen verschiedenen Fahrzeugen und Mission Types."
)

# Time range selection for comparison
comparison_start_date = st.date_input(
    "Vergleichszeitraum von", value=pd.to_datetime("2025-01-01"), key="comparison_start"
)

comparison_end_date = st.date_input(
    "Vergleichszeitraum bis", value=pd.to_datetime("2025-06-01"), key="comparison_end"
)

# Vehicle selection based on callSign
if "callSign" in merged_df.columns:
    # Get available callSigns that contain -83- or -85- (RTW and S-KTW vehicles)
    available_vehicles = sorted(
        [
            cs
            for cs in merged_df["callSign"].dropna().unique()
            if "-83-" in str(cs) or "-85-1" in str(cs)
        ]
    )

    selected_vehicles = st.multiselect(
        "Fahrzeuge auswählen (basierend auf callSign)",
        options=available_vehicles,
        default=available_vehicles,  # All RTW and S-KTW vehicles by default
        key="vehicle_comparison",
    )
else:
    selected_vehicles = []
    st.warning("callSign column not found")

if selected_vehicles and "missionDate" in merged_df.columns:
    # Filter data for comparison time range and selected vehicles
    comparison_dates = merged_df["missionDate"]
    if comparison_dates.dt.tz is not None:
        comparison_dates = comparison_dates.dt.tz_localize(None)

    comparison_df = merged_df[
        (comparison_dates >= pd.to_datetime(comparison_start_date))
        & (comparison_dates <= pd.to_datetime(comparison_end_date))
        & (merged_df["callSign"].isin(selected_vehicles))
    ].copy()

    if not comparison_df.empty:
        # Add mission type filter
        if "missionType" in comparison_df.columns:
            available_mission_types = sorted(
                comparison_df["missionType"].dropna().unique()
            )
            selected_mission_types = st.multiselect(
                "Mission Types filtern",
                options=available_mission_types,
                default=available_mission_types,
                key="mission_type_comparison",
            )

            if selected_mission_types:
                comparison_df = comparison_df[
                    comparison_df["missionType"].isin(selected_mission_types)
                ].copy()
            else:
                st.info("Keine Mission Types ausgewählt.")

        # Calculate total missions per vehicle
        total_missions = (
            comparison_df.groupby("callSign").size().reset_index(name="total_missions")
        )

        # Get protocols with EVM (evmCount > 0)
        evm_protocols = index_df[index_df["evmCount"] > 0]["protocolId"].unique()

        # Calculate missions with EVM per vehicle
        missions_with_evm = (
            comparison_df[comparison_df["protocolId"].isin(evm_protocols)]
            .groupby("callSign")
            .size()
            .reset_index(name="missions_with_evm")
        )

        # Merge total missions with EVM missions
        comparison_stats = total_missions.merge(
            missions_with_evm, on="callSign", how="left"
        ).fillna(0)

        # Calculate EVM percentage
        comparison_stats["evm_percentage"] = (
            comparison_stats["missions_with_evm"]
            / comparison_stats["total_missions"]
            * 100
        ).round(2)

        # Add vehicle type classification
        comparison_stats["vehicleType"] = comparison_stats["callSign"].apply(
            classify_vehicle_type
        )

        # Display results
        st.write(
            f"**Vergleich für Zeitraum {comparison_start_date} - "
            f"{comparison_end_date}:**"
        )
        st.dataframe(comparison_stats)

        # Time series chart for EVM % over time
        st.write("### EVM % Entwicklung über Zeit")

        # Group by month and vehicle
        comparison_df["year_month"] = (
            comparison_df["missionDate"].dt.to_period("M").astype(str)
        )

        # Calculate monthly stats for each vehicle
        monthly_stats = []
        for vehicle in selected_vehicles:
            vehicle_data = comparison_df[comparison_df["callSign"] == vehicle].copy()
            if not vehicle_data.empty:
                monthly_vehicle = (
                    vehicle_data.groupby("year_month")
                    .agg({"protocolId": "count"})  # Total missions per month
                    .reset_index()
                )
                monthly_vehicle = monthly_vehicle.rename(
                    columns={"protocolId": "total_missions"}
                )

                # Missions with EVM per month
                evm_monthly = (
                    vehicle_data[vehicle_data["protocolId"].isin(evm_protocols)]
                    .groupby("year_month")
                    .size()
                    .reset_index(name="missions_with_evm")
                )

                # Merge
                monthly_vehicle = monthly_vehicle.merge(
                    evm_monthly, on="year_month", how="left"
                ).fillna(0)

                # Calculate percentage
                monthly_vehicle["evm_percentage"] = (
                    monthly_vehicle["missions_with_evm"]
                    / monthly_vehicle["total_missions"]
                    * 100
                ).round(2)

                monthly_vehicle["callSign"] = vehicle
                monthly_vehicle["vehicleType"] = classify_vehicle_type(vehicle)

                monthly_stats.append(monthly_vehicle)

        if monthly_stats:
            # Combine all monthly stats
            time_series_df = pd.concat(monthly_stats, ignore_index=True)

            # Sort by year_month
            time_series_df["year_month"] = pd.to_datetime(time_series_df["year_month"])
            time_series_df = time_series_df.sort_values("year_month")

            # Line chart
            fig_time_series = px.line(
                time_series_df,
                x="year_month",
                y="evm_percentage",
                color="callSign",
                title="EVM % Entwicklung über Zeit nach Fahrzeug",
                labels={
                    "year_month": "Monat",
                    "evm_percentage": "EVM %",
                    "callSign": "Fahrzeug",
                },
                markers=True,
            )
            fig_time_series.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_time_series)

        # Bar chart for EVM % by vehicle
        fig_vehicle_comparison = px.bar(
            comparison_stats,
            x="callSign",
            y="evm_percentage",
            color="vehicleType",
            title="EVM % nach Fahrzeug",
            labels={
                "evm_percentage": "EVM %",
                "callSign": "Fahrzeug",
                "vehicleType": "Fahrzeugtyp",
            },
            text="evm_percentage",
        )
        fig_vehicle_comparison.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside"
        )
        st.plotly_chart(fig_vehicle_comparison)

        # Comparison by Mission Type
        if "missionType" in comparison_df.columns:
            st.write("### EVM % nach Mission Type")

            # Total missions by mission type
            total_by_type = (
                comparison_df.groupby("missionType")
                .size()
                .reset_index(name="total_missions")
            )

            # Missions with EVM by mission type
            evm_by_type = (
                comparison_df[comparison_df["protocolId"].isin(evm_protocols)]
                .groupby("missionType")
                .size()
                .reset_index(name="missions_with_evm")
            )

            # Merge and calculate percentage
            mission_comparison = total_by_type.merge(
                evm_by_type, on="missionType", how="left"
            ).fillna(0)

            mission_comparison["evm_percentage"] = (
                mission_comparison["missions_with_evm"]
                / mission_comparison["total_missions"]
                * 100
            ).round(2)

            # Sort by EVM percentage descending
            mission_comparison = mission_comparison.sort_values(
                "evm_percentage", ascending=False
            )

            st.dataframe(mission_comparison)

            # Bar chart for EVM % by mission type
            fig_mission_comparison = px.bar(
                mission_comparison,
                x="missionType",
                y="evm_percentage",
                title="EVM % nach Mission Type",
                labels={"evm_percentage": "EVM %", "missionType": "Mission Type"},
                color="evm_percentage",
                color_continuous_scale="Reds",
            )
            fig_mission_comparison.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_mission_comparison)

        # Summary statistics
        st.write("### Zusammenfassung")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Durchschnittliche EVM %",
                f"{comparison_stats['evm_percentage'].mean():.1f}%",
            )

        with col2:
            st.metric(
                "Höchste EVM %", f"{comparison_stats['evm_percentage'].max():.1f}%"
            )

        with col3:
            st.metric("Gesamtmissionen", f"{comparison_stats['total_missions'].sum()}")

    else:
        st.info(
            "Keine Daten im ausgewählten Zeitraum und für die ausgewählten "
            "Fahrzeuge gefunden."
        )
else:
    st.warning("Erforderliche Daten für den Vergleich nicht verfügbar.")


# st.subheader("interrupted time series analysis")
# st.write("https://en.wikipedia.org/wiki/Interrupted_time_series")
# st.write("vergleich mit anderer stichprobe möglich? ggf. vergleich der s-ktw 'Einsatzballungsgebiete' mit den weiterhin normalen?")

# st.dataframe(monthly_evm)

# intervention_date = st.date_input(
#     "Select Intervention Date",
#     value=pd.to_Datetime("2025-01"),
#     key="intervention_date"
# )

# import arviz as az
# import matplotlib.dates as mdates
# import matplotlib.pyplot as plt
# import numpy as np
# import pandas as pd
# import pymc as pm
# import xarray as xr

# from scipy.stats import norm

# pre = monthly_evm["year_month"] < intervention_date
# post = monthly_evm["year_month"] > intervention_date

# fig, ax = plt.subplots()
# ax = pre["evm_count"].plot(lable="pre")
# post["evm_count"].plot(ac=ax, label="post")
# ax-axvline(intervention_date,c="k",ls=":")
# plt.legend();


# st.markdown("""
#             S-KTW entlastet RTW ohne relevante Qualitätsnachteile
#             Metriken: Notarzt-Nachforderungen, Sonderrechtsfahrt zum Transportziel, 2.0 bis 3.3 der AG Indikatoren für S-RTW vs RTW"""
#             )

# sonderrechtsfahrten in details_df[content.flashingLights] "ja" or "nein" and details_df[content.transportFlashingLights
# # results_df = data_loading("NA-Nachforderung") where protocols_results[content..value_1 == "Nachforderung NA" "ja"/"nein"] # must be implemented in results_loaders


# S-KTW übernimmt niedrigere Dringlichkeitslagen effizienter als RTW (geringere Kosten)
# Metriken: Einsatz- bzw. Zykluszeit, Auslastung; Qualifikation/Mix des Personals auf S-KTW

# # qualifikationen in details_df[content.driverQualification] and details_df[content.codriverQualification]


# Sonderrechtsfahrten sind bei S-KTW seltener und zielgerichtet – ohne negative Wirkung auf das Transportintervall
# Metriken: Sonderrechts‑Indikationsprüfung
