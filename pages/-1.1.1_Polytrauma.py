import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from data_loader import data_loading
import datetime

st.title("1.1.1 Prähospitalintervall bei Polytrauma")

# Lade Daten
df_index = data_loading(metric="Index")
df_details = data_loading(metric="Details")


# Merge df_index and df_details
if not df_details.empty:
    # When merging, you can explicitly exclude the _id columns
    if '_id' in df_index.columns and '_id' in df_details.columns:
        merged_df = pd.merge(
            df_index.drop(columns=['_id']), 
            df_details.drop(columns=['_id']), 
            on='protocolId', 
            how='outer',
            suffixes=('', '_y')  # Avoid duplicate column names
        )
    else:
        merged_df = pd.merge(
            df_index, 
            df_details, 
            on='protocolId', 
            how='outer',
            suffixes=('', '_y')  # Avoid duplicate column names
        )
else:
    merged_df = df_index  # Use df_index if df_details is empty

df = merged_df

# Filteroptionen innerhalb der Hauptseite in einem Expander
with st.expander("Filteroptionen", expanded=False):
    # Erstelle 3 Spalten für die Filter
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filter für Einsatzart - mit verbesserter Fehlerbehandlung
        if 'missionType' in df.columns:
            # Entferne NaN-Werte und konvertiere alle Werte zu Strings
            mission_types = [str(mt) for mt in df['missionType'].unique() if pd.notna(mt)]
            # Sortiere die Strings
            all_mission_types = sorted(mission_types)
            
            # Finde Standard-Typen, wenn vorhanden
            default_types = [mt for mt in all_mission_types if mt in ["Pauschale RTW", "RTW - Transport"]]
            
            selected_mission_types = st.multiselect(
                "Einsatzart auswählen",
                options=all_mission_types,
                default=default_types if default_types else all_mission_types[:1] if all_mission_types else []
            )
        else:
            st.warning("Spalte 'missionType' nicht gefunden")
            selected_mission_types = []
    
    with col2:
        # Filter für Diagnosen - mit verbesserter Fehlerbehandlung
        if 'leadingDiagnosis' in df.columns:
            # Entferne NaN-Werte und konvertiere alle Werte zu Strings
            diagnoses = [str(d) for d in df['leadingDiagnosis'].unique() if pd.notna(d)]
            all_diagnoses = sorted(diagnoses)
            
            # Finde Trauma-Diagnosen, wenn vorhanden
            trauma_diagnoses = [d for d in all_diagnoses if 'polytrauma' in d.lower()]
            default_diagnoses = trauma_diagnoses if trauma_diagnoses else all_diagnoses[:1] if all_diagnoses else []
            
            selected_diagnoses = st.multiselect(
                "Diagnosen auswählen",
                options=all_diagnoses,
                default=default_diagnoses
            )
        else:
            st.warning("Spalte 'leadingDiagnosis' nicht gefunden")
            selected_diagnoses = []
    
    with col3:
        # Filter für Jahre - mit verbesserter Fehlerbehandlung
        try:
            if 'missionDate' in df.columns:
                df['Jahr'] = pd.to_datetime(df['missionDate'], errors='coerce').dt.year
                years = sorted([y for y in df['Jahr'].unique() if pd.notna(y)])
                
                selected_years = st.multiselect(
                    "Jahre auswählen",
                    options=years,
                    default=years[-2:] if len(years) > 1 else years if years else []
                )
            else:
                st.warning("Spalte 'missionDate' nicht gefunden")
                selected_years = []
        except Exception as e:
            st.warning(f"Datumsfilter nicht verfügbar: {e}")
            selected_years = []

# Filtere Daten
filtered_df = df.copy()

# Wende Filter an
if selected_mission_types and 'missionType' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['missionType'].isin(selected_mission_types)]
if selected_diagnoses:
    filtered_df = filtered_df[filtered_df['leadingDiagnosis'].isin(selected_diagnoses)]
if selected_years and 'Jahr' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Jahr'].isin(selected_years)]

