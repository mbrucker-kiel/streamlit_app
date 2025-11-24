import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loading import data_loading
import datetime
import ast

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

st.title("6.4 ZSR")
st.subheader("Diagnose-Vergleichsanalyse: Juli - Dezember 2024")


@st.cache_data(ttl=3600)
def load_and_prepare_data_v3():
    """Lade und bereite die Daten für alle Diagnosen vor (inkl. GCS und Krankenhaus)"""
    # Lade Daten
    df_index = data_loading(metric="Index")
    df_details = data_loading(metric="Details")
    df_rea = data_loading(metric="Reanimation")
    df_gcs = data_loading(metric="GCS")

    # Load hospital data with proper encoding handling
    df_krankenhaus = None
    for encoding in ["latin1", "iso-8859-1", "cp1252", "utf-8"]:
        try:
            df_krankenhaus = pd.read_csv(
                "data/krankenhausDigagnosen.csv", sep=";", encoding=encoding
            )
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    if df_krankenhaus is None:
        df_krankenhaus = pd.DataFrame()

    # Merge df_index and df_details
    if not df_details.empty:
        if "_id" in df_index.columns and "_id" in df_details.columns:
            merged_df = pd.merge(
                df_index.drop(columns=["_id"]),
                df_details.drop(columns=["_id"]),
                on="protocolId",
                how="outer",
                suffixes=("", "_y"),
            )
        else:
            merged_df = pd.merge(
                df_index,
                df_details,
                on="protocolId",
                how="outer",
                suffixes=("", "_y"),
            )
    else:
        merged_df = df_index

    return merged_df, df_rea, df_gcs, df_krankenhaus


# Load BKN data with proper encoding handling
df_bkn = None
for encoding in ["utf-8", "latin1", "iso-8859-1", "cp1252"]:
    try:
        df_bkn = pd.read_csv(
            "data/Schleswig-Flensburg_herausgefilterte_Einzeldatensätze(1).csv",
            encoding=encoding,
        )
        break
    except (UnicodeDecodeError, FileNotFoundError):
        continue

if df_bkn is None:
    df_bkn = pd.DataFrame()


def calculate_time_diff_minutes(row, start_col, end_col):
    """Berechne Zeitdifferenz in Minuten"""
    try:
        if pd.notnull(row[start_col]) and pd.notnull(row[end_col]):
            delta = row[end_col] - row[start_col]
            if isinstance(delta, datetime.timedelta):
                return delta.total_seconds() / 60
            return None
        return None
    except:
        return None


def filter_by_diagnosis(df, diagnosis_type):
    """Filtere Daten nach Diagnose-Typ"""
    if "leadingDiagnosis" not in df.columns:
        return pd.DataFrame()

    diagnosis_patterns = {
        "Polytrauma": ["polytrauma"],
        "STEMI": ["stemi", "acs"],
        "Stroke": ["schlaganfall"],
        "Reanimation": ["reanimation", "wiederbelebung"],
        "SHT": ["schädel-hirn"],
        "Sepsis": ["sepsis"],
    }

    if diagnosis_type not in diagnosis_patterns:
        return pd.DataFrame()

    patterns = diagnosis_patterns[diagnosis_type]
    mask = pd.Series([False] * len(df))

    for pattern in patterns:
        mask |= df["leadingDiagnosis"].str.lower().str.contains(pattern, na=False)

    return df[mask]


def filter_reanimation_data(df, df_rea):
    """Spezielle Filterung für Reanimation basierend auf rea_status"""
    if df_rea.empty:
        return pd.DataFrame()

    # Filter reanimation data to include only True values
    df_rea_filtered = df_rea[df_rea["rea_status"] == True]

    # Merge with main data
    reanimation_protocols = df_rea_filtered["protocolId"].unique()
    return df[df["protocolId"].isin(reanimation_protocols)]


