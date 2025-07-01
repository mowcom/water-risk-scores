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

**Water Safeguarded Metric:**
Estimates the annual volume of potable water supply that would be protected by plugging each well, based on nearby domestic wells and risk score.
- Formula: Domestic Wells × 300 m³/well/yr × (Risk Score ÷ 100)
- Based on USGS average self-supplied domestic use (~77 gal/person/day)
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
    
    display_cols = ['WELL_NAME', 'COUNTY', 'final_score', 'risk_tier', 'surface_water_dist_m', 'completion_year', 'domestic_wells_1km', 'P_Leak', 'Water_Safeguarded_m3_yr', 'Water_Safeguarded_acft_yr']
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

        # --- Key Highlights and Metrics Display ---
        with col2:
            st.subheader(f"Key Highlights: {well_data_row['WELL_NAME']}")
            
            if os.path.exists(JSON_PATH):
                with open(JSON_PATH) as f:
                    all_metrics = json.load(f)
                well_metrics = all_metrics.get(str(well_api), {})
                
                if well_metrics:
                    # Key highlights with info bubbles
                    col2a, col2b = st.columns(2)
                    
                    with col2a:
                        st.metric(
                            label="Risk Score", 
                            value=f"{well_metrics.get('final_score', 'N/A')}",
                            help="Overall risk score (0-100) based on weighted factors: Aquifer (30%), Surface Water (20%), Casing/Age (20%), Historical Spill (15%), Human Receptors (15%)"
                        )
                        
                        st.metric(
                            label="Surface Water Distance", 
                            value=f"{well_metrics.get('surface_water_dist_m', 'N/A'):.0f} m",
                            help="Distance to nearest surface water body (streams, rivers, lakes). Closer wells pose higher contamination risk to surface water."
                        )
                        
                        st.metric(
                            label="Completion Year", 
                            value=f"{well_metrics.get('completion_year', 'N/A')}",
                            help="Year the well was completed. Older wells typically have less robust casing and higher failure risk."
                        )
                    
                    with col2b:
                        st.metric(
                            label="Domestic Wells (1km)", 
                            value=f"{well_metrics.get('domestic_wells_1km', 'N/A')}",
                            help="Number of domestic water wells within 1km radius. More domestic wells means higher potential impact on drinking water supply."
                        )
                        
                        st.metric(
                            label="Water Safeguarded", 
                            value=f"{well_metrics.get('Water_Safeguarded_acft_yr', 'N/A'):.2f} ac-ft/yr",
                            help="Enhanced calculation: Annual volume of potable water supply protected by plugging this well. Uses distance-weighted domestic demand, DRASTIC vulnerability, and leak probability modeling."
                        )
                        
                        st.metric(
                            label="Surface Casing Depth", 
                            value=f"{well_metrics.get('surface_casing_ft', 'N/A')} ft",
                            help="Depth of surface casing protection. Deeper casing provides better protection for shallow groundwater aquifers."
                        )
                    
                    # Aquifer status with color coding
                    aquifer_status = well_metrics.get('live_aquifer_check', 'Unknown')
                    if aquifer_status == 'Intersect':
                        st.error(f"⚠️ **Aquifer Impact**: Well intersects live aquifer", help="This well penetrates an active groundwater aquifer, increasing contamination risk to drinking water sources.")
                    else:
                        st.success(f"✅ **Aquifer Impact**: No live aquifer intersection", help="This well does not penetrate major drinking water aquifers, reducing groundwater contamination risk.")
                    
                    # Enhanced Modeling Metrics
                    st.subheader("Enhanced Risk Modeling")
                    enh_col1, enh_col2 = st.columns(2)
                    
                    with enh_col1:
                        st.metric(
                            label="DRASTIC Vulnerability", 
                            value=f"{well_metrics.get('Drastic_Class', 'N/A')} ({well_metrics.get('Drastic_Factor', 'N/A')})",
                            help="Aquifer vulnerability classification based on DRASTIC methodology. Higher values indicate greater susceptibility to contamination."
                        )
                        st.metric(
                            label="Leak Probability", 
                            value=f"{well_metrics.get('P_Leak', 'N/A'):.3f}",
                            help="Probability of leak occurrence based on risk score and aquifer vulnerability using sigmoid modeling."
                        )
                    
                    with enh_col2:
                        st.metric(
                            label="Distance-Weighted Demand", 
                            value=f"{well_metrics.get('Domestic_Demand_Wtd_m3_yr', 'N/A'):.0f} m³/yr",
                            help="Total domestic water demand within 1km, weighted by distance. Closer wells have higher weights in the calculation."
                        )
                        if well_metrics.get('Contaminant_Load_Removed_m3_yr'):
                            st.metric(
                                label="Contaminant Load Avoided", 
                                value=f"{well_metrics.get('Contaminant_Load_Removed_m3_yr', 'N/A'):.0f} m³/yr",
                                help="Annual volume of potential contamination prevented by plugging this well, based on estimated leak rates and probability."
                            )
                    
                    # Component scores breakdown
                    st.subheader("Risk Component Breakdown")
                    scores_col1, scores_col2 = st.columns(2)
                    
                    with scores_col1:
                        st.metric("Aquifer Score", f"{well_metrics.get('aquifer_score', 'N/A')}/30", help="Score based on aquifer sensitivity and well's proximity/intersection with groundwater sources")
                        st.metric("Surface Water Score", f"{well_metrics.get('surface_water_score', 'N/A')}/20", help="Score based on distance to surface water bodies - closer distances = higher scores")
                        st.metric("Casing/Age Score", f"{well_metrics.get('casing_score', 'N/A')}/20", help="Score based on surface casing depth and well age - older wells with shallow casing = higher scores")
                    
                    with scores_col2:
                        st.metric("Historical Spill Score", f"{well_metrics.get('spill_score', 'N/A')}/15", help="Score based on documented spill incidents in the area - more spills = higher scores")
                        st.metric("Human Receptors Score", f"{well_metrics.get('receptors_score', 'N/A')}/15", help="Score based on nearby domestic wells and population density - more people = higher scores")
                        
                    # Well links
                    st.subheader("Official Records")
                    if well_metrics.get('WELL_BROWSE_LINK'):
                        st.markdown(f"[🔗 Well Browse (OCC)]({well_metrics['WELL_BROWSE_LINK']})")
                    if well_metrics.get('WELL_RECORDS_DOCS'):
                        st.markdown(f"[📄 Well Records (OCC)]({well_metrics['WELL_RECORDS_DOCS']})")
                    
                    # Expandable full JSON
                    with st.expander("View Full Technical Details"):
                        st.json(well_metrics)
                else:
                    st.warning("Well metrics not found in JSON file.")
            else:
                 st.warning("Metrics JSON file not found. Please run the analysis.")
else:
    st.info("Analysis results not found. Click the 'Run New Analysis' button in the sidebar to generate them.") 