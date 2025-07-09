"""
Streamlit app for Water Pollution Risk Assessment - Refactored Version
Enhanced with modular structure, GPT-4 AI equivalents, and improved DRASTIC explanations.
"""
import streamlit as st
from water_risk_scorer import run_risk_analysis
from run_analysis import save_outputs, generate_maps
from data_models import load_results_from_disk
from ui_components import (
    render_sidebar, 
    render_main_table, 
    render_methodology_section,
    render_well_selector,
    render_well_dossier
)
from pdf_generator import generate_well_report

# --- App Configuration ---
st.set_page_config(
    page_title="Water Pollution Risk Assessment - Enhanced",
    layout="wide"
)

def run_full_analysis():
    """
    Runs the core analysis and generates all output files.
    This is the heavy-lifting function using ONLY enhanced risk modeling.
    """
    with st.spinner("Running enhanced risk analysis... This may take a few minutes."):
        final_results_df, gis_data = run_risk_analysis()
        if final_results_df is not None:
            save_outputs(final_results_df)
            # Only generate maps if they don't exist (efficiency improvement)
            generate_maps(final_results_df, gis_data, force_regenerate=False)
            st.success("Enhanced analysis complete! Output files have been generated.")
        else:
            st.error("Analysis failed. Check the terminal for errors.")
    st.experimental_rerun()

# --- Main App UI ---
st.title("CH4mber Technologies: Orphan Gas Well Plugging: Water Pollution Risk Assessment")

st.markdown("""
This application displays pre-computed risk assessments for orphan wells in Oklahoma using **enhanced risk modeling only**.
You can run a new analysis to download the latest data and re-calculate the scores using the button in the sidebar.
""")

# --- Sidebar ---
run_analysis, refresh_data = render_sidebar()

if run_analysis:
    run_full_analysis()

if refresh_data:
    st.cache_data.clear()
    st.rerun()

# --- Main Content ---
results_df = load_results_from_disk()

if results_df is not None:
    # Main results table (using enhanced modeling only)
    render_main_table(results_df)
    
    # Enhanced methodology explanation
    render_methodology_section()
    
    # Per-Well Dossier Section
    st.header("Per-Well Dossier")
    
    well_api = render_well_selector(results_df)
    
    if well_api:
        render_well_dossier(well_api, results_df)
        
        # Additional Well Analysis Components
        st.subheader("Risk Component Breakdown")
        well_data_row = results_df.set_index('API').loc[well_api]
        
        scores_col1, scores_col2 = st.columns(2)
        
        with scores_col1:
            st.markdown(f"**{well_data_row['WELL_NAME']} Component Scores:**")
            st.write(f"- **Aquifer Vulnerability (30 pts)**: {well_data_row['aquifer_score']:.1f}/30")
            st.write(f"- **Surface Water Proximity (20 pts)**: {well_data_row['surface_water_score']:.1f}/20") 
            st.write(f"- **Well Integrity (Age/Casing) (20 pts)**: {well_data_row['casing_age_score']:.1f}/20")
            st.write(f"- **Historical Spills (15 pts)**: {well_data_row['spill_score']:.1f}/15")
            st.write(f"- **Human Receptors (15 pts)**: {well_data_row['receptors_score']:.1f}/15")

        with scores_col2:
            # Display AI equivalent
            st.markdown(f"<div style="background-color:#e0f7fa; padding:10px; border-radius:5px;">"                        f"<h4 style="color:#00796b;">AI Offset Equivalent:</h4>"                        f"<p style="color:#004d40;">{well_data_row['AI_primary_comparison']}</p>"                        f"<ul>"                        f"<li>GPT-4 Training: {well_data_row['AI_gpt4_training_equivalent']:.2f}x</li>"                        f"<li>GPT-4 Queries: {well_data_row['AI_gpt4_queries_per_year']:,}</li>"                        f"<li>Claude Queries: {well_data_row['AI_claude_queries_per_year']:,}</li>"                        f"<li>H100 Hours: {well_data_row['AI_h100_cluster_hours']:,}</li>"                        f"</ul>"                        f"</div>", unsafe_allow_html=True)

            # Aquifer status
            aquifer_status = well_data_row.get('live_aquifer_check', 'Unknown')
            if 'Intersect' in str(aquifer_status):
                st.error(f"⚠️ **Aquifer Impact**: Well intersects live aquifer")
            else:
                st.success(f"✅ **Aquifer Impact**: No live aquifer intersection")

            # PDF Download Button
            st.write("&nbsp;") # Add some space
            if st.button("Generate PDF Report"):
                with st.spinner("Generating report..."):
                    pdf_path = generate_well_report(well_data_row)
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_file,
                            file_name=f"{well_api}_risk_report.pdf",
                            mime="application/octet-stream"
                        )

else:
    st.warning("⚠️ No results found. Please run the analysis to generate risk assessment data.")
    st.markdown("""
    **To get started:**
    1. Click "Run New Analysis" in the sidebar
    2. Wait for the analysis to complete (2-3 minutes)
    3. View the enhanced risk assessment results
    """)

# --- Footer ---
st.markdown("---")
st.markdown("""
**Technical Notes:**
- This app uses **enhanced risk modeling only** - no basic 0.8 constant factors
- All water safeguarded calculations use distance-weighted domestic demand and sigmoid probability modeling
- DRASTIC vulnerability factors are location-specific based on hydrogeological conditions
- AI compute equivalents updated for GPT-4 and modern language models
""")