# Anzahl der Datensätze nach Filterung anzeigen
st.write(f"Anzahl gefilterte Einsätze: {len(filtered_df)}")


# Funktion zum sicheren Berechnen von Zeitintervallen
def calculate_time_diff_minutes(row, start_col, end_col):
    try:
        if pd.notnull(row[start_col]) and pd.notnull(row[end_col]):
            delta = row[end_col] - row[start_col]
            if isinstance(delta, datetime.timedelta):
                return delta.total_seconds() / 60
            return None
        return None
    except:
        return None

# Berechne Zeitintervalle auf sichere Weise
filtered_df['ReaktionsIntervall'] = filtered_df.apply(lambda row: calculate_time_diff_minutes(row, 'StatusAlarm', 'Status4'), axis=1)
filtered_df['VersorgungsIntervall'] = filtered_df.apply(lambda row: calculate_time_diff_minutes(row, 'Status4', 'Status7'), axis=1)
filtered_df['TransportIntervall'] = filtered_df.apply(lambda row: calculate_time_diff_minutes(row, 'Status7', 'Status8'), axis=1)
filtered_df['PraehospitalIntervall'] = filtered_df.apply(lambda row: calculate_time_diff_minutes(row, 'StatusAlarm', 'Status8'), axis=1)

# Entferne negative Werte und Ausreißer
for col in ['ReaktionsIntervall', 'VersorgungsIntervall', 'TransportIntervall', 'PraehospitalIntervall']:
    filtered_df = filtered_df[(filtered_df[col].isna()) | (filtered_df[col] >= 0)]

# Qualitätsziel und Rationale mit Markdown
st.markdown("""
## Qualitätsziel
**Das Prähospitalintervall beträgt bei Patienten mit Tracerdiagnose Polytrauma maximal 60 Minuten.**

Der Patient wird zeitgerecht in einer geeigneten Behandlungseinrichtung weiterversorgt.

## Rationale
Bei polytraumatisierten Patienten hat die rasche zielgerichtete Diagnostik und Therapie in der Klinik einen relevanten Einfluss auf den Behandlungserfolg.

Das interdisziplinäre Eckpunktepapier zur Gesundheitsversorgung in Deutschland fordert ein Prähospitalintervall von **maximal 60 Minuten** für Schwerverletzte. In der aktuellen S3-Leitlinie Schwerverletztenversorgung ist ein quantitativ festgelegtes Ziel für das Prähospitalintervall jedoch nicht mehr zu finden. Auch bei Kindern soll die Zeitspanne bis zur Klinikaufnahme so kurz wie möglich gehalten werden.
""")

# Berechnungsgrundlage
st.markdown("""
## Berechnungsgrundlage
**Indikator:** Intervall zwischen Aufschaltung des Notrufs in der Leitstelle und Ankunft Zielklinik (FMS Status 8) (Prähospitalintervall).

**Grundgesamtheit:** Primäreinsätze in der Notfallrettung bei Patienten mit der Diagnose Polytrauma, die lebend in eine Klinik aufgenommen werden.

**Ergebnisdarstellung:** Median, Quartile, 10. und 90. Perzentil. Differenzierung der Ergebnisse nach Reaktionsintervall (Aufschaltung des Notrufs bis Status 4), Versorgungsintervall (Status 4 bis Status 7) und Transportintervall (Status 7 bis Status 8).
""")

st.subheader("Gefilterte Datenvorschau")
st.write(filtered_df)

# Überprüfe, ob Daten mit gültigen Zeiten existieren
valid_data = filtered_df.dropna(subset=['PraehospitalIntervall'])

if len(valid_data) == 0:
    st.warning("Keine gültigen Zeitdaten für die gewählten Filter gefunden. Möglicherweise fehlen Status-Zeitpunkte in den Einsatzdaten.")