def check_hospital_eligibility(df_krankenhaus, df_index, diagnosis_type=None):
    """
    Check and display hospital eligibility for patient transports.
    If diagnosis_type is provided, only check for that specific diagnosis.
    """
    # Create a dictionary for faster lookups
    hospital_capabilities = {}

    # Process hospital data
    for _, row in df_krankenhaus.iterrows():
        hospital_names = ast.literal_eval(row["Name"])
        capabilities = {
            "TIA / Schlaganfall": row["TIA / Schlaganfall"],
            "ACS / STEMI /NSTEMI": row["ACS / STEMI /NSTEMI"],
            "Reanimation": row["Reanimation"],
            "Polytrauma": row["Polytrauma"],
        }

        # Add each name variant to the dictionary
        for name in hospital_names:
            hospital_capabilities[name.lower()] = capabilities

    # Diagnosis mapping - if diagnosis_type is provided, focus on that
    if diagnosis_type:
        # Map specific diagnosis type to hospital capability
        diagnosis_to_capability = {
            "Polytrauma": "Polytrauma",
            "SHT": "Polytrauma",
            "STEMI": "ACS / STEMI /NSTEMI",
            "Stroke": "TIA / Schlaganfall",
            "Reanimation": "Reanimation",
            "Sepsis": "Reanimation",
        }
        target_capability = diagnosis_to_capability.get(diagnosis_type, None)
    else:
        target_capability = None

    # Full diagnosis mapping for fallback
    diagnosis_map = {
        "schlaganfall": "TIA / Schlaganfall",
        "tia": "TIA / Schlaganfall",
        "stroke": "TIA / Schlaganfall",
        "apoplex": "TIA / Schlaganfall",
        "neurologisches defizit": "TIA / Schlaganfall",
        "halbseitenlähmung": "TIA / Schlaganfall",
        "hemiplegie": "TIA / Schlaganfall",
        "parese": "TIA / Schlaganfall",
        "sprachstörung": "TIA / Schlaganfall",
        "stemi": "ACS / STEMI /NSTEMI",
        "nstemi": "ACS / STEMI /NSTEMI",
        "acs": "ACS / STEMI /NSTEMI",
        "herzinfarkt": "ACS / STEMI /NSTEMI",
        "st-hebung": "ACS / STEMI /NSTEMI",
        "sthebung": "ACS / STEMI /NSTEMI",
        "akutes koronarsyndrom": "ACS / STEMI /NSTEMI",
        "reanimation": "Reanimation",
        "herz-kreislauf-stillstand": "Reanimation",
        "wiederbelebung": "Reanimation",
        "polytrauma": "Polytrauma",
        "schwerverletzt": "Polytrauma",
    }

    # Function to check individual transport
    def check_transport(target, diagnosis):
        if pd.isna(target) or pd.isna(diagnosis):
            return False

        target = target.strip().lower()
        diagnosis_lower = diagnosis.lower()

        # If diagnosis_type was provided, use that
        if target_capability:
            matched_category = target_capability
        else:
            # Otherwise, find matching diagnosis category from data
            matched_category = None
            for key, category in diagnosis_map.items():
                if key in diagnosis_lower:
                    matched_category = category
                    break

        if not matched_category:
            return False

        # Check if any hospital name matches
        for hospital_name, capabilities in hospital_capabilities.items():
            if hospital_name in target or target in hospital_name:
                return capabilities.get(matched_category, False)

        return False

    # Add eligibility column
    df_index["hospital_eligible"] = df_index.apply(
        lambda row: check_transport(
            row.get("targetDestination", ""), row.get("leadingDiagnosis", "")
        ),
        axis=1,
    )

    return df_index


def filter_severe_trauma_by_gcs(df, df_gcs, gcs_threshold=8):
    """Filtere SHT basierend auf GCS < 8"""
    if df_gcs.empty:
        return pd.DataFrame()

    # Fix duplicate column names in df_gcs if they exist
    if len(df_gcs.columns) != len(set(df_gcs.columns)):
        cols = pd.Series(df_gcs.columns)
        for dup in cols[cols.duplicated()].unique():
            cols[cols[cols == dup].index.values.tolist()] = [
                f"{dup}_{i}" if i != 0 else dup for i in range(sum(cols == dup))
            ]
        df_gcs.columns = cols

    # Ensure value_num is numeric
    df_gcs["value_num"] = pd.to_numeric(df_gcs["value_num"], errors="coerce")

    # Get protocolId column
    protocol_id_col = [col for col in df_gcs.columns if "protocolId" in col][0]

    # Filter for severe trauma: GCS < gcs_threshold, preferably eb_neuro (initial assessment)
    gcs_types = df_gcs["type"].unique()
    preferred_type = "eb_neuro" if "eb_neuro" in gcs_types else gcs_types[0]

    filtered_gcs = df_gcs[
        (df_gcs["type"] == preferred_type) & (df_gcs["value_num"] < gcs_threshold)
    ]

    if filtered_gcs.empty:
        return pd.DataFrame()

    # Get protocol IDs
    gcs_protocol_ids = filtered_gcs[protocol_id_col].unique()

    # Convert to same type for comparison
    df["protocolId"] = df["protocolId"].astype(str)
    gcs_protocol_ids = [str(pid) for pid in gcs_protocol_ids]

    return df[df["protocolId"].isin(gcs_protocol_ids)]


