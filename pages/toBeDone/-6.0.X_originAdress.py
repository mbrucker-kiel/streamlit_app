import streamlit as st
import pandas as pd
from data_loading import data_loading

if not st.user.is_logged_in:
    st.set_page_config(page_title="KTW.sh - Login erforderlich", layout="centered")

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

st.title("🔍 Origin Address Search")

details = data_loading("Details")

# Search for origin address information
st.subheader("📍 Origin Address Filter")

# Check if origin address columns exist
origin_columns = [
    "content_originStreet",
    "content_originHousenumber",
    "content_originCity",
]
available_origin_cols = [col for col in origin_columns if col in details.columns]

if available_origin_cols:
    st.write(f"**Verfügbare Origin-Spalten:** {', '.join(available_origin_cols)}")

    # Create filters for origin address
    col1, col2, col3 = st.columns(3)

    with col1:
        if "content_originCity" in details.columns:
            cities = ["Alle"] + sorted(
                details["content_originCity"].dropna().unique().tolist()
            )
            selected_city = st.selectbox("Origin City", cities, key="origin_city")
        else:
            selected_city = "Alle"
            st.write("Origin City column not found")

    with col2:
        if "content_originStreet" in details.columns:
            streets = ["Alle"] + sorted(
                details["content_originStreet"].dropna().unique().tolist()
            )
            selected_street = st.selectbox(
                "Origin Street", streets, key="origin_street"
            )
        else:
            selected_street = "Alle"
            st.write("Origin Street column not found")

    with col3:
        if "content_originHousenumber" in details.columns:
            house_nums = ["Alle"] + sorted(
                details["content_originHousenumber"].dropna().unique().tolist()
            )
            selected_house = st.selectbox(
                "Origin House Number", house_nums, key="origin_house"
            )
        else:
            selected_house = "Alle"
            st.write("Origin House Number column not found")

    # Apply filters
    filtered_details = details.copy()

    if selected_city != "Alle":
        filtered_details = filtered_details[
            filtered_details["content_originCity"] == selected_city
        ]

    if selected_street != "Alle":
        filtered_details = filtered_details[
            filtered_details["content_originStreet"] == selected_street
        ]

    if selected_house != "Alle":
        filtered_details = filtered_details[
            filtered_details["content_originHousenumber"] == selected_house
        ]

    # Display results
    st.subheader("📊 Gefilterte Origin Address Daten")
    st.write(f"**Gefundene Datensätze:** {len(filtered_details)}")

    if not filtered_details.empty:
        # Show relevant columns including missionType
        display_columns = []
        if "content_missionType" in filtered_details.columns:
            display_columns.append("content_missionType")
        display_columns.extend(available_origin_cols)

        # Add protocolId if available
        if "protocolId" in filtered_details.columns:
            display_columns.insert(0, "protocolId")

        st.dataframe(filtered_details[display_columns])

        # Show some statistics
        if "content_missionType" in filtered_details.columns:
            st.subheader("📈 Mission Type Statistics")
            mission_stats = filtered_details["content_missionType"].value_counts()
            st.bar_chart(mission_stats)
    else:
        st.warning("Keine Datensätze mit den gewählten Origin Address Filtern gefunden")

else:
    st.warning("Keine Origin Address Spalten in den Details-Daten gefunden")
    st.write("**Verfügbare Spalten:**")
    st.write(list(details.columns))
