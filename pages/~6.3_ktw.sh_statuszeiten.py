import streamlit as st
import pandas as pd
import plotly.express as px
from auth import check_authentication, logout

# Authentication check
if not check_authentication():
    st.warning("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.")
    st.stop()

st.title("6.3 Transport Status Zeiten Analyse")

# Logout-Button in der Sidebar anzeigen
logout()

# Begrüßung anzeigen
st.sidebar.write(f'Willkommen *{st.session_state["name"]}*')


# Load the data
@st.cache_data(ttl=3600)
def load_transport_status_data():
    """Load transport status history from pipe-delimited text file"""
    # Read the text file
    with open("data/ktw_sh_transport_status_history.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse the data
    data = []
    for line in lines:
        # Skip header and separator lines
        if not line.strip() or "|" not in line or "---" in line:
            continue

        # Split by pipe and clean up whitespace
        parts = [part.strip() for part in line.split("|")]

        # Skip if not enough columns
        if len(parts) < 6:
            continue

        # Extract values
        try:
            record = {
                "id": int(parts[0]),
                "old_status": parts[1] if parts[1] else None,
                "new_status": parts[2],
                "changed_at": parts[3],
                "changed_by_id": int(parts[4]),
                "transport_id": int(parts[5]),
            }
            data.append(record)
        except (ValueError, IndexError):
            continue

    # Create DataFrame
    loaded_df = pd.DataFrame(data)
    if not loaded_df.empty:
        loaded_df["changed_at"] = pd.to_datetime(loaded_df["changed_at"])

    return loaded_df


df = pd.read_csv("data/ktw_sh_transport_status_history.csv")

if df.empty:
    st.error(
        "Keine Transportstatus-Daten verfügbar. "
        "Bitte überprüfen Sie die Datenbankverbindung."
    )
    st.stop()

st.write(f"**Gesamtzahl der Statusänderungen:** {len(df)}")
st.write(f"**Zeitbereich:** {df['changed_at'].min()} bis {df['changed_at'].max()}")

# Data preview
st.subheader("Datentabelle - Rohdata")
st.dataframe(df, use_container_width=True)

# Analysis section
st.subheader("Statusübergänge Analyse")

# Create a summary of status transitions
if "old_status" in df.columns and "new_status" in df.columns:
    # Count transitions
    df["transition"] = df["old_status"].fillna("START") + " → " + df["new_status"]
    transition_counts = df["transition"].value_counts().reset_index()
    transition_counts.columns = ["Übergang", "Häufigkeit"]

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Top Statusübergänge:**")
        st.dataframe(transition_counts, use_container_width=True)

    with col2:
        fig_transitions = px.bar(
            transition_counts.head(10),
            x="Häufigkeit",
            y="Übergang",
            orientation="h",
            title="Top 10 Statusübergänge",
            labels={"Häufigkeit": "Anzahl", "Übergang": "Statusübergang"},
        )
        st.plotly_chart(fig_transitions, use_container_width=True)

# Status distribution
st.subheader("Statusverteilung")

col1, col2 = st.columns(2)

with col1:
    if "old_status" in df.columns:
        old_status_counts = df["old_status"].value_counts().reset_index()
        old_status_counts.columns = ["Status", "Häufigkeit"]
        old_status_counts = old_status_counts[
            old_status_counts["Status"].notna()
        ]  # Filter out NaN

        fig_old_status = px.pie(
            old_status_counts,
            values="Häufigkeit",
            names="Status",
            title="Verteilung - Alter Status",
        )
        st.plotly_chart(fig_old_status, use_container_width=True)

with col2:
    if "new_status" in df.columns:
        new_status_counts = df["new_status"].value_counts().reset_index()
        new_status_counts.columns = ["Status", "Häufigkeit"]

        fig_new_status = px.pie(
            new_status_counts,
            values="Häufigkeit",
            names="Status",
            title="Verteilung - Neuer Status",
        )
        st.plotly_chart(fig_new_status, use_container_width=True)

# Time-based analysis
st.subheader("Zeitliche Analyse")

if "changed_at" in df.columns:
    # Convert to datetime if not already
    df["changed_at"] = pd.to_datetime(df["changed_at"])

    # Extract date information
    df["date"] = df["changed_at"].dt.date
    df["hour"] = df["changed_at"].dt.hour
    df["day_of_week"] = df["changed_at"].dt.day_name()

    col1, col2 = st.columns(2)

    with col1:
        # Timeline chart - changes per day
        changes_per_day = df.groupby("date").size().reset_index(name="Anzahl")
        fig_timeline = px.line(
            changes_per_day,
            x="date",
            y="Anzahl",
            title="Statusänderungen pro Tag",
            labels={"date": "Datum", "Anzahl": "Anzahl Statusänderungen"},
            markers=True,
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

    with col2:
        # Changes per hour
        changes_per_hour = df.groupby("hour").size().reset_index(name="Anzahl")
        fig_hourly = px.bar(
            changes_per_hour,
            x="hour",
            y="Anzahl",
            title="Statusänderungen pro Stunde",
            labels={"hour": "Stunde", "Anzahl": "Anzahl Statusänderungen"},
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

    # Day of week analysis
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    changes_per_dow = df.groupby("day_of_week").size().reset_index(name="Anzahl")
    changes_per_dow["day_of_week"] = pd.Categorical(
        changes_per_dow["day_of_week"], categories=day_order, ordered=True
    )
    changes_per_dow = changes_per_dow.sort_values("day_of_week")

    fig_dow = px.bar(
        changes_per_dow,
        x="day_of_week",
        y="Anzahl",
        title="Statusänderungen pro Wochentag",
        labels={"day_of_week": "Wochentag", "Anzahl": "Anzahl Statusänderungen"},
    )
    st.plotly_chart(fig_dow, use_container_width=True)

# Transport-specific analysis
st.subheader("Transport-spezifische Analyse")

if "transport_id" in df.columns:
    # Transports per status change
    transports_per_status = df["transport_id"].nunique()
    st.metric("Anzahl einzigartiger Transporte", transports_per_status)

    # Average status changes per transport
    avg_changes_per_transport = len(df) / transports_per_status
    st.metric(
        "Durchschnittliche Statusänderungen pro Transport",
        f"{avg_changes_per_transport:.1f}",
    )

    # Transport journey visualization
    st.write("**Transport Journey - Status Timeline pro Transport:**")
    
    selected_transport = st.selectbox(
        "Wählen Sie einen Transport:",
        sorted(df["transport_id"].unique()),
        key="transport_select",
    )

    if selected_transport:
        transport_data = df[df["transport_id"] == selected_transport].sort_values(
            "changed_at"
        )
        
        # Create a Gantt-like visualization
        transport_data_display = transport_data[
            ["changed_at", "old_status", "new_status", "changed_by_id"]
        ].copy()
        transport_data_display.columns = [
            "Zeitpunkt",
            "Alter Status",
            "Neuer Status",
            "Geändert von",
        ]
        
        st.dataframe(transport_data_display, use_container_width=True)

        # Timeline visualization
        if len(transport_data) > 0:
            fig_transport_timeline = px.timeline(
                transport_data.reset_index(),
                x_start="changed_at",
                x_end="changed_at",
                y="new_status",
                title=f"Status Timeline für Transport {selected_transport}",
                labels={"new_status": "Status", "changed_at": "Zeit"},
            )
            st.plotly_chart(fig_transport_timeline, use_container_width=True)

# Users analysis
st.subheader("Benutzer-Aktivitäts Analyse")

if "changed_by_id" in df.columns:
    user_activity = (
        df.groupby("changed_by_id")
        .size()
        .reset_index(name="Statusänderungen")
    )
    user_activity = user_activity.sort_values(
        "Statusänderungen", ascending=False
    )

    st.write("**Statusänderungen pro Benutzer:**")
    st.dataframe(user_activity, use_container_width=True)

    fig_users = px.bar(
        user_activity.head(10),
        x="Statusänderungen",
        y="changed_by_id",
        orientation="h",
        title="Top 10 Benutzer nach Statusänderungen",
        labels={"changed_by_id": "Benutzer ID", "Statusänderungen": "Anzahl"},
    )
    st.plotly_chart(fig_users, use_container_width=True)


# Transport flow analysis
st.subheader("Transport-Fluss Analyse")

st.write(
    "**Analyse des Transports von 'offen' Status zu den verschiedenen "
    "Zielstatussen**"
)

# Analyze all transports and their status flows
transport_flows = []

for transport_id in df["transport_id"].unique():
    transport_df = df[df["transport_id"] == transport_id].sort_values("changed_at")

    if len(transport_df) > 0:
        # Get initial status (first entry)
        first_status = transport_df.iloc[0]["new_status"]
        # Get final status (last entry)
        final_status = transport_df.iloc[-1]["new_status"]
        # Get all statuses in order
        all_statuses = " → ".join(transport_df["new_status"].tolist())
        # Count status occurrences
        status_counts = transport_df["new_status"].value_counts().to_dict()

        transport_flows.append(
            {
                "transport_id": transport_id,
                "first_status": first_status,
                "final_status": final_status,
                "status_path": all_statuses,
                "num_changes": len(transport_df),
                "has_storno": "storniert" in transport_df["new_status"].values,
                "storno_count": status_counts.get("storniert", 0),
            }
        )

flows_df = pd.DataFrame(transport_flows)

# Overall statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Gesamtzahl Transporte", len(flows_df))

with col2:
    storno_count = flows_df["has_storno"].sum()
    st.metric("Transporte mit Storno", storno_count)

with col3:
    st.metric(
        "Storno Prozentanteil",
        f"{(storno_count / len(flows_df) * 100):.1f}%"
    )

with col4:
    abgeschlossen_count = (flows_df["final_status"] == "abgeschlossen").sum()
    st.metric(
        "Abgeschlossene Transporte",
        f"{abgeschlossen_count} ({abgeschlossen_count/len(flows_df)*100:.1f}%)"
    )

# Analyze final status distribution
st.write("**Verteilung der Endzustände:**")

final_status_counts = flows_df["final_status"].value_counts().reset_index()
final_status_counts.columns = ["Status", "Anzahl"]
final_status_counts["Prozent"] = (
    final_status_counts["Anzahl"] / len(flows_df) * 100
).round(1)

col1, col2 = st.columns(2)

with col1:
    st.dataframe(final_status_counts, use_container_width=True)

with col2:
    fig_final_status = px.pie(
        final_status_counts,
        values="Anzahl",
        names="Status",
        title="Verteilung Endzustände",
    )
    st.plotly_chart(fig_final_status, use_container_width=True)

# Storno analysis
st.write("**Detaillierte Storno-Analyse:**")

storno_transports = flows_df[flows_df["has_storno"]]

if len(storno_transports) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Transporte mit Storno: {len(storno_transports)}**")

        storno_display = storno_transports[
            ["transport_id", "status_path", "final_status"]
        ].copy()
        storno_display.columns = ["Transport ID", "Status Pfad", "Endzustand"]

        st.dataframe(storno_display, use_container_width=True)

    with col2:
        # Storno outcomes
        storno_outcomes = (
            storno_transports["final_status"].value_counts().reset_index()
        )
        storno_outcomes.columns = ["Endzustand nach Storno", "Anzahl"]

        fig_storno_outcomes = px.bar(
            storno_outcomes,
            x="Anzahl",
            y="Endzustand nach Storno",
            orientation="h",
            title="Endzustände nach Storno",
            text="Anzahl",
        )
        st.plotly_chart(fig_storno_outcomes, use_container_width=True)

else:
    st.info("Keine Transporte mit Storno gefunden.")

# Analyze non-standard flows
st.write("**Nicht-standardisierte Transportflüsse:**")

# Define standard flow: offen → disponiert → abgeschlossen
standard_paths = [
    "offen → disponiert → abgeschlossen",
    "offen → disponiert",
    "offen → abgeschlossen",
]

non_standard = flows_df[~flows_df["status_path"].isin(standard_paths)]

if len(non_standard) > 0:
    st.write(
        f"**{len(non_standard)} Transporte folgen nicht dem "
        f"Standard-Fluss (offen → disponiert → abgeschlossen):**"
    )

    # Group by status path
    path_counts = non_standard["status_path"].value_counts().reset_index()
    path_counts.columns = ["Status Pfad", "Anzahl"]

    col1, col2 = st.columns(2)

    with col1:
        st.dataframe(path_counts, use_container_width=True)

    with col2:
        fig_non_standard = px.bar(
            path_counts.head(10),
            x="Anzahl",
            y="Status Pfad",
            orientation="h",
            title="Top 10 Nicht-Standard Flüsse",
        )
        st.plotly_chart(fig_non_standard, use_container_width=True)

    # Detail view of non-standard flows
    st.write("**Detaillierte Liste nicht-standardisierter Flüsse:**")

    non_standard_display = non_standard[
        ["transport_id", "status_path", "final_status", "num_changes"]
    ].copy()
    non_standard_display.columns = [
        "Transport ID",
        "Status Pfad",
        "Endzustand",
        "Anzahl Änderungen",
    ]
    non_standard_display = non_standard_display.sort_values("Transport ID")

    st.dataframe(non_standard_display, use_container_width=True)

else:
    st.success("✓ Alle Transporte folgen dem Standard-Fluss!")

# Summary comparison
st.write("**Vergleich: Standard vs. Non-Standard Flüsse**")

standard_count = len(flows_df[flows_df["status_path"].isin(standard_paths)])
non_standard_count = len(non_standard)

comparison_data = pd.DataFrame(
    {
        "Flusstyp": ["Standard-Fluss", "Nicht-Standard"],
        "Anzahl Transporte": [standard_count, non_standard_count],
        "Prozentanteil": [
            f"{standard_count / len(flows_df) * 100:.1f}%",
            f"{non_standard_count / len(flows_df) * 100:.1f}%",
        ],
    }
)

col1, col2 = st.columns(2)

with col1:
    st.dataframe(comparison_data, use_container_width=True)

with col2:
    fig_comparison = px.bar(
        comparison_data,
        x="Flusstyp",
        y="Anzahl Transporte",
        title="Standard vs. Nicht-Standard Flüsse",
        text="Anzahl Transporte",
    )
    st.plotly_chart(fig_comparison, use_container_width=True)


# Status transition time analysis - Focus on acceptance time
st.subheader("Annahme-Zeit Analyse (offen → angenommen)")

st.write(
    "**Analyse der Zeit, die das Personal benötigte, "
    "um einen Transport anzunehmen (offen → angenommen)**"
)

# Collect acceptance times (offen to angenommen)
acceptance_times = []

for transport_id in df["transport_id"].unique():
    transport_df = df[df["transport_id"] == transport_id].sort_values("changed_at")
    statuses = transport_df["new_status"].tolist()

    # Check if transport has offen and angenommen status
    if "offen" in statuses and "angenommen" in statuses:
        offen_time = transport_df[
            transport_df["new_status"] == "offen"
        ]["changed_at"].iloc[0]
        angenommen_time = transport_df[
            transport_df["new_status"] == "angenommen"
        ]["changed_at"].iloc[0]

        # Only consider if angenommen comes after offen
        if angenommen_time > offen_time:
            duration = angenommen_time - offen_time
            duration_minutes = duration.total_seconds() / 60
            duration_hours = duration_minutes / 60

            acceptance_times.append(
                {
                    "transport_id": transport_id,
                    "offen_time": offen_time,
                    "angenommen_time": angenommen_time,
                    "acceptance_duration_min": duration_minutes,
                    "acceptance_duration_hours": duration_hours,
                }
            )

# Also collect direct transitions (without angenommen step)
direct_transitions = []

for transport_id in df["transport_id"].unique():
    transport_df = df[df["transport_id"] == transport_id].sort_values("changed_at")
    statuses = transport_df["new_status"].tolist()

    # Check transports without angenommen
    if "offen" in statuses and "angenommen" not in statuses:
        if "disponiert" in statuses or "abgeschlossen" in statuses:
            offen_time = transport_df[
                transport_df["new_status"] == "offen"
            ]["changed_at"].iloc[0]

            # Find next status after offen
            remaining = transport_df[transport_df["changed_at"] > offen_time]
            if not remaining.empty:
                next_status = remaining.iloc[0]["new_status"]
                next_time = remaining.iloc[0]["changed_at"]

                duration = next_time - offen_time
                duration_minutes = duration.total_seconds() / 60
                duration_hours = duration_minutes / 60

                direct_transitions.append(
                    {
                        "transport_id": transport_id,
                        "offen_time": offen_time,
                        "next_status": next_status,
                        "next_time": next_time,
                        "response_time_min": duration_minutes,
                        "response_time_hours": duration_hours,
                        "type": "direct (no acceptance)",
                    }
                )

# Display acceptance times
if acceptance_times:
    acceptance_df = pd.DataFrame(acceptance_times)

    st.write(
        f"**Transporte mit Annahme-Phase "
        f"(offen → angenommen): {len(acceptance_df)}**"
    )

    # Summary statistics for acceptance
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Ø Annahmezeit (Min)",
            f"{acceptance_df['acceptance_duration_min'].mean():.1f}",
        )

    with col2:
        st.metric(
            "Median Annahmezeit (Min)",
            f"{acceptance_df['acceptance_duration_min'].median():.1f}",
        )

    with col3:
        st.metric(
            "Min Annahmezeit (Min)",
            f"{acceptance_df['acceptance_duration_min'].min():.1f}",
        )

    with col4:
        st.metric(
            "Max Annahmezeit (Min)",
            f"{acceptance_df['acceptance_duration_min'].max():.1f}",
        )

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Histogram of acceptance times
        fig_acceptance_hist = px.histogram(
            acceptance_df,
            x="acceptance_duration_min",
            nbins=15,
            title="Verteilung der Annahmezeiten",
            labels={"acceptance_duration_min": "Annahmezeit (Minuten)"},
            color_discrete_sequence=["#2ca02c"],
        )
        fig_acceptance_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_acceptance_hist, use_container_width=True)

    with col2:
        # Box plot of acceptance times
        fig_acceptance_box = px.box(
            acceptance_df,
            y="acceptance_duration_min",
            title="Annahmezeit-Verteilung",
            labels={"acceptance_duration_min": "Annahmezeit (Minuten)"},
            color_discrete_sequence=["#2ca02c"],
        )
        st.plotly_chart(fig_acceptance_box, use_container_width=True)

    # Detailed table
    st.write("**Detaillierte Annahmezeiten pro Transport:**")

    acceptance_display = acceptance_df[
        ["transport_id", "offen_time", "angenommen_time", "acceptance_duration_min"]
    ].copy()

    acceptance_display.columns = [
        "Transport ID",
        "Offen Zeit",
        "Angenommen Zeit",
        "Annahmezeit (Min)",
    ]

    acceptance_display["Annahmezeit (Min)"] = acceptance_display[
        "Annahmezeit (Min)"
    ].apply(lambda x: f"{x:.1f}")

    st.dataframe(acceptance_display, use_container_width=True)

else:
    st.info(
        "Keine Transporte mit Annahme-Phase (offen → angenommen) gefunden."
    )

# Display direct transitions (no acceptance)
if direct_transitions:
    st.write(
        f"**Transporte ohne Annahme-Phase "
        f"(Direkte Übergänge): {len(direct_transitions)}**"
    )

    direct_df = pd.DataFrame(direct_transitions)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Ø Reaktionszeit (Min)",
            f"{direct_df['response_time_min'].mean():.1f}",
        )

    with col2:
        st.metric(
            "Median Reaktionszeit (Min)",
            f"{direct_df['response_time_min'].median():.1f}",
        )

    with col3:
        st.metric(
            "Min Reaktionszeit (Min)",
            f"{direct_df['response_time_min'].min():.1f}",
        )

    with col4:
        st.metric(
            "Max Reaktionszeit (Min)",
            f"{direct_df['response_time_min'].max():.1f}",
        )

    direct_display = direct_df[
        ["transport_id", "offen_time", "next_status", "next_time", "response_time_min"]
    ].copy()

    direct_display.columns = [
        "Transport ID",
        "Offen Zeit",
        "Nächster Status",
        "Status Zeit",
        "Reaktionszeit (Min)",
    ]

    direct_display["Reaktionszeit (Min)"] = direct_display[
        "Reaktionszeit (Min)"
    ].apply(lambda x: f"{x:.1f}")

    st.dataframe(direct_display, use_container_width=True)