def prepare_diagnosis_data(df, df_rea, diagnosis_type, df_gcs=None):
    """Bereite Daten für eine spezifische Diagnose vor"""
    if diagnosis_type == "Reanimation":
        filtered_df = filter_reanimation_data(df, df_rea)
    elif diagnosis_type == "SHT (GCS<8)":
        # Combine SHT diagnosis with GCS < 8
        trauma_df = filter_by_diagnosis(df, "Polytrauma")
        if df_gcs is not None and not df_gcs.empty:
            filtered_df = filter_severe_trauma_by_gcs(
                trauma_df, df_gcs, gcs_threshold=8
            )
        else:
            filtered_df = trauma_df
    else:
        filtered_df = filter_by_diagnosis(df, diagnosis_type)

    if filtered_df.empty:
        return pd.DataFrame()

    # Berechne Zeitintervalle
    filtered_df = filtered_df.copy()

    # Konvertiere Datumsfelder
    if "missionDate" in filtered_df.columns:
        filtered_df["missionDate"] = pd.to_datetime(
            filtered_df["missionDate"], errors="coerce", utc=True
        )

    # Berechne Intervalle
    filtered_df["ReaktionsIntervall"] = filtered_df.apply(
        lambda row: calculate_time_diff_minutes(row, "StatusAlarm", "Status4"), axis=1
    )
    filtered_df["VersorgungsIntervall"] = filtered_df.apply(
        lambda row: calculate_time_diff_minutes(row, "Status4", "Status7"), axis=1
    )
    filtered_df["TransportIntervall"] = filtered_df.apply(
        lambda row: calculate_time_diff_minutes(row, "Status7", "Status8"), axis=1
    )
    filtered_df["PraehospitalIntervall"] = filtered_df.apply(
        lambda row: calculate_time_diff_minutes(row, "StatusAlarm", "Status8"), axis=1
    )

    # Entferne negative Werte
    for col in [
        "ReaktionsIntervall",
        "VersorgungsIntervall",
        "TransportIntervall",
        "PraehospitalIntervall",
    ]:
        filtered_df = filtered_df[(filtered_df[col].isna()) | (filtered_df[col] >= 0)]

    return filtered_df


def calculate_statistics(df):
    """Berechne Statistiken für Prähospitalintervall"""
    if df.empty or "PraehospitalIntervall" not in df.columns:
        return {
            "count": 0,
            "median": None,
            "mean": None,
            "q25": None,
            "q75": None,
            "p90": None,
            "under_60min": None,
        }

    valid_data = df.dropna(subset=["PraehospitalIntervall"])

    if len(valid_data) == 0:
        return {
            "count": 0,
            "median": None,
            "mean": None,
            "q25": None,
            "q75": None,
            "p90": None,
            "under_60min": None,
        }

    praehospital = valid_data["PraehospitalIntervall"]

    return {
        "count": len(valid_data),
        "median": praehospital.median(),
        "mean": praehospital.mean(),
        "q25": praehospital.quantile(0.25),
        "q75": praehospital.quantile(0.75),
        "p90": praehospital.quantile(0.90),
        "under_60min": (praehospital <= 60).mean() * 100,
    }


# Lade Daten
with st.spinner("Lade Daten..."):
    df, df_rea, df_gcs, df_krankenhaus = load_and_prepare_data_v3()

st.markdown(
    """
## Übersicht
Diese Analyse vergleicht die Prähospitalintervalle aller Hauptdiagnosen aus den Qualitätsindikatoren 1.1.1 bis 1.1.6:
- **Polytrauma** (1.1.1) - Diagnosebasierte Filterung
- **SHT (GCS<8)** - Schädel-Hirn-Trauma mit Glasgow Coma Scale < 8
- **STEMI** (1.1.2) - ST-Hebungsinfarkt
- **Stroke** (1.1.3) - Akuter Schlaganfall
- **Reanimation** (1.1.4) - Basierend auf rea_status=True
- **SHT** - Schädel-Hirn-Trauma (1.1.5)
- **Sepsis** (1.1.6)

**Vergleichsperioden:**
- 📊 **Fokus:** Juli - Dezember 2024
- 📈 **Referenz:** Gesamter verfügbarer Datenzeitraum
"""
)

# Definiere Zeiträume
focus_start = pd.Timestamp("2024-07-01", tz="UTC")
focus_end = pd.Timestamp("2024-12-31", tz="UTC")

# Show data range overview
if "missionDate" in df.columns:
    df_with_date = df.dropna(subset=["missionDate"])
    if not df_with_date.empty:
        date_min = df_with_date["missionDate"].min()
        date_max = df_with_date["missionDate"].max()

        st.info(
            f"📅 **Datenzeitraum 'Gesamt Einsätze':** {date_min.strftime('%d.%m.%Y')} bis {date_max.strftime('%d.%m.%Y')} "
            f"({len(df_with_date):,} Einsätze mit gültigem Datum)"
        )
    else:
        st.warning("Keine Einsätze mit gültigem Datum gefunden.")
else:
    st.warning("Keine Datumsinformationen verfügbar.")

# Erstelle Tabs für verschiedene Ansichten
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 Übersicht Vergleich",
        "📈 Detailstatistiken",
        "🎯 Zeitreihenanalyse",
        "🏥 Zielklinik-Analyse",
    ]
)

diagnoses = [
    "Polytrauma",
    "SHT (GCS<8)",
    "STEMI",
    "Stroke",
    "Reanimation",
    "SHT",
    "Sepsis",
]

