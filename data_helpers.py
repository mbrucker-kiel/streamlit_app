import pandas as pd
from bson import ObjectId
import datetime

def convert_objectid_to_str(data_list):
    """Convert ObjectId to string in a list of MongoDB documents"""
    for item in data_list:
        if '_id' in item and isinstance(item['_id'], ObjectId):
            item['_id'] = str(item['_id'])
    return data_list

def ja_nein_to_bool(val):
    """Convert 'ja'/'nein' or 'Ja'/'Nein' values to boolean"""
    if isinstance(val, str):
        return True if val.lower() in ["ja", "yes"] else False if val.lower() in ["nein", "no"] else None
    return val

def process_boolean_fields(df):
    """Process boolean fields that may be stored as 'ja'/'nein'"""
    bool_fields = ['flashingLights', 'transportFlashingLights', 'nachforderungNA']
    for field in bool_fields:
        if field in df.columns:
            df[field] = df[field].apply(ja_nein_to_bool)
    return df

def combine_date_time(date_val, time_val):
    """Combine date and time values into a datetime object"""
    if pd.notna(date_val) and pd.notna(time_val):
        try:
            date_str = str(date_val).strip()
            time_str = str(time_val).strip()
            if not date_str or not time_str:
                return None
            datetime_str = f"{date_str} {time_str}"
            return pd.to_datetime(datetime_str, errors='coerce')
        except Exception:
            return None
    return None

def combine_date_time_fields(df):
    """Combine date and time fields into datetime fields"""
    if df.empty:
        return df

    status_fields = [
        ("StatusAlarm", "content_dateStatusAlarm", "content_timeStatusAlarm"),
        ("Status3", "content_dateStatus3", "content_timeStatus3"),
        ("Status4", "content_dateStatus4", "content_timeStatus4"),
        ("Status4b", "content_dateStatus4b", "content_timeStatus4b"),
        ("Status7", "content_dateStatus7", "content_timeStatus7"),
        ("Status8", "content_dateStatus8", "content_timeStatus8"),
        ("Status8b", "content_dateStatus8b", "content_timeStatus8b"),
        ("Status1", "content_dateStatus1", "content_timeStatus1"),
        ("Status2", "content_dateStatus2", "content_timeStatus2"),
        ("StatusEnd", "content_dateStatusEnd", "content_timeStatusEnd"),
    ]

    for target_field, date_field, time_field in status_fields:
        if date_field in df.columns and time_field in df.columns:
            df[target_field] = df.apply(
                lambda row: combine_date_time(row[date_field], row[time_field]), axis=1
            )
    return df

def check_requirements(anamnesis_text):
    """
    Analyze anamnesis text to check for medical care requirements during transport.
    
    Args:
        anamnesis_text (str): The anamnesis text to analyze
        
    Returns:
        dict: Dictionary with analysis results for medical_care, ktw_equipment, and infectious_disease
    """
    if pd.isna(anamnesis_text):
        return {
            'medical_care': None,
            'ktw_equipment': None, 
            'infectious_disease': None
        }
    
    text = str(anamnesis_text)
    
    # Medical care checking
    medical_care = None
    if "Während des Transport wurde eine medizinische Betreuung notwendig. Es wurden folgende Maßnahmen ergriffen:" in text:
        medical_care = "needed"
    elif "Während des gesamten Transports ist keine medizinische Betreuung notwendig geworden." in text:
        medical_care = "not_needed"
    
    # KTW equipment checking
    ktw_equipment = None
    if "Während der Fahrt war der Patient auf die folgende besondere Ausstattung eines KTW angewiesen:" in text:
        ktw_equipment = "needed"
    elif "Während der Fahrt war der Patient zu keiner Zeit auf die besondere Ausstattung eines KTW angewiesen" in text:
        ktw_equipment = "not_needed"
    
    # Infectious disease checking
    infectious_disease = None
    if "Bei dem Patient liegt eine schwere ansteckende Infektionserkrankung vor, sodass lokale Schutzmaßnahmen während des Transportes nicht ausreichen" in text:
        infectious_disease = "needed"
    elif "Bei dem Patienten ist keine schwere ansteckende Infektionserkrankung festgestellt worden oder als wahrscheinlich anzunehmen." in text:
        infectious_disease = "not_needed"
    elif "Bei dem Patienten liegt eine Infektionserkrankung vor, deren Verbreitung jedoch durch lokal Schutzmaßnahmen ausreichend vermieden werden kann" in text:
        infectious_disease = "local_protection"
    
    return {
        'medical_care': medical_care,
        'ktw_equipment': ktw_equipment,
        'infectious_disease': infectious_disease
    }