else:
    st.info("Keine Transporte ohne Annahme-Phase gefunden.")

# Comparison
st.subheader("Vergleich: Annahmezeit vs. Direkte Übergänge")

if acceptance_times and direct_transitions:
    comparison_data = pd.DataFrame(
        {
            "Kategorie": [
                "Mit Annahme-Phase",
                "Direkte Übergänge",
            ],
            "Anzahl": [len(acceptance_df), len(direct_df)],
            "Ø Zeit (Min)": [
                f"{acceptance_df['acceptance_duration_min'].mean():.1f}",
                f"{direct_df['response_time_min'].mean():.1f}",
            ],
            "Median (Min)": [
                f"{acceptance_df['acceptance_duration_min'].median():.1f}",
                f"{direct_df['response_time_min'].median():.1f}",
            ],
        }
    )

    st.dataframe(comparison_data, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Combined histogram
        combined_data = pd.concat(
            [
                acceptance_df.assign(type="Mit Annahme").rename(
                    columns={"acceptance_duration_min": "duration_min"}
                )[["transport_id", "duration_min", "type"]],
                direct_df.assign(type="Direkt").rename(
                    columns={"response_time_min": "duration_min"}
                )[["transport_id", "duration_min", "type"]],
            ]
        )

        fig_combined = px.histogram(
            combined_data,
            x="duration_min",
            color="type",
            nbins=15,
            title="Vergleich: Annahmezeit vs. Reaktionszeit",
            labels={"duration_min": "Zeit (Minuten)"},
            barmode="overlay",
        )
        st.plotly_chart(fig_combined, use_container_width=True)

    with col2:
        # Box plot comparison
        fig_comparison_box = px.box(
            combined_data,
            x="type",
            y="duration_min",
            title="Zeitverteilung Vergleich",
            labels={"duration_min": "Zeit (Minuten)", "type": "Kategorie"},
            color="type",
        )
        st.plotly_chart(fig_comparison_box, use_container_width=True)


# Extended flow analysis: offen → angenommen → disponiert → abgeschlossen
st.subheader(
    "Erweiterte Fluss-Analyse: "
    "offen → angenommen → disponiert → abgeschlossen"
)

# Analyze complete flow paths
complete_flows = []

for transport_id in df["transport_id"].unique():
    transport_df = df[df["transport_id"] == transport_id].sort_values("changed_at")

    # Look for transports that go through all these statuses
    statuses = transport_df["new_status"].tolist()

    # Check if this transport follows or contains the sequence
    if "offen" in statuses:
        offen_idx = statuses.index("offen")
        remaining_statuses = statuses[offen_idx:]

        # Check for various sequences
        has_angenommen = "angenommen" in remaining_statuses
        has_disponiert = "disponiert" in remaining_statuses
        has_abgeschlossen = "abgeschlossen" in remaining_statuses

        if (
            has_angenommen and has_disponiert and has_abgeschlossen
        ):  # Full flow
            offen_time = transport_df[
                transport_df["new_status"] == "offen"
            ]["changed_at"].iloc[0]
            angenommen_time = transport_df[
                transport_df["new_status"] == "angenommen"
            ]["changed_at"].iloc[0]
            disponiert_time = transport_df[
                transport_df["new_status"] == "disponiert"
            ]["changed_at"].iloc[0]
            abgeschlossen_time = transport_df[
                transport_df["new_status"] == "abgeschlossen"
            ]["changed_at"].iloc[-1]

            # Calculate durations for each step
            offen_to_angenommen = (
                angenommen_time - offen_time
            ).total_seconds() / 60
            angenommen_to_disponiert = (
                disponiert_time - angenommen_time
            ).total_seconds() / 60
            disponiert_to_abgeschlossen = (
                abgeschlossen_time - disponiert_time
            ).total_seconds() / 60
            total_duration = (
                abgeschlossen_time - offen_time
            ).total_seconds() / 60

            complete_flows.append(
                {
                    "transport_id": transport_id,
                    "offen_start": offen_time,
                    "angenommen_time": angenommen_time,
                    "disponiert_time": disponiert_time,
                    "abgeschlossen_time": abgeschlossen_time,
                    "offen_to_angenommen_min": offen_to_angenommen,
                    "angenommen_to_disponiert_min": angenommen_to_disponiert,
                    "disponiert_to_abgeschlossen_min": disponiert_to_abgeschlossen,
                    "total_duration_min": total_duration,
                }
            )

if complete_flows:
    complete_flows_df = pd.DataFrame(complete_flows)

    st.write(
        f"**Transporte mit vollständiger Flussfolge "
        f"(offen → angenommen → disponiert → abgeschlossen): "
        f"{len(complete_flows_df)}**"
    )

    # Summary statistics for each step
    st.write("**Durchschnittliche Dauer pro Schritt:**")

    step_stats = pd.DataFrame(
        {
            "Schritt": [
                "offen → angenommen",
                "angenommen → disponiert",
                "disponiert → abgeschlossen",
                "Gesamtdauer",
            ],
            "Durchschnitt (Min)": [
                f"{complete_flows_df['offen_to_angenommen_min'].mean():.1f}",
                f"{complete_flows_df['angenommen_to_disponiert_min'].mean():.1f}",
                f"{complete_flows_df['disponiert_to_abgeschlossen_min'].mean():.1f}",
                f"{complete_flows_df['total_duration_min'].mean():.1f}",
            ],
            "Median (Min)": [
                f"{complete_flows_df['offen_to_angenommen_min'].median():.1f}",
                f"{complete_flows_df['angenommen_to_disponiert_min'].median():.1f}",
                f"{complete_flows_df['disponiert_to_abgeschlossen_min'].median():.1f}",
                f"{complete_flows_df['total_duration_min'].median():.1f}",
            ],
            "Min (Min)": [
                f"{complete_flows_df['offen_to_angenommen_min'].min():.1f}",
                f"{complete_flows_df['angenommen_to_disponiert_min'].min():.1f}",
                f"{complete_flows_df['disponiert_to_abgeschlossen_min'].min():.1f}",
                f"{complete_flows_df['total_duration_min'].min():.1f}",
            ],
            "Max (Min)": [
                f"{complete_flows_df['offen_to_angenommen_min'].max():.1f}",
                f"{complete_flows_df['angenommen_to_disponiert_min'].max():.1f}",
                f"{complete_flows_df['disponiert_to_abgeschlossen_min'].max():.1f}",
                f"{complete_flows_df['total_duration_min'].max():.1f}",
            ],
        }
    )

    st.dataframe(step_stats, use_container_width=True)

    # Visualization of step durations
    col1, col2 = st.columns(2)

    with col1:
        # Create data for visualization
        viz_data = pd.DataFrame(
            {
                "Schritt": [
                    "offen →\nangenommen",
                    "angenommen →\nverfügbar",
                    "verfügbar →\nabgeschlossen",
                ]
                * len(complete_flows_df),
                "Dauer (Min)": list(
                    complete_flows_df["offen_to_angenommen_min"]
                )
                + list(complete_flows_df["angenommen_to_disponiert_min"])
                + list(complete_flows_df["disponiert_to_abgeschlossen_min"]),
            }
        )

        fig_steps = px.box(
            viz_data,
            x="Schritt",
            y="Dauer (Min)",
            title="Verteilung der Schrittdauern",
            color="Schritt",
        )
        st.plotly_chart(fig_steps, use_container_width=True)

    with col2:
        # Stacked bar chart showing relative durations
        avg_data = pd.DataFrame(
            {
                "Durchschnittliche Dauer (Min)": [
                    complete_flows_df["offen_to_angenommen_min"].mean(),
                    complete_flows_df["angenommen_to_disponiert_min"].mean(),
                    complete_flows_df["disponiert_to_abgeschlossen_min"].mean(),
                ],
                "Schritt": [
                    "offen → angenommen",
                    "angenommen → disponiert",
                    "disponiert → abgeschlossen",
                ],
            }
        )

        fig_avg_steps = px.bar(
            avg_data,
            x="Schritt",
            y="Durchschnittliche Dauer (Min)",
            title="Durchschnittliche Dauer pro Schritt",
            text="Durchschnittliche Dauer (Min)",
        )
        fig_avg_steps.update_traces(
            texttemplate="%{text:.1f}", textposition="outside"
        )
        st.plotly_chart(fig_avg_steps, use_container_width=True)

    # Timeline scatter showing all transports
    st.write("**Individuelle Transportflüsse:**")

    timeline_data = pd.DataFrame(
        {
            "Transport ID": complete_flows_df["transport_id"],
            "Schritt 1: offen → angenommen": complete_flows_df[
                "offen_to_angenommen_min"
            ],
            "Schritt 2: angenommen → disponiert": complete_flows_df[
                "angenommen_to_disponiert_min"
            ],
            "Schritt 3: disponiert → abgeschlossen": complete_flows_df[
                "disponiert_to_abgeschlossen_min"
            ],
            "Gesamt": complete_flows_df["total_duration_min"],
        }
    )

    st.dataframe(timeline_data, use_container_width=True)

    # Scatter plot showing relationship between steps
    fig_scatter = px.scatter(
        complete_flows_df,
        x="offen_to_angenommen_min",
        y="angenommen_to_disponiert_min",
        size="total_duration_min",
        color="disponiert_to_abgeschlossen_min",
        hover_data={
            "transport_id": True,
            "total_duration_min": ":.1f",
        },
        title="Beziehung zwischen Schrittdauern",
        labels={
            "offen_to_angenommen_min": "offen → angenommen (Min)",
            "angenommen_to_disponiert_min": "angenommen → disponiert (Min)",
            "disponiert_to_abgeschlossen_min": "disponiert → abgeschlossen (Min)",
        },
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Detailed statistics
    st.write("**Detaillierte Statistiken:**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Ø Schritt 1 (Min)",
            f"{complete_flows_df['offen_to_angenommen_min'].mean():.1f}",
            delta=f"σ={complete_flows_df['offen_to_angenommen_min'].std():.1f}",
        )

    with col2:
        st.metric(
            "Ø Schritt 2 (Min)",
            f"{complete_flows_df['angenommen_to_disponiert_min'].mean():.1f}",
            delta=f"σ={complete_flows_df['angenommen_to_disponiert_min'].std():.1f}",
        )

    with col3:
        st.metric(
            "Ø Schritt 3 (Min)",
            f"{complete_flows_df['disponiert_to_abgeschlossen_min'].mean():.1f}",
            delta=f"σ={complete_flows_df['disponiert_to_abgeschlossen_min'].std():.1f}",
        )

    with col4:
        st.metric(
            "Ø Gesamtdauer (Min)",
            f"{complete_flows_df['total_duration_min'].mean():.1f}",
            delta=f"σ={complete_flows_df['total_duration_min'].std():.1f}",
        )

else:
    st.info(
        "Keine Transporte gefunden, die die vollständige Flussfolge "
        "(offen → angenommen → disponiert → abgeschlossen) durchlaufen."
    )

