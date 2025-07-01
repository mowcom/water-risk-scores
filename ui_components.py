"""
UI components for the Water Pollution Risk Assessment Streamlit app.
"""
import streamlit as st
import pandas as pd
import os
import json
from PIL import Image
from data_models import load_well_metrics, get_drastic_explanation, calculate_enhanced_ai_equivalents

OUTPUT_DIR = 'output'

def render_sidebar():
    """Render the sidebar with controls and information."""
    st.sidebar.title("Actions")
    
    run_analysis = st.sidebar.button("Run New Analysis")
    refresh_data = st.sidebar.button("🔄 Clear Cache & Refresh Data")
    
    st.sidebar.title("About")
    st.sidebar.info("""
    This app provides a reproducible workflow for screening environmental risks associated with orphan oil and gas wells.

    **Risk Tier Definitions:**
    - **High:** Score >= 60
    - **Moderate:** Score 30 - 59
    - **Low:** Score < 30

    **Water Safeguarded Metric:**
    Estimates the annual volume of potable water supply that would be protected by plugging each well, using enhanced distance-weighted domestic demand modeling and DRASTIC vulnerability assessment.
    """)
    
    st.sidebar.title("Scoring Weights")
    st.sidebar.json({
        'Aquifer': '30%',
        'Surface Water': '20%',
        'Casing/Age': '20%',
        'Historical Spill': '15%',
        'Human Receptors': '15%'
    })
    
    return run_analysis, refresh_data

def render_main_table(results_df):
    """Render the main results table."""
    st.header("Risk Assessment Results")
    st.markdown("The table below shows the final risk scores and tiers for each well using **enhanced risk modeling only**.")
    
    display_cols = [
        'WELL_NAME', 'COUNTY', 'final_score', 'risk_tier', 
        'surface_water_dist_m', 'completion_year', 'domestic_wells_1km', 
        'P_Leak', 'Water_Safeguarded_m3_yr', 'Water_Safeguarded_acft_yr'
    ]
    st.dataframe(results_df.set_index('API')[display_cols])

    # Water unit explanation
    st.info("💧 **What is ac-ft/yr?** An acre-foot per year (ac-ft/yr) is the volume of water covering one acre to a depth of one foot annually. One acre-foot equals ~326,000 gallons or enough to supply 6-7 rural households for a year.")

def render_methodology_section():
    """Render the detailed methodology explanation."""
    st.header("📊 Enhanced Water Safeguarded Methodology")
    
    with st.expander("🔬 **How We Calculate These Numbers** - Click to expand detailed explanation"):
        st.markdown("""
        ### Overview
        Our enhanced methodology calculates how much potable water supply would be protected by plugging each orphan well. This uses sophisticated probabilistic modeling instead of simple linear scaling.
        
        ### Step-by-Step Calculation Process
        
        #### 1. **Enhanced Risk Score Calculation** (0-100 scale)
        The code calculates a weighted risk score based on five components:
        - **Aquifer Proximity/Intersection (30%)**: Wells intersecting live aquifers get higher scores
        - **Surface Water Distance (20%)**: Closer to streams/rivers = higher risk  
        - **Casing & Age (20%)**: Older wells with shallow surface casing = higher risk
        - **Historical Spills (15%)**: Areas with documented contamination incidents
        - **Human Receptors (15%)**: Number of nearby domestic wells and population density
        
        #### 2. **DRASTIC Vulnerability Assessment**
        ```python
        drastic_factor = get_drastic_factor(well_location)  # 0.2 to 1.0
        ```
        """)
        
        st.markdown(get_drastic_explanation())
        
        st.markdown("""
        #### 3. **Distance-Weighted Domestic Demand**
        ```python
        demand = distance_weighted_demand(well_pt, domestic_wells, county_data, county)
        ```
        - **Purpose**: Calculates how much water demand exists near each well
        - **Method**: 
          - Finds all domestic wells within 1km radius
          - Gets county-specific water use per well (e.g., Haskell County: 3,000 m³/well/year)
          - Applies distance weighting: `weight = max(0, 1 - distance/1000)`
          - Sums: `Σ(county_use_per_well × distance_weight)`
        
        #### 4. **Sigmoid Leak Probability Model**
        ```python
        p_leak = sigmoid_prob(risk_score) * drastic_factor
        sigmoid_prob(score) = 1 / (1 + exp(-(score-50)/7.5))
        ```
        - **Purpose**: Converts risk score to actual probability of contamination
        - **Method**: Uses sigmoid curve calibrated so score 67 → ~0.9 base probability
        - **DRASTIC Adjustment**: Multiplies by vulnerability factor
        - **No More 0.8 Constant**: We've eliminated the old basic model's 0.8 constant factor
        
        #### 5. **Final Water Safeguarded Calculation**
        ```python
        water_safeguarded = distance_weighted_demand × leak_probability
        ```
        - **Formula**: `Demand (m³/yr) × P(leak) = Protected Water (m³/yr)`
        - **Logic**: Higher demand + higher leak risk = more water protected by plugging
        - **Unit Conversion**: `acre-feet = m³ × 0.000811`
        """)