def check_requirements_enhanced(anamnesis_text):
    """
    Enhanced analysis of anamnesis text for comprehensive transport requirement assessment.
    
    Args:
        anamnesis_text (str): The anamnesis text to analyze
        
    Returns:
        dict: Dictionary with comprehensive analysis results
    """
    if pd.isna(anamnesis_text):
        return {
            'medical_care': None,
            'ktw_equipment': None,
            'infectious_disease': None,
            'crew_assessment': None,
            'krankenfahrt_mentioned': False
        }
    
    text = str(anamnesis_text).lower()
    
    # Medical care checking (enhanced patterns) - prioritize specific over general
    medical_care = None
    # First check for logistical/social/pedagogical care (most specific)
    if any(phrase in text for phrase in [
        "logistische betreuung",
        "soziale betreuung", 
        "pädagogische betreuung",
        "psychologische betreuung",
        "begleitperson notwendig",
        "keine medizinische betreuung notwendig geworden, sondern lediglich eine logistische"
    ]):
        medical_care = "logistische_soziale_paedagogische"
    # Then check for medical care needed
    elif any(phrase in text for phrase in [
        "medizinische betreuung notwendig",
        "medizinische versorgung erforderlich",
        "ärztliche betreuung notwendig",
        "medizinische intervention",
        "therapeutische maßnahmen",
        "während des transport wurde eine medizinische betreuung notwendig"
    ]):
        medical_care = "indiziert"
    elif any(phrase in text for phrase in [
        "logistische betreuung",
        "soziale betreuung", 
        "pädagogische betreuung",
        "psychologische betreuung",
        "begleitperson notwendig",
        "keine medizinische betreuung notwendig geworden, sondern lediglich eine logistische"
    ]):
        medical_care = "logistische_soziale_paedagogische"
    # Finally check for no medical care needed
    elif any(phrase in text for phrase in [
        "keine medizinische betreuung notwendig",
        "keine medizinische versorgung erforderlich",
        "keine ärztliche betreuung notwendig",
        "keine medizinische intervention",
        "keine therapeutischen maßnahmen",
        "während des gesamten transports ist keine medizinische betreuung notwendig geworden"
    ]):
        medical_care = "nicht_indiziert"
    
    # KTW equipment checking (enhanced patterns) - prioritize specific over general
    ktw_equipment = None
    # First check for no special equipment needed (most common case)
    if any(phrase in text for phrase in [
        "keine besondere ausstattung ktw",
        "keine spezielle ausstattung ktw",
        "während der fahrt war der patient zu keiner zeit auf die besondere ausstattung eines ktw angewiesen"
    ]):
        ktw_equipment = "nicht_indiziert"
    # Then check for Krankenfahrt sufficient
    elif any(phrase in text for phrase in [
        "krankenfahrt ausreichend",
        "beförderung als krankenfahrt ausreichend",
        "keine besondere ausstattung eines ktw erforderlich, sodass die beforderung als krankenfahrt ausreichend",
        "lediglich liegend transportiert werden",
        "lediglich im rollstuhl sitzend transportiert werden",
        "der patient muss lediglich liegend / im rollstuhl sitzend transportiert werden"
    ]):
        ktw_equipment = "krankenfahrt"
    # Finally check for special equipment needed
    elif any(phrase in text for phrase in [
        "besondere ausstattung ktw",
        "spezielle ausstattung ktw",
        "rtw ausstattung notwendig",
        "intensivtransport",
        "beatmung notwendig",
        "monitorüberwachung",
        "defibrillator notwendig",
        "während der fahrt war der patient auf die folgende besondere ausstattung eines ktw angewiesen"
    ]):
        ktw_equipment = "indiziert"
    
    # Infectious disease checking (enhanced patterns) - prioritize specific over general
    infectious_disease = None
    # First check for no infectious disease (most common case)
    if any(phrase in text for phrase in [
        "keine ansteckende infektionserkrankung",
        "nicht infektiös",
        "keine isolierung notwendig",
        "bei dem patienten ist keine schwere ansteckende infektionserkrankung festgestellt worden oder als wahrscheinlich anzunehmen"
    ]):
        infectious_disease = "nicht_indiziert"
    # Then check for local protection sufficient
    elif any(phrase in text for phrase in [
        "lokale schutzmaßnahmen ausreichend",
        "standard hygiene ausreichend",
        "normale schutzmaßnahmen",
        "bei dem patienten liegt eine infektionserkrankung vor, deren verbreitung jedoch durch lokal schutzmaßnahmen ausreichend vermieden werden kann"
    ]):
        infectious_disease = "lokaler_schutz"
    # Finally check for severe infectious disease
    elif any(phrase in text for phrase in [
        "schwere ansteckende infektionserkrankung",
        "hochinfektiös",
        "isolierung notwendig",
        "quarantäne",
        "infektionsschutz",
        "bei dem patient liegt eine schwere ansteckende infektionserkrankung vor"
    ]):
        infectious_disease = "indiziert"
    
    # Crew assessment (enhanced patterns) - prioritize specific over general
    crew_assessment = None
    # First check for Krankenfahrt sufficient
    if any(phrase in text for phrase in [
        "laut vorliegendem patientenzustand ist eine beförderung des patienten indiziert, jedoch nicht als krankentransport sondern als krankenfahrt",
    ]):
        crew_assessment = "krankenfahrt_ausreichend"
    # Then check for RTW/medical crew needed
    elif any(phrase in text for phrase in [
        "ärztliche begleitung notwendig",
        "die vorliegenden begründungen der transportverordnung bzw. der übergabe entsprechen den einschätzungen des teamleiters"
    ]):
        crew_assessment = "indiziert"
    # Finally check for no RTW needed
    elif any(phrase in text for phrase in [
        "auch bei genauer anamnese ist keine indikationen für einen krankentransport oder eine krankenfahrt erkennbar"
    ]):
        crew_assessment = "nicht_indiziert"
    
    # Krankenfahrt mentioned
    krankenfahrt_mentioned = any(phrase in text for phrase in [
        "krankenfahrt",
        "krankenwagen",
        "ktw",
        "krankentransport"
    ])
    
    return {
        'medical_care': medical_care,
        'ktw_equipment': ktw_equipment,
        'infectious_disease': infectious_disease,
        'crew_assessment': crew_assessment,
        'krankenfahrt_mentioned': krankenfahrt_mentioned
    }

def analyze_freetext_requirements(df_freetext, protocol_ids=None):
    """
    Analyze freetext data for medical requirements using enhanced analysis.
    
    Args:
        df_freetext (pd.DataFrame): DataFrame containing freetext data
        protocol_ids (list, optional): List of protocol IDs to filter by
        
    Returns:
        pd.Series: Series with analysis results for each row
    """
    if df_freetext.empty:
        return pd.Series(dtype=object)
    
    # Filter by protocol IDs if provided
    if protocol_ids is not None:
        df_freetext = df_freetext[df_freetext['protocolId'].isin(protocol_ids)]
    
    # Check what text column is available (prioritize 'content' as shown in data structure)
    text_column = None
    if 'content' in df_freetext.columns:
        text_column = 'content'
    elif 'text' in df_freetext.columns:
        text_column = 'text'
    else:
        # If neither 'content' nor 'text' exists, return empty series
        return pd.Series(dtype=object)
    
    # Apply enhanced analysis function to the text column
    analysis_results = df_freetext[text_column].apply(check_requirements_enhanced)
    
    return analysis_results