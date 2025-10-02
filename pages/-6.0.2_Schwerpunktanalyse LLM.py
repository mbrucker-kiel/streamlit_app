import streamlit as st
import pandas as pd
import requests
import json
from data_loading import data_loading

from auth import check_authentication

import os

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

def analyze_medical_text(text_content, protocol_id=None):
    """Send medical text to local LLM for structured analysis"""
    try:
        prompt = f"""
        Analysiere diesen Anamnesetext und gib eine strukturierte Analyse zurück.

        TEXT: {text_content}

        Gib deine Antwort als einfache Textzeilen mit diesem Format:

        Erklärung: Wurde in dem Anamnesetext ein Übergriff auf Einsatzkräfte beschrieben?
        UEBERGRIF_VORHANDEN: [ja/nein]
        UEBERGRIF_ART: [verbal/koerperlich/sexuell/keine]
        UEBERGRIF_TEXTBELEG: [konkreter Text aus dem Anamnesetext oder "kein"]

        Erklärung: Wurden Maßnahmen, Untersuchungen oder Transport verweigert?
        VERWEIGERUNG_VORHANDEN: [ja/nein]
        VERWEIGERUNG_MASSNAHME: [konkrete abgelehnte Maßnahme oder "keine"]
        VERWEIGERUNG_BEGRUENDUNG: [konkreter Grund oder "kein"]

        Erklärung: Welche maßnahmen wurden durchgeführt?
        HILFEBEDARF_TYP: [medizinisch/pflegerisch/aufstehhilfe/unbekannt]
        HILFEBEDARF_BESCHREIBUNG: [kurze Beschreibung oder "keine"]

        Erklärung: Liegt ein akutes Rettungsdienstliches Problem vor? (keine chronischen Krankheiten)
        MEDIZINISCHES_PROBLEM_BESCHREIBUNG: [konkrete Beschreibung oder "kein Problem"]
        MEDIZINISCHES_PROBLEM_KATEGORIE: [kardiovaskulär/respiratorisch/neurologisch/traumatologisch/intoxikation/psychisch/sonstiges/keine]

        Erklärung: Wurden sonstige Einsatzbesonderheiten beschrieben?
        AUFFAELLIGKEITEN_VORHANDEN: [ja/nein]
        AUFFAELLIGKEITEN_BESCHREIBUNG: [konkrete Beschreibung oder "keine"]

        WICHTIG: Verwende nur die erlaubten Werte in Klammern. Gib keine zusätzlichen Erklärungen.
        """

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.1
        }

        response = requests.post(
            LLM_BASE_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Fehler: HTTP {response.status_code} - {response.text}"

    except Exception as e:
        return f"Fehler beim LLM-Aufruf: {str(e)}"


def parse_llm_response(llm_text):
    """Parse the structured LLM response into individual fields"""
    result = {
        'übergriff_vorhanden': '',
        'übergriff_art': '',
        'übergriff_textbeleg': '',
        'verweigerung_vorhanden': '',
        'verweigerung_massnahme': '',
        'verweigerung_begruendung': '',
        'hilfebedarf_typ': '',
        'hilfebedarf_beschreibung': '',
        'medizinisches_problem_beschreibung': '',
        'medizinisches_problem_kategorie': '',
        'auffaelligkeiten_vorhanden': '',
        'auffaelligkeiten_beschreibung': ''
    }

    try:
        # Clean the text first
        cleaned_text = llm_text.strip()

        # Remove markdown code blocks if present
        if cleaned_text.startswith('```'):
            lines = cleaned_text.split('\n')
            # Find the first line that doesn't start with ```
            content_lines = []
            for line in lines:
                if not line.strip().startswith('```'):
                    content_lines.append(line)
                elif content_lines:  # If we already have content, stop at next ```
                    break
            cleaned_text = '\n'.join(content_lines)

        # Parse line by line
        lines = cleaned_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line or ':' not in line:
                continue

            # Split on first colon only
            key, value = line.split(':', 1)
            key = key.strip().upper()
            value = value.strip()

            # Remove brackets if present
            if value.startswith('[') and value.endswith(']'):
                value = value[1:-1]

            # Map keys to result fields
            if key == 'UEBERGRIF_VORHANDEN':
                result['übergriff_vorhanden'] = value
            elif key == 'UEBERGRIF_ART':
                result['übergriff_art'] = value
            elif key == 'UEBERGRIF_TEXTBELEG':
                result['übergriff_textbeleg'] = value
            elif key == 'VERWEIGERUNG_VORHANDEN':
                result['verweigerung_vorhanden'] = value
            elif key == 'VERWEIGERUNG_MASSNAHME':
                result['verweigerung_massnahme'] = value
            elif key == 'VERWEIGERUNG_BEGRUENDUNG':
                result['verweigerung_begruendung'] = value
            elif key == 'HILFEBEDARF_TYP':
                result['hilfebedarf_typ'] = value
            elif key == 'HILFEBEDARF_BESCHREIBUNG':
                result['hilfebedarf_beschreibung'] = value
            elif key == 'MEDIZINISCHES_PROBLEM_BESCHREIBUNG':
                result['medizinisches_problem_beschreibung'] = value
            elif key == 'MEDIZINISCHES_PROBLEM_KATEGORIE':
                result['medizinisches_problem_kategorie'] = value
            elif key == 'AUFFAELLIGKEITEN_VORHANDEN':
                result['auffaelligkeiten_vorhanden'] = value
            elif key == 'AUFFAELLIGKEITEN_BESCHREIBUNG':
                result['auffaelligkeiten_beschreibung'] = value

    except Exception as e:
        # If parsing fails, return the raw text in one field
        result['auffaelligkeiten_beschreibung'] = f"Parse error: {str(e)} - Raw text: {llm_text[:200]}"

    # Clean up results - remove any leading/trailing whitespace and empty entries
    for key in result:
        result[key] = result[key].strip() if isinstance(result[key], str) else result[key]
        if not result[key] or result[key].startswith('- ') or result[key].startswith('**'):
            result[key] = ''

    return result


st.title("Schwerpunkt LLM Anamnese Analyse")

etu_df = data_loading("ETÜ")

with st.expander("Filteroptionen"):
    city_options = ["Alle"] + list(etu_df["EO_ORT"].dropna().drop_duplicates().unique())
    selected_city = st.selectbox("EO_ORT", city_options, key="etu_city_filter")

    # Street filter
    if selected_city != "Alle":
        street_options = ["Alle"] + list(etu_df[etu_df["EO_ORT"] == selected_city]["EO_STRASSE"].dropna().drop_duplicates().unique())
    else:
        street_options = ["Alle"] + list(etu_df["EO_STRASSE"].dropna().drop_duplicates().unique())
    selected_street = st.selectbox("EO_STRASSE", street_options, key="etu_street_filter")

    # House number filter
    if selected_street != "Alle":
        if selected_city != "Alle":
            house_options = ["Alle"] + list(etu_df[(etu_df["EO_ORT"] == selected_city) & (etu_df["EO_STRASSE"] == selected_street)]["EO_STRASSE_ZUSATZ"].dropna().drop_duplicates().unique())
        else:
            house_options = ["Alle"] + list(etu_df[etu_df["EO_STRASSE"] == selected_street]["EO_STRASSE_ZUSATZ"].dropna().drop_duplicates().unique())
    else:
        house_options = ["Alle"] + list(etu_df["EO_STRASSE_ZUSATZ"].dropna().drop_duplicates().unique())
    selected_house = st.selectbox("EO_STRASSE_ZUSATZ (Hausnummer)", house_options, key="etu_house_filter")

# Filter für Einsatzdatum Intervall
st.date_input(
    "Einsatzdatum von-bis",
    value=(pd.to_datetime("2025-01-01T00:00:00"), pd.to_datetime("2025-12-31")),
    key="date_range",
)

# Get date range from session state
start_date, end_date = st.session_state["date_range"]

# Convert dates to datetime for comparison
start_dt = pd.to_datetime(start_date)
end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# Apply filters
filtered_df = etu_df.copy()

# Date filter
if "EINSATZDATUM" in filtered_df.columns:
    filtered_df["EINSATZDATUM"] = pd.to_datetime(filtered_df["EINSATZDATUM"], errors="coerce")
    filtered_df = filtered_df[
        (filtered_df["EINSATZDATUM"] >= start_dt) &
        (filtered_df["EINSATZDATUM"] <= end_dt)
    ]

# City filter
if selected_city != "Alle":
    filtered_df = filtered_df[filtered_df["EO_ORT"] == selected_city]

# Street filter
if selected_street != "Alle":
    filtered_df = filtered_df[filtered_df["EO_STRASSE"] == selected_street]

# House number filter
if selected_house != "Alle":
    filtered_df = filtered_df[filtered_df["EO_STRASSE_ZUSATZ"] == selected_house]

# Display filtered data
st.write(f"Gefilterte ETÜ-Daten: {len(filtered_df)} Einträge")

nida_df = data_loading("Index")
freetext_df = data_loading("Freetext", limit=100000)

# merge nida_df[protocolId] with etu EINSATZ_NR
if not filtered_df.empty and not nida_df.empty:
    # Merge ETÜ data with Index data based on mission numbers
    merged_df = filtered_df.merge(
        nida_df,
        left_on="EINSATZ_NR",
        right_on="missionNumber",
        how="left",
        suffixes=("_ETÜ", "_Index")
    )

    # Show merge statistics
    matched_records = merged_df["protocolId"].notna().sum()
    total_records = len(merged_df)
    st.write(f"**Übereinstimmungen gefunden:** {matched_records} von {total_records} Datensätzen ({matched_records/total_records*100:.1f}%)")

    # If Freetext data is available, merge it too
    if not freetext_df.empty:
        merged_with_freetext = merged_df.merge(
            freetext_df,
            left_on="protocolId",
            right_on="protocolId",
            how="left",
            suffixes=("", "_Freetext")
        )
else:
    st.warning("Keine Daten zum Zusammenführen verfügbar")

# Display Anamnese data from freetext
st.subheader("🏥 Anamnese-Daten")

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
                        **item
                    }
                    anamnese_data.append(anamnese_item)