with tab1:
    st.subheader("Prähospitalintervall-Vergleich: Juli-Dezember 2024 vs. Gesamt")

    # Sammle Statistiken für alle Diagnosen
    comparison_data = []

    for diagnosis in diagnoses:
        with st.spinner(f"Verarbeite {diagnosis}..."):
            # Bereite Daten vor
            diagnosis_df = prepare_diagnosis_data(df, df_rea, diagnosis, df_gcs)

            if not diagnosis_df.empty and "missionDate" in diagnosis_df.columns:
                # Fokusperiode (Juli-Dezember 2024)
                focus_df = diagnosis_df[
                    (diagnosis_df["missionDate"] >= focus_start)
                    & (diagnosis_df["missionDate"] <= focus_end)
                ]

                # Gesamtdaten
                total_df = diagnosis_df

                # Berechne Statistiken
                focus_stats = calculate_statistics(focus_df)
                total_stats = calculate_statistics(total_df)

                comparison_data.append(
                    {
                        "Diagnose": diagnosis,
                        "Fokus_Anzahl": focus_stats["count"],
                        "Fokus_Median": focus_stats["median"],
                        "Fokus_Unter60Min": focus_stats["under_60min"],
                        "Gesamt_Anzahl": total_stats["count"],
                        "Gesamt_Median": total_stats["median"],
                        "Gesamt_Unter60Min": total_stats["under_60min"],
                    }
                )

    # Erstelle Vergleichstabelle
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)

        # Formatiere die Anzeige
        st.markdown("### 📊 Vergleichsübersicht")

        # Metrics in Spalten
        cols = st.columns(len(diagnoses))

        for i, (_, row) in enumerate(comparison_df.iterrows()):
            with cols[i]:
                st.metric(
                    label=row["Diagnose"],
                    value=(
                        f"{row['Fokus_Median']:.1f} min"
                        if pd.notna(row["Fokus_Median"])
                        else "N/A"
                    ),
                    delta=(
                        f"{row['Fokus_Median'] - row['Gesamt_Median']:.1f} min"
                        if pd.notna(row["Fokus_Median"])
                        and pd.notna(row["Gesamt_Median"])
                        else None
                    ),
                )
                st.caption(
                    f"Fokus: {row['Fokus_Anzahl']} | Gesamt: {row['Gesamt_Anzahl']}"
                )

        # Detaillierte Tabelle im Schema-Format
        st.markdown("### 📋 Detaillierte Intervall-Vergleichstabelle")

        # Create detailed interval comparison table
        def create_detailed_interval_table():
            # Collect detailed statistics for all diagnoses
            detailed_stats = {}

            for diagnosis in diagnoses:
                diagnosis_df = prepare_diagnosis_data(df, df_rea, diagnosis, df_gcs)

                if not diagnosis_df.empty and "missionDate" in diagnosis_df.columns:
                    # Focus period data
                    focus_df = diagnosis_df[
                        (diagnosis_df["missionDate"] >= focus_start)
                        & (diagnosis_df["missionDate"] <= focus_end)
                    ]

                    # Calculate detailed statistics for each interval
                    intervals = {
                        "Prähospitalintervall": "PraehospitalIntervall",
                        "Reaktionsintervall": "ReaktionsIntervall",
                        "Versorgungsintervall": "VersorgungsIntervall",
                        "Transportintervall": "TransportIntervall",
                    }

                    diagnosis_stats = {}
                    for interval_name, interval_col in intervals.items():
                        focus_valid = focus_df.dropna(subset=[interval_col])
                        if len(focus_valid) > 0:
                            values = focus_valid[interval_col]
                            diagnosis_stats[f"{interval_name} n"] = len(focus_valid)
                            diagnosis_stats[f"{interval_name} Median"] = (
                                f"{values.median():.1f}"
                            )
                            diagnosis_stats[f"{interval_name} P10"] = (
                                f"{values.quantile(0.10):.1f}"
                            )
                            diagnosis_stats[f"{interval_name} P25"] = (
                                f"{values.quantile(0.25):.1f}"
                            )
                            diagnosis_stats[f"{interval_name} P75"] = (
                                f"{values.quantile(0.75):.1f}"
                            )
                            diagnosis_stats[f"{interval_name} P90"] = (
                                f"{values.quantile(0.90):.1f}"
                            )
                            diagnosis_stats[f"{interval_name} Max"] = (
                                f"{values.max():.1f}"
                            )
                        else:
                            diagnosis_stats[f"{interval_name} n"] = 0
                            for stat in ["Median", "P10", "P25", "P75", "P90", "Max"]:
                                diagnosis_stats[f"{interval_name} {stat}"] = "-"

                    detailed_stats[diagnosis] = diagnosis_stats

            # Create table data
            table_data = []

            # Header with diagnosis names and sample counts
            header_row = ["Parameter"]
            for diagnosis in diagnoses:
                if diagnosis in detailed_stats:
                    # Get total n for this diagnosis (use Prähospitalintervall as reference)
                    total_n = detailed_stats[diagnosis].get("Prähospitalintervall n", 0)
                    header_row.append(f"{diagnosis}\nn = {total_n}")
                else:
                    header_row.append(f"{diagnosis}\nn = 0")

            table_data.append(header_row)

            # Add interval rows
            for interval_name in [
                "Prähospitalintervall",
                "Reaktionsintervall",
                "Versorgungsintervall",
                "Transportintervall",
            ]:
                for stat_name, stat_key in [
                    ("Median (50. Perzentil)", "Median"),
                    ("10. Perzentil", "P10"),
                    ("25. Perzentil", "P25"),
                    ("75. Perzentil", "P75"),
                    ("90. Perzentil", "P90"),
                    ("Maximum", "Max"),
                ]:
                    if stat_name == "Median (50. Perzentil)":
                        # Add interval header
                        interval_header = [f"**{interval_name}**"] + ["-"] * len(
                            diagnoses
                        )
                        table_data.append(interval_header)

                    # Add statistic row
                    row = [stat_name]
                    for diagnosis in diagnoses:
                        if diagnosis in detailed_stats:
                            value = detailed_stats[diagnosis].get(
                                f"{interval_name} {stat_key}", "-"
                            )
                            if value != "-" and stat_key != "n":
                                row.append(f"{value} min")
                            else:
                                row.append(value)
                        else:
                            row.append("-")
                    table_data.append(row)

            return table_data

        # Generate and display table
        table_data = create_detailed_interval_table()

        # Create DataFrame for display
        if table_data:
            detailed_df = pd.DataFrame(table_data[1:], columns=table_data[0])

            # Style the table
            st.dataframe(
                detailed_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Parameter": st.column_config.TextColumn(
                        "Parameter", width="medium"
                    )
                },
            )

        # Visualisierung
        st.markdown("### 📊 Medianvergleich")

        # Bereite Daten für Plotly vor
        plot_data = []
        for _, row in comparison_df.iterrows():
            if pd.notna(row["Fokus_Median"]):
                plot_data.append(
                    {
                        "Diagnose": row["Diagnose"],
                        "Periode": "Juli-Dez 2024",
                        "Median": row["Fokus_Median"],
                    }
                )
            if pd.notna(row["Gesamt_Median"]):
                plot_data.append(
                    {
                        "Diagnose": row["Diagnose"],
                        "Periode": "Gesamt",
                        "Median": row["Gesamt_Median"],
                    }
                )

        if plot_data:
            plot_df = pd.DataFrame(plot_data)

            fig = px.bar(
                plot_df,
                x="Diagnose",
                y="Median",
                color="Periode",
                barmode="group",
                title="Medianvergleich Prähospitalintervall",
                labels={"Median": "Median Prähospitalintervall (Minuten)"},
                color_discrete_map={"Juli-Dez 2024": "#1f77b4", "Gesamt": "#ff7f0e"},
            )

            # Zielwert-Linie bei 60 Minuten
            fig.add_hline(
                y=60,
                line_dash="dash",
                line_color="red",
                annotation_text="Zielwert: 60 min",
            )

            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Detaillierte Statistiken nach Diagnose")

    selected_diagnosis = st.selectbox(
        "Diagnose auswählen:", diagnoses, key="detail_diagnosis"
    )

    if selected_diagnosis:
        diagnosis_df = prepare_diagnosis_data(df, df_rea, selected_diagnosis, df_gcs)

        if not diagnosis_df.empty and "missionDate" in diagnosis_df.columns:
            # Filtere für Fokusperiode
            focus_df = diagnosis_df[
                (diagnosis_df["missionDate"] >= focus_start)
                & (diagnosis_df["missionDate"] <= focus_end)
            ]

            # Zwei Spalten für Vergleich
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📊 Juli - Dezember 2024")
                focus_stats = calculate_statistics(focus_df)

                if focus_stats["count"] > 0:
                    st.metric("Anzahl Einsätze", focus_stats["count"])
                    st.metric("Median", f"{focus_stats['median']:.1f} min")
                    st.metric("Mittelwert", f"{focus_stats['mean']:.1f} min")
                    st.metric("Einsätze < 60 min", f"{focus_stats['under_60min']:.1f}%")

                    # Perzentile
                    st.markdown("**Perzentile:**")
                    st.write(f"25%: {focus_stats['q25']:.1f} min")
                    st.write(f"75%: {focus_stats['q75']:.1f} min")
                    st.write(f"90%: {focus_stats['p90']:.1f} min")
                else:
                    st.warning("Keine Daten für die Fokusperiode verfügbar.")

            with col2:
                st.markdown("#### 📈 Gesamter Datenzeitraum")
                total_stats = calculate_statistics(diagnosis_df)

                if total_stats["count"] > 0:
                    st.metric("Anzahl Einsätze", total_stats["count"])
                    st.metric("Median", f"{total_stats['median']:.1f} min")
                    st.metric("Mittelwert", f"{total_stats['mean']:.1f} min")
                    st.metric("Einsätze < 60 min", f"{total_stats['under_60min']:.1f}%")

                    # Perzentile
                    st.markdown("**Perzentile:**")
                    st.write(f"25%: {total_stats['q25']:.1f} min")
                    st.write(f"75%: {total_stats['q75']:.1f} min")
                    st.write(f"90%: {total_stats['p90']:.1f} min")
                else:
                    st.warning("Keine Daten verfügbar.")

            # Box-Plot Vergleich
            if focus_stats["count"] > 0 and total_stats["count"] > 0:
                st.markdown("### Verteilungsvergleich")

                # Bereite Daten für Box-Plot vor
                box_data = []

                # Fokusperiode
                focus_valid = focus_df.dropna(subset=["PraehospitalIntervall"])
                for val in focus_valid["PraehospitalIntervall"]:
                    box_data.append(
                        {"Periode": "Juli-Dez 2024", "Prähospitalintervall": val}
                    )

                # Gesamtdaten
                total_valid = diagnosis_df.dropna(subset=["PraehospitalIntervall"])
                for val in total_valid["PraehospitalIntervall"]:
                    box_data.append({"Periode": "Gesamt", "Prähospitalintervall": val})

                if box_data:
                    box_df = pd.DataFrame(box_data)

                    fig = px.box(
                        box_df,
                        x="Periode",
                        y="Prähospitalintervall",
                        color="Periode",
                        title=f"Verteilung Prähospitalintervall - {selected_diagnosis}",
                        labels={
                            "Prähospitalintervall": "Prähospitalintervall (Minuten)"
                        },
                    )

                    fig.add_hline(y=60, line_dash="dash", line_color="red")
                    fig.update_layout(height=500, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Zeitreihenanalyse")

    selected_diagnosis_ts = st.selectbox(
        "Diagnose für Zeitreihenanalyse:", diagnoses, key="ts_diagnosis"
    )

    if selected_diagnosis_ts:
        diagnosis_df = prepare_diagnosis_data(df, df_rea, selected_diagnosis_ts, df_gcs)

        if not diagnosis_df.empty and "missionDate" in diagnosis_df.columns:
            valid_data = diagnosis_df.dropna(
                subset=["missionDate", "PraehospitalIntervall"]
            )

            if len(valid_data) > 5:
                # Gruppiere nach Monat
                valid_data["Month"] = valid_data["missionDate"].dt.to_period("M")

                monthly_stats = (
                    valid_data.groupby("Month")["PraehospitalIntervall"]
                    .agg(
                        [
                            ("Anzahl", "count"),
                            ("Median", "median"),
                            ("Mittelwert", "mean"),
                            ("Q25", lambda x: np.percentile(x, 25)),
                            ("Q75", lambda x: np.percentile(x, 75)),
                        ]
                    )
                    .reset_index()
                )

                monthly_stats["Month"] = (
                    monthly_stats["Month"].dt.to_timestamp().dt.tz_localize("UTC")
                )

                # Markiere Fokusperiode
                def classify_period(x):
                    if focus_start <= x <= focus_end:
                        return "Fokusperiode"
                    else:
                        return "Außerhalb"

                monthly_stats["Periode"] = monthly_stats["Month"].apply(classify_period)

                # Trend-Plot
                fig = go.Figure()

                # Quartile als Bereich
                fig.add_trace(
                    go.Scatter(
                        x=monthly_stats["Month"],
                        y=monthly_stats["Q75"],
                        fill=None,
                        mode="lines",
                        line_color="rgba(0,100,80,0.2)",
                        name="Q75",
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=monthly_stats["Month"],
                        y=monthly_stats["Q25"],
                        fill="tonexty",
                        mode="lines",
                        line_color="rgba(0,100,80,0.2)",
                        name="Q25-Q75 Bereich",
                    )
                )

                # Median-Linie mit Farbe nach Periode
                focus_data = monthly_stats[monthly_stats["Periode"] == "Fokusperiode"]
                other_data = monthly_stats[monthly_stats["Periode"] == "Außerhalb"]

                if not focus_data.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=focus_data["Month"],
                            y=focus_data["Median"],
                            mode="lines+markers",
                            line=dict(color="red", width=3),
                            marker=dict(size=8),
                            name="Median (Fokusperiode)",
                        )
                    )

                if not other_data.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=other_data["Month"],
                            y=other_data["Median"],
                            mode="lines+markers",
                            line=dict(color="blue", width=2),
                            marker=dict(size=6),
                            name="Median (Gesamt)",
                        )
                    )

                # Zielwert-Linie
                fig.add_hline(
                    y=60,
                    line_dash="dash",
                    line_color="orange",
                    annotation_text="Zielwert: 60 min",
                )

                # Markiere Fokusperiode
                fig.add_vrect(
                    x0=focus_start,
                    x1=focus_end,
                    fillcolor="yellow",
                    opacity=0.2,
                    layer="below",
                    line_width=0,
                    annotation_text="Fokusperiode",
                    annotation_position="top left",
                )

                fig.update_layout(
                    title=f"Zeitreihenentwicklung Prähospitalintervall - {selected_diagnosis_ts}",
                    xaxis_title="Monat",
                    yaxis_title="Prähospitalintervall (Minuten)",
                    height=600,
                    hovermode="x unified",
                )

                st.plotly_chart(fig, use_container_width=True)

                # Monatliche Statistiken Tabelle
                st.markdown("### Monatliche Statistiken")
                display_monthly = monthly_stats.copy()
                display_monthly["Monat"] = display_monthly["Month"].dt.strftime("%Y-%m")
                display_monthly = display_monthly[
                    ["Monat", "Periode", "Anzahl", "Median", "Mittelwert", "Q25", "Q75"]
                ].round(1)

                st.dataframe(display_monthly, use_container_width=True, hide_index=True)
            else:
                st.warning("Nicht genügend Daten für Zeitreihenanalyse verfügbar.")

