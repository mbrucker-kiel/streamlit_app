from .index_loaders import get_index, get_details
from .findings_loaders import get_metric_from_findings, get_neurological_signs, get_pupil_status
from .measures_loaders import get_medikamente, get_intubation, get_12lead_ecg
from .results_loaders import get_metric_from_results, get_reanimation, get_symptom_onset
from .vitals_loaders import get_vitals

# Registry
LOADERS = {
    "Index": get_index,
    "Details": get_details,
    "GCS": get_metric_from_findings,
    "Schmerzen": get_metric_from_findings,
    "Medikamente": get_medikamente,
    "NACA": get_metric_from_results,
    "af": get_vitals,
    "bd": get_vitals,
    "bz": get_vitals,
    "co2": get_vitals,
    "co": get_vitals,
    "hb": get_vitals,
    "hf": get_vitals,
    "puls": get_vitals,
    "spo2": get_vitals,
    "temp": get_vitals,
    "Intubation": get_intubation,
    "Reanimation": get_reanimation,
    "12-Kanal-EKG": get_12lead_ecg,
    "Symptombeginn": get_symptom_onset,
    "Neurologische_Auffälligkeiten": get_neurological_signs,
    "Pupillenstatus": get_pupil_status,
}