# LLM Analysis Section
st.subheader("🤖 LLM Anamnese Analyse")

st.markdown("""
Durch die Analyse der Metriken, Einsatzhäufigkeit, Einsatzarten, Arbeitsdiagnosen etc. ist es möglich, bereits tiefgehende Einblicke in die Einsätze zu erhalten.

Um jedoch einen konkreten Einblick in die von der Einsatzdienst-Besatzung vorgefundene Situation zu erhalten, ist es zwingend notwendig, die Anamnese-Texte auszuwerten.

Hierfür wurde ein lokales LLM auf dem `ktw.sh`-Server aufgesetzt, welches über eine API angesprochen wird. Die Daten werden im Rechenzentrum von NNC verarbeitet, es findet **keine externe Verarbeitung** statt.

**Hinweis:**  
Die Ergebnisse der KI-Analyse sind lediglich ein Hinweis und können eine manuelle Prüfung der Anamnese-Texte **nicht ersetzen**.  
Dieses System ist ein technischer Proof of Concept. Besonders bei der strukturierten Verarbeitung von medizinischen Daten muss auf die Einhaltung des [EU AI Act](https://artificialintelligenceact.eu/) geachtet werden.

Nach dem EU AI Act sind medizinische Anwendungen in der Regel **"Hochrisiko"-KI-Systeme**. Das bedeutet:  
Strenge Anforderungen an Transparenz, Dokumentation, Risikomanagement und Kontrolle.  
Da es sich hier um die nachträgliche Auswertung von Daten zu statistischen und analytischen Zwecken handelt, sollten die Anforderungen etwas einfacher umsetzbar sein als bei KI-Systemen, die direkt in Therapieentscheidungen für Patient:innen eingebunden sind.

Das verwendete KI-Modell ist `google/gemma-3-4b-it`.  
Aufgrund der geringen Modellgröße kann es besonders schnell (relativ zur Serverkapazität, ca. 2 Minuten je Antwort) arbeiten. Es handelt sich jedoch **nicht um ein spezialisiertes medizinisches Modell**, sondern um ein allgemeines Sprachmodell. Die Antworten sind daher mit Vorsicht zu genießen und **MÜSSEN IMMER manuell geprüft werden**.

> Je Protokoll hat das Sprachmodell 120 Sekunden zum Antworten. Sollte das Modell nicht schnell genug antworten, wird die Anfrage abgebrochen.

⚠️ **Wichtig:** Die KI-Ergebnisse sind lediglich ein Hinweis und müssen immer manuell geprüft werden. 
⚠️ Jedes neustarten der Auswertung liefert andere Ergebnisse, da das Modell probabilistisch arbeitet.
LLM Prompt: https://i.imgur.com/WEFTbsl.png
""")

