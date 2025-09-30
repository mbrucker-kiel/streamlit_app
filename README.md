# Data Analysis Dashboard

## Overview

This project is a data analysis dashboard built with Streamlit that processes and visualizes medical data from medDV NIDA-Tablet. The system fetches data stored in MongoDB, processes it using custom data loaders, and displays the results on various Streamlit pages.

## Technical Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ medDV NIDA  │ -> │ medDV       │ -> │ MongoDB     │ -> │ Data Loader │
│ Tablet Data │    │ Database    │    │ Database    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                          ┌─────▼──────┐
                                                          │ Streamlit  │
                                                          │ Dashboard  │
                                                          └────────────┘
```

## Database Schema

The MongoDB database `einsatzdaten` contains the following collections (based on medDV API endpoints):

### Collections -> very different json shemata
- `etu_leitstelle`
- `nida_index`
- `protocols_details`
- `protocols_findings`
- `protocols_freetexts`
- `protocols_measures`
- `protocols_results`
- **Vitals Collections**: fairly simmilar json responses
  - `vitals_af` - Respiratory rate
  - `vitals_bd` - Blood pressure
  - `vitals_bz` - Blood sugar
  - `vitals_co` - Carbon monoxide
  - `vitals_co2` - Carbon dioxide
  - `vitals_hb` - Hemoglobin
  - `vitals_hf` - Heart rate
  - `vitals_puls` - Pulse
  - `vitals_spo2` - Oxygen saturation
  - `vitals_temp` - Temperature

## Installation

```bash
# Clone the repository
git clone https://github.com/mbrucker-kiel/streamlit_app
cd repository-name

# Install dependencies
pip install -r requirements.txt

# Configure MongoDB connection
# Edit .env with your MongoDB connection details
# Setup config.yaml with Usernames

# Run the Streamlit app
streamlit run Home.py
```

## Usage

1. Launch the application using `streamlit run Home.py`
2. Navigate through different pages using the sidebar
3. Select metrics, date ranges, and other filters as needed
4. Interact with the visualizations to explore the data