def render_well_selector(results_df):
    """Render the well selector dropdown."""
    # Get list of APIs and set SCHNITZER as default (API: 3500320743)
    api_options = results_df['API'].tolist()
    schnitzer_api = 3500320743
    default_index = api_options.index(schnitzer_api) if schnitzer_api in api_options else 0
    
    well_api = st.selectbox(
        'Select a well to view details:',
        options=api_options,
        index=default_index,
        format_func=lambda api: f"{results_df.set_index('API').loc[api, 'WELL_NAME']} ({api})"
    )
    
    return well_api

def render_well_dossier(well_api, results_df):
    """Render the detailed well dossier section."""
    well_data_row = results_df.set_index('API').loc[well_api]
    all_metrics = load_well_metrics()
    well_metrics = all_metrics.get(str(well_api), {})
    
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
                
                water_safeguarded_acft = well_metrics.get('Water_Safeguarded_acft_yr', 0)
                st.metric(
                    label="Water Safeguarded", 
                    value=f"{water_safeguarded_acft:.3f} ac-ft/yr",
                    help="Enhanced calculation: Annual volume of potable water supply protected by plugging this well. Uses distance-weighted domestic demand, DRASTIC vulnerability, and sigmoid leak probability modeling."
                )
                
                st.metric(
                    label="Surface Casing Depth", 
                    value=f"{well_metrics.get('surface_casing_ft', 'N/A')} ft",
                    help="Depth of surface casing protection. Deeper casing provides better protection for shallow groundwater aquifers."
                )
            
            render_enhanced_modeling_section(well_metrics)
            render_ai_equivalents_section(well_metrics)

def render_enhanced_modeling_section(well_metrics):
    """Render the enhanced risk modeling metrics."""
    st.subheader("Enhanced Risk Modeling")
    enh_col1, enh_col2 = st.columns(2)
    
    with enh_col1:
        drastic_class = well_metrics.get('Drastic_Class', 'N/A')
        drastic_factor = well_metrics.get('Drastic_Factor', 'N/A')
        st.metric(
            label="DRASTIC Vulnerability", 
            value=f"{drastic_class} ({drastic_factor})",
            help=f"Aquifer vulnerability classification: {drastic_class} vulnerability means aquifer is {'more' if drastic_factor > 0.6 else 'moderately' if drastic_factor > 0.3 else 'less'} susceptible to surface contamination. Factor {drastic_factor} multiplies leak probability (1.0=most vulnerable, 0.2=least vulnerable)."
        )
        st.metric(
            label="Leak Probability", 
            value=f"{well_metrics.get('P_Leak', 'N/A'):.3f}",
            help="Probability of leak occurrence based on risk score and aquifer vulnerability using sigmoid modeling (no more 0.8 constant factor)."
        )
    
    with enh_col2:
        st.metric(
            label="Distance-Weighted Demand", 
            value=f"{well_metrics.get('Domestic_Demand_Wtd_m3_yr', 'N/A'):.0f} m³/yr",
            help="Total domestic water demand within 1km, weighted by distance. Closer wells have higher weights in the calculation."
        )
        contam_load = well_metrics.get('Contaminant_Load_Removed_m3_yr', 0)
        if contam_load > 0:
            st.metric(
                label="Contaminant Load Avoided", 
                value=f"{contam_load:.0f} m³/yr",
                help="Annual volume of potential contamination prevented by plugging this well, based on estimated leak rates and probability."
            )