if anamnese_data and not merged_df.empty:
    # Get protocol IDs from the filtered/merged data
    filtered_protocol_ids = set()
    if "protocolId" in merged_df.columns:
        filtered_protocol_ids = set(merged_df["protocolId"].dropna().unique())

    # Filter anamnese data to only include protocols that match our filtered ETÜ data
    filtered_anamnese_data = [
        item for item in anamnese_data
        if item.get('protocolId') in filtered_protocol_ids
    ]

    # Ensure only unique protocolIds in the filtered anamnese data
    seen_protocol_ids = set()
    unique_filtered_anamnese_data = []
    original_count = len(filtered_anamnese_data)

    for item in filtered_anamnese_data:
        protocol_id = item.get('protocolId')
        if protocol_id and protocol_id not in seen_protocol_ids:
            seen_protocol_ids.add(protocol_id)
            unique_filtered_anamnese_data.append(item)

    # Update filtered_anamnese_data to contain only unique protocolIds
    filtered_anamnese_data = unique_filtered_anamnese_data

    duplicate_count = original_count - len(filtered_anamnese_data)
    if duplicate_count > 0:
        st.info(f"ℹ️ {duplicate_count} Duplikate nach protocolId entfernt. "
                f"Es bleiben {len(filtered_anamnese_data)} eindeutige Protokolle.")

    if filtered_anamnese_data:
        st.write(f"**Gefilterte Anamnese-Einträge für Analyse:** {len(filtered_anamnese_data)}")

        # Add button to trigger structured LLM analysis
        if st.button("� Strukturierte KI-Analyse (Übergriffe, Verweigerungen, etc.)", type="primary"):
            with st.spinner("Führe strukturierte KI-Analyse durch... Dies kann einige Minuten dauern."):

                # Check for duplicates in anamnesis texts before analysis
                st.write("🔍 Überprüfe Anamnese-Texte auf Duplikate...")

                # Extract text content from filtered data
                text_entries = []
                for item in filtered_anamnese_data:
                    protocol_id = item.get('protocolId', 'Unknown')
                    # Try different possible text fields
                    text_content = ''
                    possible_text_fields = ['text', 'content', 'value', 'data']

                    for field in possible_text_fields:
                        if field in item and item[field]:
                            text_content = str(item[field])
                            break

                    # If no specific field found, try to get any string content
                    if not text_content:
                        for key, value in item.items():
                            if key not in ['id', 'protocolId', 'description'] and \
                                    isinstance(value, str) and len(value.strip()) > 10:
                                text_content = value
                                break

                    if text_content and len(text_content.strip()) > 10:
                        text_entries.append({
                            'protocol_id': protocol_id,
                            'text_content': text_content.strip(),
                            'original_item': item
                        })

                # Remove duplicates based on text content
                unique_texts = []
                seen_texts = set()
                duplicate_count = 0

                for entry in text_entries:
                    text_hash = hash(entry['text_content'])
                    if text_hash not in seen_texts:
                        seen_texts.add(text_hash)
                        unique_texts.append(entry)
                    else:
                        duplicate_count += 1

                st.write("📊 Duplikatsanalyse abgeschlossen")
                st.write(f"- Gesamt Anamnese-Texte: {len(text_entries)}")
                st.write(f"- Eindeutige Texte: {len(unique_texts)}")
                st.write(f"- Duplikate entfernt: {duplicate_count}")

                if duplicate_count > 0:
                    st.info(f"💡 {duplicate_count} Duplikate entfernt, "
                            "API-Aufrufe gespart und Analyse beschleunigt.")

                analysis_results = []

                # Process unique anamnese entries
                st.write(f"🤖 Starte LLM-Analyse für {len(unique_texts)} eindeutige Texte...")

                for i, entry in enumerate(unique_texts):
                    protocol_id = entry['protocol_id']
                    text_content = entry['text_content']
                    st.write(f"Warte auf LLM Antwort für Protokoll {protocol_id}...")

                    # Use the structured analysis function
                    llm_result = analyze_medical_text(text_content, protocol_id)
                    parsed_result = parse_llm_response(llm_result)

                    # Create result entry for this unique text
                    base_result = {
                        'einsatz_id': protocol_id,
                        'übergriff_vorhanden': parsed_result['übergriff_vorhanden'],
                        'übergriff_art': parsed_result['übergriff_art'],
                        'übergriff_textbeleg': parsed_result['übergriff_textbeleg'],
                        'verweigerung_vorhanden': parsed_result['verweigerung_vorhanden'],
                        'verweigerung_massnahme': parsed_result['verweigerung_massnahme'],
                        'verweigerung_begruendung': parsed_result['verweigerung_begruendung'],
                        'hilfebedarf_typ': parsed_result['hilfebedarf_typ'],
                        'hilfebedarf_beschreibung': parsed_result['hilfebedarf_beschreibung'],
                        'medizinisches_problem_beschreibung':
                            parsed_result['medizinisches_problem_beschreibung'],
                        'medizinisches_problem_kategorie':
                            parsed_result['medizinisches_problem_kategorie'],
                        'auffaelligkeiten_vorhanden': parsed_result['auffaelligkeiten_vorhanden'],
                        'auffaelligkeiten_beschreibung': parsed_result['auffaelligkeiten_beschreibung'],
                        'anamnesis_text': text_content[:100] + "..."
                            if len(text_content) > 100 else text_content
                    }

                    analysis_results.append(base_result)

                # Expand results to include all original entries (including duplicates)
                if duplicate_count > 0:
                    # Create mapping from text content to analysis result
                    text_to_result = {}
                    for result in analysis_results:
                        text_to_result[result['anamnesis_text']] = result

                    # Create final results list with all original entries
                    final_results = []
                    for entry in text_entries:
                        text_key = entry['text_content'][:100] + "..." \
                            if len(entry['text_content']) > 100 else entry['text_content']
                        if text_key in text_to_result:
                            # Copy result and update protocol ID
                            result_copy = text_to_result[text_key].copy()
                            result_copy['einsatz_id'] = entry['protocol_id']
                            final_results.append(result_copy)

                    analysis_results = final_results
                    st.write(f"✅ Ergebnisse erweitert: {len(analysis_results)} Gesamteinträge")

                if analysis_results:
                    st.success(f"✅ Analyse für {len(analysis_results)} Protokolle abgeschlossen!")

                    # Display results in a dataframe
                    results_df = pd.DataFrame(analysis_results)
                    st.subheader("📊 Strukturierte Analyse-Ergebnisse")
                    st.dataframe(results_df)

                    # Summary statistics
                    st.subheader("📈 Zusammenfassung")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Analysierte Einsätze", len(results_df))

                    with col2:
                        # Count cases with assaults
                        assaults = results_df['übergriff_vorhanden']\
                            .str.contains('ja', case=False, na=False).sum()
                        st.metric("Übergriffe", assaults)

                    with col3:
                        # Count medical vs nursing cases
                        medical = results_df['hilfebedarf_typ'].str.contains('medizinisch', case=False, na=False).sum()
                        st.metric("Medizinische Hilfe", medical)

                    with col4:
                        # Count refusals
                        refusals = results_df['verweigerung_vorhanden'].str.contains('ja', case=False, na=False).sum()
                        st.metric("Verweigerungen", refusals)

                    # Distribution charts
                    st.subheader("📊 Verteilungsdiagramme")

                    # Check if plotly is available, if not use streamlit charts
                    try:
                        import plotly.express as px
                        import plotly.graph_objects as go
                        use_plotly = True
                    except ImportError:
                        use_plotly = False
                        st.info("💡 Für schönere Diagramme installiere plotly: `pip install plotly`")

                    # Create charts for different categories
                    tab1, tab2, tab3, tab4 = st.tabs(["🏥 Hilfebedarf", "🩺 Medizinische Probleme", "⚠️ Übergriffe", "📈 Übersicht"])

                    with tab1:
                        # Hilfebedarf distribution
                        hilfebedarf_counts = results_df['hilfebedarf_typ'].value_counts()
                        if not hilfebedarf_counts.empty:
                            if use_plotly:
                                fig = px.pie(hilfebedarf_counts,
                                           values=hilfebedarf_counts.values,
                                           names=hilfebedarf_counts.index,
                                           title="Verteilung des Hilfebedarfs",
                                           color_discrete_sequence=px.colors.qualitative.Set3)
                                fig.update_traces(textposition='inside', textinfo='percent+label')
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.bar_chart(hilfebedarf_counts)

                            # Show raw numbers
                            st.write("**Rohdaten:**")
                            st.dataframe(hilfebedarf_counts.to_frame(name="Anzahl"))

                    with tab2:
                        # Medizinische Problem-Kategorien
                        problem_counts = results_df['medizinisches_problem_kategorie'].value_counts()
                        if not problem_counts.empty:
                            if use_plotly:
                                fig = px.bar(problem_counts,
                                           x=problem_counts.index,
                                           y=problem_counts.values,
                                           title="Medizinische Problem-Kategorien",
                                           color=problem_counts.values,
                                           color_continuous_scale='Blues')
                                fig.update_layout(xaxis_title="Kategorie", yaxis_title="Anzahl")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.bar_chart(problem_counts)

                            # Show raw numbers
                            st.write("**Rohdaten:**")
                            st.dataframe(problem_counts.to_frame(name="Anzahl"))

                    with tab3:
                        # Übergriff-Arten distribution
                        uebergriff_art_counts = results_df['übergriff_art'].value_counts()
                        if not uebergriff_art_counts.empty:
                            if use_plotly:
                                fig = px.bar(uebergriff_art_counts,
                                           x=uebergriff_art_counts.index,
                                           y=uebergriff_art_counts.values,
                                           title="Arten von Übergriffen",
                                           color=uebergriff_art_counts.values,
                                           color_continuous_scale='Reds')
                                fig.update_layout(xaxis_title="Art des Übergriffs", yaxis_title="Anzahl")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.bar_chart(uebergriff_art_counts)

                            # Show raw numbers
                            st.write("**Rohdaten:**")
                            st.dataframe(uebergriff_art_counts.to_frame(name="Anzahl"))

                        # Additional: Übergriffe ja/nein
                        uebergriff_ja_nein = results_df['übergriff_vorhanden'].value_counts()
                        if not uebergriff_ja_nein.empty:
                            st.subheader("Übergriffe: Ja/Nein")
                            if use_plotly:
                                fig = px.pie(uebergriff_ja_nein,
                                           values=uebergriff_ja_nein.values,
                                           names=uebergriff_ja_nein.index,
                                           title="Vorhandensein von Übergriffen",
                                           color_discrete_sequence=['#FF6B6B', '#4ECDC4'])
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.bar_chart(uebergriff_ja_nein)

                    with tab4:
                        # Overview dashboard with multiple metrics
                        col1, col2 = st.columns(2)

                        with col1:
                            # Verweigerungen ja/nein
                            verweigerung_counts = results_df['verweigerung_vorhanden'].value_counts()
                            if not verweigerung_counts.empty:
                                st.subheader("Verweigerungen")
                                if use_plotly:
                                    fig = go.Figure(data=[go.Pie(labels=verweigerung_counts.index,
                                                               values=verweigerung_counts.values,
                                                               marker_colors=['#45B7D1', '#96CEB4'])])
                                    fig.update_layout(title="Verweigerungen: Ja/Nein")
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.bar_chart(verweigerung_counts)

                        with col2:
                            # Auffälligkeiten ja/nein
                            auffaelligkeiten_counts = results_df['auffaelligkeiten_vorhanden'].value_counts()
                            if not auffaelligkeiten_counts.empty:
                                st.subheader("Auffälligkeiten")
                                if use_plotly:
                                    fig = go.Figure(data=[go.Pie(labels=auffaelligkeiten_counts.index,
                                                               values=auffaelligkeiten_counts.values,
                                                               marker_colors=['#FECA57', '#FF9FF3'])])
                                    fig.update_layout(title="Auffälligkeiten: Ja/Nein")
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.bar_chart(auffaelligkeiten_counts)

                        # Summary table
                        st.subheader("� Zusammenfassung aller Kategorien")
                        summary_data = {
                            'Kategorie': [],
                            'Ja': [],
                            'Nein': [],
                            'Total': []
                        }

                        categories = {
                            'Übergriffe': 'übergriff_vorhanden',
                            'Verweigerungen': 'verweigerung_vorhanden',
                            'Auffälligkeiten': 'auffaelligkeiten_vorhanden'
                        }

                        for cat_name, col_name in categories.items():
                            counts = results_df[col_name].value_counts()
                            ja_count = counts.get('ja', 0)
                            nein_count = counts.get('nein', 0)
                            summary_data['Kategorie'].append(cat_name)
                            summary_data['Ja'].append(ja_count)
                            summary_data['Nein'].append(nein_count)
                            summary_data['Total'].append(ja_count + nein_count)

                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df)

                        # Overall statistics
                        st.subheader("📊 Gesamtstatistik")
                        total_cases = len(results_df)
                        uebergriffe_pct = (results_df['übergriff_vorhanden'] == 'ja').sum() / total_cases * 100
                        verweigerungen_pct = (results_df['verweigerung_vorhanden'] == 'ja').sum() / total_cases * 100
                        auffaelligkeiten_pct = (results_df['auffaelligkeiten_vorhanden'] == 'ja').sum() / total_cases * 100

                        stat_col1, stat_col2, stat_col3 = st.columns(3)
                        with stat_col1:
                            st.metric("Übergriffe", f"{uebergriffe_pct:.1f}%")
                        with stat_col2:
                            st.metric("Verweigerungen", f"{verweigerungen_pct:.1f}%")
                        with stat_col3:
                            st.metric("Auffälligkeiten", f"{auffaelligkeiten_pct:.1f}%")

                else:
                    st.warning("Keine geeigneten Anamnese-Texte in den gefilterten Daten gefunden")

    else:
        st.warning("Keine Anamnese-Daten für die aktuellen Filterkriterien gefunden")
        st.info("Stelle sicher, dass deine ETÜ-Filter (Stadt, Straße, Hausnummer, Datum) so gesetzt sind, dass übereinstimmende Protokolle gefunden werden.")
elif not merged_df.empty:
    st.info("Keine Anamnese-Daten verfügbar für LLM-Analyse")
else:
    st.warning("Keine gefilterten ETÜ-Daten verfügbar - wähle Filterkriterien aus")