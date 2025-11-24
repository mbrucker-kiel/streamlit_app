import streamlit as st
import pandas as pd
from data_loading import data_loading

st.set_page_config(page_title="BKN NIDA ETU", layout="wide")
st.title("🔬 BKN ↔ ETÜ ↔ NIDA Diagnosis Mapping")

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

# Load BKN data
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

if df_bkn is None or df_bkn.empty:
    st.error("Could not load BKN data")
    st.stop()

# Load Details data
df_details = data_loading("Details", limit=50000)
if df_details.empty:
    st.error("Could not load Details data")
    st.stop()

# Load ETÜ data
df_etu = None
for encoding in ["utf-8", "latin1", "iso-8859-1", "cp1252"]:
    for delimiter in [",", ";", "\t", "|"]:
        try:
            df_etu = pd.read_csv(
                "data/etu2024.csv",
                encoding=encoding,
                sep=delimiter,
                on_bad_lines="skip",
            )
            break
        except (UnicodeDecodeError, FileNotFoundError, pd.errors.ParserError):
            continue
    if df_etu is not None:
        break

if df_etu is None or df_etu.empty:
    st.error("Could not load ETÜ data")
    st.stop()

# Load Index data
df_index = data_loading("Index", limit=50000)
if df_index.empty:
    st.error("Could not load Index data")
    st.stop()

# Load BKN Diagnosen from Excel
try:
    df_bkn_diagnosis = pd.read_excel("data/BKN Diagnosen.xlsx", engine="openpyxl")
except FileNotFoundError:
    st.warning("BKN Diagnosen.xlsx not found")
    df_bkn_diagnosis = pd.DataFrame()

# ============================================
# MERGE LOGIC
# ============================================

# Step 1: Merge BKN with ETÜ on OBER_EINSATZ_NR
merged_df = df_bkn.merge(
    df_etu, on="OBER_EINSATZ_NR", how="left", suffixes=("_bkn", "_etu")
)

# Step 2: Merge with Index
index_cols = ["missionNumber", "leadingDiagnosis"]
index_for_merge = df_index[
    [col for col in index_cols if col in df_index.columns]
].copy()

final_df = merged_df.merge(
    index_for_merge, left_on="EINSATZ_NR", right_on="missionNumber", how="left"
)

# Step 3: Add Verdachtsdiagnose
if (
    not df_bkn_diagnosis.empty
    and "Verdachtsdiagnose" in df_bkn_diagnosis.columns
    and "diagnosis_id" in final_df.columns
):

    # Find ID column
    id_col = None
    for col in df_bkn_diagnosis.columns:
        if "id" in col.lower() or "diagnose" in col.lower():
            if "verdacht" not in col.lower():
                id_col = col
                break

    if id_col:
        # Create mapping
        diagnosis_map = dict(
            zip(
                df_bkn_diagnosis[id_col].astype(str),
                df_bkn_diagnosis["Verdachtsdiagnose"],
            )
        )

        # Apply mapping
        final_df["Verdachtsdiagnose"] = (
            final_df["diagnosis_id"].astype(str).map(diagnosis_map)
        )

# ============================================
# DISPLAY FINAL RESULT
# ============================================

st.header("✅ Merged Diagnosis Data")

result_cols = [
    col
    for col in ["diagnosis_id", "Verdachtsdiagnose", "CEDUS_CODE", "leadingDiagnosis"]
    if col in final_df.columns
]

if result_cols:
    final_result = final_df[result_cols].copy()
    final_result = final_result[
        final_result[result_cols].notna().any(axis=1)
    ].reset_index(drop=True)

    st.write(f"**Total Records: {len(final_result)}**")
    st.dataframe(final_result, use_container_width=True, height=600)

    # Download button
    csv = final_result.to_csv(index=False)
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="diagnosis_mapping.csv",
        mime="text/csv",
    )
else:
    st.error("No diagnosis columns found")

# display the bkn diagnosen df