else:
    # Hauptstatistiken anzeigen
    st.markdown("## Übersicht Prähospitalintervall")
    
    # KPI-Metriken 
    col1, col2, col3 = st.columns(3)
    
    # Berechne Anteil der Einsätze unter 60 Minuten
    anteil_unter_60min = (valid_data['PraehospitalIntervall'] <= 60).mean() * 100
    
    with col1:
        st.metric(
            "Median Prähospitalzeit", 
            f"{valid_data['PraehospitalIntervall'].median():.1f} min",
            delta=f"{valid_data['PraehospitalIntervall'].median() - 60:.1f} min" if valid_data['PraehospitalIntervall'].median() - 60 else None,
            delta_color="inverse"
        )
    with col2:
        st.metric(
            "Einsätze < 60 min", 
            f"{anteil_unter_60min:.1f}%"
        )
    with col3:
        st.metric(
            "Anzahl Polytrauma-Einsätze", 
            f"{len(valid_data)}"
        )
    
    # Ausführliche Statistiken
    st.markdown("### Detaillierte Statistiken")
    
    # Funktion zur Berechnung der Perzentile (mit Fehlerbehandlung)
    def calculate_percentiles(series):
        series = series.dropna()
        if len(series) == 0:
            return {'10%': None, '25%': None, '50% (Median)': None, '75%': None, '90%': None}
        return {
            '10%': np.percentile(series, 10),
            '25%': np.percentile(series, 25),
            '50% (Median)': np.percentile(series, 50),
            '75%': np.percentile(series, 75),
            '90%': np.percentile(series, 90)
        }
    
    # Perzentile berechnen
    stats_praehospital = calculate_percentiles(valid_data['PraehospitalIntervall'])
    stats_reaktion = calculate_percentiles(valid_data['ReaktionsIntervall'])
    stats_versorgung = calculate_percentiles(valid_data['VersorgungsIntervall'])
    stats_transport = calculate_percentiles(valid_data['TransportIntervall'])
    
    # Daten für Tabelle
    stats_df = pd.DataFrame({
        'Prähospitalintervall': stats_praehospital,
        'Reaktionsintervall': stats_reaktion,
        'Versorgungsintervall': stats_versorgung,
        'Transportintervall': stats_transport
    })
    
    # Konvertiere zu Floats und runde (mit Fehlerbehandlung)
    for col in stats_df.columns:
        stats_df[col] = pd.to_numeric(stats_df[col], errors='coerce').round(1)
    
    # Statistik-Tabelle anzeigen
    st.dataframe(stats_df, use_container_width=True)
    
    # Box-Plot für Zeitverteilung
    st.markdown("### Verteilung der Zeitintervalle")
    
    # Daten für Box-Plot vorbereiten
    box_data = []
    for interval_name, interval_col in [
        ('Prähospitalintervall', 'PraehospitalIntervall'),
        ('Reaktionsintervall', 'ReaktionsIntervall'),
        ('Versorgungsintervall', 'VersorgungsIntervall'),
        ('Transportintervall', 'TransportIntervall')
    ]:
        for val in valid_data[interval_col].dropna():
            box_data.append({
                'Intervall': interval_name,
                'Zeit (Minuten)': val
            })
    
    box_df = pd.DataFrame(box_data)
    
    if not box_df.empty:
        # Box-Plot mit Plotly
        fig = px.box(
            box_df, 
            x='Intervall', 
            y='Zeit (Minuten)',
            color='Intervall',
            points="all",  # Zeige alle Punkte
            title="Verteilung der Zeitintervalle",
            height=500
        )
        
        # Horizontale Linie für Zielwert (60 Minuten)
        fig.add_shape(
            type="line",
            x0=-0.5,
            x1=0.5,
            y0=60,
            y1=60,
            line=dict(color="red", width=2, dash="dash"),
        )
        
        fig.add_annotation(
            x=0,
            y=65,
            text="Zielwert: 60 min",
            showarrow=False,
            font=dict(color="red")
        )
        
        # Layout verbessern
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Zeit (Minuten)",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nicht genügend Daten für eine Visualisierung der Zeitintervalle.")
    
    # Nur Zeitreihe anzeigen, wenn genügend Daten vorhanden sind
    if len(valid_data) > 5:
        try:
            # Zeitreihe für die Entwicklung
            st.markdown("### Entwicklung über Zeit")
            
            # Versuche, nach Monat zu gruppieren
            valid_data['Month'] = pd.to_datetime(valid_data['missionDate'], errors='coerce')
            if valid_data['Month'].isna().all():
                st.warning("Keine gültigen Datumswerte für die Zeitreihenanalyse verfügbar.")
            else:
                valid_data['Month'] = valid_data['Month'].dt.to_period('M')
                monthly_data = valid_data.dropna(subset=['Month', 'PraehospitalIntervall'])
                
                if len(monthly_data) > 0:
                    monthly_stats = monthly_data.groupby('Month')['PraehospitalIntervall'].agg([
                        ('Median', 'median'),
                        ('25%', lambda x: np.percentile(x, 25)),
                        ('75%', lambda x: np.percentile(x, 75))
                    ]).reset_index()
                    
                    if len(monthly_stats) > 1:  # Nur anzeigen, wenn mehr als ein Monat vorhanden ist
                        monthly_stats['Month'] = monthly_stats['Month'].dt.to_timestamp()
                        
                        # Trend-Plot
                        fig_trend = go.Figure()
                        
                        # Bereich für 25-75% Perzentil
                        fig_trend.add_trace(go.Scatter(
                            x=monthly_stats['Month'],
                            y=monthly_stats['75%'],
                            fill=None,
                            mode='lines',
                            line_color='rgba(0,100,80,0.2)',
                            name='75% Perzentil'
                        ))
                        
                        fig_trend.add_trace(go.Scatter(
                            x=monthly_stats['Month'],
                            y=monthly_stats['25%'],
                            fill='tonexty',
                            mode='lines',
                            line_color='rgba(0,100,80,0.2)',
                            name='25% Perzentil'
                        ))
                        
                        # Median-Linie
                        fig_trend.add_trace(go.Scatter(
                            x=monthly_stats['Month'],
                            y=monthly_stats['Median'],
                            mode='lines+markers',
                            line=dict(color='rgb(0,100,80)', width=2),
                            name='Median'
                        ))
                        
                        # Zielwert-Linie
                        fig_trend.add_hline(
                            y=60,
                            line_dash="dash",
                            line_color="red",
                            annotation_text="Zielwert: 60 min",
                            annotation_position="bottom right"
                        )
                        
                        # Layout anpassen
                        fig_trend.update_layout(
                            title='Entwicklung des Prähospitalintervalls (Median und Quartile)',
                            xaxis_title='Monat',
                            yaxis_title='Zeit (Minuten)',
                            hovermode='x unified',
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            )
                        )
                        
                        st.plotly_chart(fig_trend, use_container_width=True)
                    else:
                        st.info("Nicht genügend Zeitreihendaten für eine monatliche Trendanalyse.")
        except Exception as e:
            st.error(f"Fehler bei der Zeitreihenanalyse: {e}")
    
    # Pie-Chart für Anteile der verschiedenen Intervalle
    st.markdown("### Anteil der Intervalle am Gesamtprozess")
    
    # Prüfe, ob ausreichend Daten für jedes Intervall vorliegen
    valid_intervals = valid_data.dropna(subset=['ReaktionsIntervall', 'VersorgungsIntervall', 'TransportIntervall'])
    
    if len(valid_intervals) > 0:
        # Mittelwerte der Intervalle
        mean_reaktion = valid_intervals['ReaktionsIntervall'].mean()
        mean_versorgung = valid_intervals['VersorgungsIntervall'].mean()
        mean_transport = valid_intervals['TransportIntervall'].mean()
        
        # Pie-Chart
        fig_pie = px.pie(
            values=[mean_reaktion, mean_versorgung, mean_transport],
            names=['Reaktionsintervall', 'Versorgungsintervall', 'Transportintervall'],
            title='Durchschnittlicher Anteil der Intervalle am Gesamtprozess',
            color_discrete_sequence=px.colors.sequential.Viridis
        )
        
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("Nicht genügend vollständige Zeitdaten für die Analyse der Prozessanteile.") 