def render_ai_equivalents_section(well_metrics):
    """Render the AI compute equivalents section with GPT-4 focus."""
    st.subheader("🤖 GPT-4 & AI Compute Water Equivalents")
    st.caption("Putting the water safeguarded into perspective using modern AI model training and inference water consumption")
    
    water_m3 = well_metrics.get('Water_Safeguarded_m3_yr', 0)
    
    if water_m3 > 0:
        # Calculate updated AI equivalents with GPT-4 focus
        ai_equivalents = calculate_enhanced_ai_equivalents(water_m3)
        
        ai_col1, ai_col2 = st.columns(2)
        
        with ai_col1:
            # Use the stored metrics from the JSON file
            gpt4_equiv = well_metrics.get('AI_GPT4_Training_Equivalent', 0)
            if gpt4_equiv >= 0.1:
                st.metric(
                    label="GPT-4 Training Equivalent", 
                    value=f"{gpt4_equiv:.1f}×",
                    help="Number of GPT-4 scale model trainings this amount of water could support (GPT-4 training ≈ 2.5M liters)"
                )
            
            gpt4_queries = well_metrics.get('AI_GPT4_Queries_Per_Year', 0)
            if gpt4_queries >= 1000:
                if gpt4_queries >= 1000000:
                    st.metric(
                        label="GPT-4 Queries Per Year", 
                        value=f"{gpt4_queries/1000000:.1f}M",
                        help="GPT-4 queries this water volume could support per year (≈1.2L per complex query)"
                    )
                else:
                    st.metric(
                        label="GPT-4 Queries Per Year", 
                        value=f"{gpt4_queries:,}",
                        help="GPT-4 queries this water volume could support per year (≈1.2L per complex query)"
                    )
        
        with ai_col2:
            claude_queries = well_metrics.get('AI_Claude_Queries_Per_Year', 0)
            if claude_queries >= 1000:
                if claude_queries >= 1000000:
                    st.metric(
                        label="Claude-3 Queries Per Year", 
                        value=f"{claude_queries/1000000:.1f}M",
                        help="Claude-3 queries this water volume could support per year (similar usage to GPT-4)"
                    )
                else:
                    st.metric(
                        label="Claude-3 Queries Per Year", 
                        value=f"{claude_queries:,}",
                        help="Claude-3 queries this water volume could support per year (similar usage to GPT-4)"
                    )
            
            h100_hours = ai_equivalents['h100_cluster_hours']
            if h100_hours >= 8760:  # 1 year
                years = h100_hours / 8760
                st.metric(
                    label="H100 GPU Cluster Cooling", 
                    value=f"{years:.1f} years",
                    help="Years of H100 GPU cluster cooling this water volume could support (≈50L/hour for cooling)"
                )
            elif h100_hours >= 1:
                st.metric(
                    label="H100 GPU Cluster Hours", 
                    value=f"{h100_hours:,}",
                    help="Hours of H100 GPU cluster cooling this water volume could support (≈50L/hour for cooling)"
                )
        
        # Primary comparison as highlighted text
        primary_comparison = well_metrics.get('AI_Primary_Comparison', '')
        if primary_comparison:
            st.info(f"**Bottom Line**: {primary_comparison}")
        
        # Project lifetime calculation (assume 20-year well life)
        lifetime_water = water_m3 * 20
        lifetime_gpt4 = lifetime_water / 2500  # Updated for GPT-4
        if lifetime_gpt4 >= 1:
            st.success(f"🚀 **Project Lifetime Impact**: Over 20 years, plugging this well safeguards {lifetime_water:,.0f} m³ of water — equivalent to **{lifetime_gpt4:.0f}× GPT-4 scale model trainings**!")
        else:
            lifetime_gpt4_queries = int(lifetime_water / 0.0012)
            st.success(f"🚀 **Project Lifetime Impact**: Over 20 years, plugging this well safeguards {lifetime_water:,.0f} m³ of water — equivalent to **{lifetime_gpt4_queries:,} GPT-4 queries**!")
    else:
        st.info("No water safeguarded for this well (no nearby domestic wells).") 