with tab4:
    st.subheader("Zielklinik-Analyse (5.1-5.3)")

    st.markdown(
        """
    Diese Analyse überprüft, ob Patienten in geeignete Zielkliniken transportiert wurden:
    - **5.1 Traumazentrum:** Polytrauma-Patienten
    - **5.2 Herzkatheter-Zentrum:** STEMI/ACS-Patienten  
    - **5.3 Stroke-Unit:** Schlaganfall-Patienten
    """
    )

    # Add hospital eligibility analysis
    try:
        hospital_data_available = not df_krankenhaus.empty
    except NameError:
        hospital_data_available = False
        st.error("Hospital data not loaded. Please check the data loading function.")

    if hospital_data_available:
        # Apply hospital eligibility check to ALL data
        df_with_eligibility = check_hospital_eligibility(df_krankenhaus, df.copy())

        # Analysis by diagnosis type
        st.markdown("### Analyse nach Diagnosegruppe")

        # 5.1 Polytrauma/Schwerverletzt
        st.markdown("#### 5.1 Traumazentrum (Polytrauma)")
        df_trauma = df_with_eligibility.copy()
        df_trauma["leadingDiagnosis"] = df_trauma["leadingDiagnosis"].fillna("")
        trauma_mask = (
            df_trauma["leadingDiagnosis"]
            .str.lower()
            .str.contains("polytrauma|schwerverletzt")
        )
        trauma_cases = df_trauma[trauma_mask].copy()

        trauma_count = len(trauma_cases)
        if trauma_count > 0:
            trauma_eligible = trauma_cases["hospital_eligible"].sum()
            trauma_rate = (
                (trauma_eligible / trauma_count * 100) if trauma_count > 0 else 0
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Polytrauma-Fälle", f"{trauma_count}")
            col2.metric("Geeignetes Traumazentrum", f"{trauma_eligible}")
            col3.metric("Quote", f"{trauma_rate:.1f}%")
        else:
            st.info("Keine Polytrauma-Fälle gefunden")

        # 5.2 STEMI/ACS
        st.markdown("#### 5.2 Herzkatheter-Zentrum (STEMI/ACS)")
        df_stemi = df_with_eligibility.copy()
        df_stemi["leadingDiagnosis"] = df_stemi["leadingDiagnosis"].fillna("")
        stemi_mask = (
            df_stemi["leadingDiagnosis"]
            .str.lower()
            .str.contains("stemi|acs|herzinfarkt")
        )
        stemi_cases = df_stemi[stemi_mask].copy()

        stemi_count = len(stemi_cases)
        if stemi_count > 0:
            stemi_eligible = stemi_cases["hospital_eligible"].sum()
            stemi_rate = (stemi_eligible / stemi_count * 100) if stemi_count > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("STEMI/ACS-Fälle", f"{stemi_count}")
            col2.metric("Geeignetes Katheterlabor", f"{stemi_eligible}")
            col3.metric("Quote", f"{stemi_rate:.1f}%")
        else:
            st.info("Keine STEMI/ACS-Fälle gefunden")

        # 5.3 Stroke/Schlaganfall
        st.markdown("#### 5.3 Stroke-Unit (Schlaganfall)")
        df_stroke = df_with_eligibility.copy()
        df_stroke["leadingDiagnosis"] = df_stroke["leadingDiagnosis"].fillna("")
        stroke_mask = (
            df_stroke["leadingDiagnosis"]
            .str.lower()
            .str.contains("schlaganfall|stroke|tia|apoplex")
        )
        stroke_cases = df_stroke[stroke_mask].copy()

        stroke_count = len(stroke_cases)
        if stroke_count > 0:
            stroke_eligible = stroke_cases["hospital_eligible"].sum()
            stroke_rate = (
                (stroke_eligible / stroke_count * 100) if stroke_count > 0 else 0
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Schlaganfall-Fälle", f"{stroke_count}")
            col2.metric("Geeignete Stroke-Unit", f"{stroke_eligible}")
            col3.metric("Quote", f"{stroke_rate:.1f}%")
        else:
            st.info("Keine Schlaganfall-Fälle gefunden")

        # Visualization of hospital eligibility by diagnosis
        st.markdown("### 📊 Vergleich der Zielklinik-Eignung")

        hospital_comparison_data = []

        if trauma_count > 0:
            hospital_comparison_data.append(
                {
                    "Diagnose": "Polytrauma",
                    "Geeignete": int(trauma_eligible),
                    "Nicht geeignet": trauma_count - int(trauma_eligible),
                }
            )

        if stemi_count > 0:
            hospital_comparison_data.append(
                {
                    "Diagnose": "STEMI/ACS",
                    "Geeignete": int(stemi_eligible),
                    "Nicht geeignet": stemi_count - int(stemi_eligible),
                }
            )

        if stroke_count > 0:
            hospital_comparison_data.append(
                {
                    "Diagnose": "Schlaganfall",
                    "Geeignete": int(stroke_eligible),
                    "Nicht geeignet": stroke_count - int(stroke_eligible),
                }
            )

        if hospital_comparison_data:
            comparison_df = pd.DataFrame(hospital_comparison_data)

            fig = px.bar(
                comparison_df,
                x="Diagnose",
                y=["Geeignete", "Nicht geeignet"],
                title="Zielklinik-Eignung nach Diagnosegruppe",
                labels={"value": "Anzahl Fälle", "variable": "Status"},
                barmode="stack",
                color_discrete_map={
                    "Geeignete": "#2ecc71",
                    "Nicht geeignet": "#e74c3c",
                },
            )

            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Hospital assignments by time interval
        st.markdown("### 🏥 Krankenhausverteilung nach Zeitintervall")

        # Group by month and show hospital assignments
        if "missionDate" in df_with_eligibility.columns:
            # For each diagnosis, show distribution
            for diag_name, diag_cases, diag_label in [
                ("Polytrauma", trauma_cases, "Polytrauma"),
                ("STEMI", stemi_cases, "STEMI/ACS"),
                ("Schlaganfall", stroke_cases, "Schlaganfall"),
            ]:
                if not diag_cases.empty and "missionDate" in diag_cases.columns:
                    diag_with_month = diag_cases.copy()
                    diag_with_month["Month"] = (
                        diag_with_month["missionDate"].dt.to_period("M").astype(str)
                    )

                    monthly_hospital = (
                        diag_with_month.groupby(["Month", "hospital_eligible"])
                        .size()
                        .unstack(fill_value=0)
                    )

                    # Rename columns
                    monthly_hospital.columns = [
                        "Nicht geeignet" if col is False else "Geeignet"
                        for col in monthly_hospital.columns
                    ]

                    monthly_hospital_reset = monthly_hospital.reset_index()

                    fig_monthly = px.bar(
                        monthly_hospital_reset,
                        x="Month",
                        y=list(monthly_hospital.columns),
                        title=f"Krankenhausverteilung {diag_label}",
                        labels={"value": "Anzahl Fälle", "Month": "Monat"},
                        barmode="stack",
                        color_discrete_map={
                            "Geeignet": "#2ecc71",
                            "Nicht geeignet": "#e74c3c",
                        },
                    )

                    fig_monthly.update_layout(height=350)
                    st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.error("Hospital data not available")

# Footer
st.markdown("---")
st.markdown(
    """
**Hinweise:**
- Prähospitalintervall = StatusAlarm bis Status8
- Zielwert für alle Diagnosen: ≤ 60 Minuten
- Fokusperiode: 01.07.2024 - 31.12.2024
- Negative Zeitwerte wurden automatisch ausgeschlossen
"""
)

if st.checkbox("🔧 Debug-Informationen anzeigen"):
    st.write("DataFrame Info:")
    st.write(f"Gesamt Protokolle geladen: {len(df)}")
    st.write(f"Verfügbare Spalten: {list(df.columns)}")
    if "missionDate" in df.columns:
        df_with_date = df.dropna(subset=["missionDate"])
        if not df_with_date.empty:
            st.write(
                f"Datumsbereich: {df_with_date['missionDate'].min()} bis {df_with_date['missionDate'].max()}"
            )
    if not df_rea.empty:
        st.write(f"Reanimation Protokolle: {len(df_rea)}")
        st.write(
            f"Reanimation mit rea_status=True: {len(df_rea[df_rea['rea_status'] == True])}"
        )
    if not df_gcs.empty:
        st.write(f"GCS Messungen: {len(df_gcs)}")
        st.write(f"GCS Typen: {df_gcs['type'].unique().tolist()}")
        gcs_under_8 = df_gcs[pd.to_numeric(df_gcs["value_num"], errors="coerce") < 8]
        st.write(f"GCS < 8 Messungen: {len(gcs_under_8)}")
    try:
        st.write(
            f"Krankenhaus Daten: {len(df_krankenhaus) if 'df_krankenhaus' in locals() else 'Nicht definiert'}"
        )
        if "df_krankenhaus" in locals() and not df_krankenhaus.empty:
            st.write(f"Krankenhaus Spalten: {list(df_krankenhaus.columns)}")
    except NameError:
        st.write("df_krankenhaus ist nicht definiert")
    if not df_gcs.empty:
        st.write(f"GCS Messungen: {len(df_gcs)}")
        st.write(f"GCS Typen: {df_gcs['type'].unique().tolist()}")
        gcs_under_8 = df_gcs[pd.to_numeric(df_gcs["value_num"], errors="coerce") < 8]
        st.write(f"GCS < 8 Messungen: {len(gcs_under_8)}")
