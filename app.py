import streamlit as st
import pandas as pd
import os
import json
from PIL import Image
from water_risk_scorer import run_risk_analysis
from run_analysis import save_outputs, generate_maps

# --- App Configuration ---
st.set_page_config(
    page_title="Water Pollution Risk Assessment",
    layout="wide"
)

# --- App State & File Paths ---
OUTPUT_DIR = 'output'
CSV_PATH = os.path.join(OUTPUT_DIR, 'water_risk_scores.csv')
JSON_PATH = os.path.join(OUTPUT_DIR, 'well_metrics.json')

# --- Data Handling Functions ---

def run_full_analysis():
    """
    Runs the core analysis and generates all output files.
    This is the heavy-lifting function.
    """
    with st.spinner("Running full risk analysis... This may take a few minutes."):
        final_results_df, gis_data = run_risk_analysis()
        if final_results_df is not None:
            save_outputs(final_results_df)
            generate_maps(final_results_df, gis_data)
            st.success("Analysis complete! Output files have been generated.")
        else:
            st.error("Analysis failed. Check the terminal for errors.")
    st.experimental_rerun()


@st.cache_data
def load_results_from_disk():
    """
    Loads the analysis results from the output files.
    Returns None if files don't exist.
    """
    if os.path.exists(CSV_PATH):
        results_df = pd.read_csv(CSV_PATH)
        return results_df
    return None

# --- Main App UI ---
st.title("Orphan Well Water Pollution Risk Assessment")

st.markdown("""
This application displays pre-computed risk assessments for orphan wells in Oklahoma.
You can run a new analysis to download the latest data and re-calculate the scores using the button in the sidebar.
""")

# --- Sidebar ---
st.sidebar.title("Actions")
if st.sidebar.button("Run New Analysis"):
    run_full_analysis()

st.sidebar.title("About")
st.sidebar.info("""
This app provides a reproducible workflow for screening environmental risks associated with orphan oil and gas wells.

**Risk Tier Definitions:**
- **High:** Score >= 60
- **Moderate:** Score 30 - 59
- **Low:** Score < 30
""")
st.sidebar.title("Scoring Rubric")
st.sidebar.json(json.dumps({
    'Aquifer': '30%',
    'Surface Water': '20%',
    'Casing/Age': '20%',
    'Historical Spill': '15%',
    'Human Receptors': '15%'
}))


# --- Main Content ---
results_df = load_results_from_disk()

if results_df is not None:
    st.header("Risk Assessment Results")
    st.markdown("The table below shows the final risk scores and tiers for each well.")
    
    display_cols = ['WELL_NAME', 'COUNTY', 'final_score', 'risk_tier', 'surface_water_dist_m', 'completion_year']
    st.dataframe(results_df.set_index('API')[display_cols])

    st.header("Per-Well Dossier")
    
    # --- Well Selector ---
    well_api = st.selectbox(
        'Select a well to view details:',
        options=results_df['API'].tolist(),
        format_func=lambda api: f"{results_df.set_index('API').loc[api, 'WELL_NAME']} ({api})"
    )

    if well_api:
        well_data_row = results_df.set_index('API').loc[well_api]
        
        col1, col2 = st.columns(2)

        # --- Map Display ---
        with col1:
            st.subheader(f"Map for: {well_data_row['WELL_NAME']}")
            map_path = os.path.join(OUTPUT_DIR, f'{well_api}_map.png')
            if os.path.exists(map_path):
                image = Image.open(map_path)
                st.image(image, caption=f'Risk map for well {well_api}', use_column_width=True)
            else:
                st.warning("Map image not found. Please run the analysis.")

        # --- Metrics Display ---
        with col2:
            st.subheader(f"Metrics for: {well_data_row['WELL_NAME']}")
            if os.path.exists(JSON_PATH):
                with open(JSON_PATH) as f:
                    all_metrics = json.load(f)
                st.json(all_metrics.get(str(well_api), "Metrics not found."))
            else:
                 st.warning("Metrics JSON file not found. Please run the analysis.")
else:
    st.info("Analysis results not found. Click the 'Run New Analysis' button in the sidebar to generate them.") 