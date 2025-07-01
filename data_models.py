"""
Data models and utilities for the Water Pollution Risk Assessment app.
"""
import os
import json
import pandas as pd
import streamlit as st

# File paths
OUTPUT_DIR = 'output'
CSV_PATH = os.path.join(OUTPUT_DIR, 'water_risk_scores.csv')
JSON_PATH = os.path.join(OUTPUT_DIR, 'well_metrics.json')

@st.cache_data
def load_results_from_disk():
    """
    Loads the analysis results from the output files with data validation.
    Returns None if files don't exist.
    """
    if os.path.exists(CSV_PATH):
        results_df = pd.read_csv(CSV_PATH)
        
        # Ensure API column is properly formatted as int64 for consistent indexing
        results_df['API'] = results_df['API'].astype('int64')
        
        return results_df
    return None

def load_well_metrics():
    """Load detailed well metrics from JSON file."""
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            return json.load(f)
    return {}

def get_drastic_explanation():
    """Return detailed explanation of DRASTIC vulnerability scoring."""
    return """
    ### DRASTIC Vulnerability Factor Explained
    
    DRASTIC is a standardized system for evaluating groundwater pollution potential using hydrogeological factors:
    
    **D** - Depth to water table  
    **R** - Net recharge  
    **A** - Aquifer media  
    **S** - Soil media  
    **T** - Topography  
    **I** - Impact of vadose zone  
    **C** - Hydraulic conductivity  
    
    #### Vulnerability Classes & Factors:
    - **Very High (1.0)**: Sand/gravel aquifers, shallow water table, high permeability
    - **High (0.8)**: Moderate protection, some vulnerability to surface contamination  
    - **Moderate (0.6)**: Mixed geology, moderate protection
    - **Low (0.4)**: Clay layers, deeper water table, good natural protection
    - **Very Low (0.2)**: Dense clay/shale, deep water table, excellent protection
    
         #### Why Different Wells Have Different DRASTIC Scores:
     - **SCHNITZER (1.0 - Very High)**: Located in area with highly permeable geology, minimal natural protection
     - **BLAKE (1.0 - Very High)**: Also in highly permeable area with limited natural barriers
     - **KING-OH (0.2 - Very Low)**: Located in area with thick clay/shale layers providing excellent protection
     - **Geographic Variation**: Oklahoma has diverse geology - some areas have protective clay layers, others have permeable sand/gravel
    
    #### How It Affects Calculations:
    The DRASTIC factor multiplies the base leak probability:
    ```
    Final P_Leak = sigmoid(risk_score) × DRASTIC_factor
    ```
    This means a well with identical risk scores will have different leak probabilities based on local geological protection.
    """

def calculate_enhanced_ai_equivalents(water_m3_per_year):
    """
    Calculate GPT-4 and other advanced AI model water equivalents.
    Updated with more recent and sophisticated AI model comparisons.
    """
    if water_m3_per_year <= 0:
        return {
            'gpt4_training_equivalent': 0,
            'gpt4_queries_per_year': 0,
            'claude_queries_per_year': 0,
            'h100_cluster_hours': 0,
            'description': 'No water safeguarded',
            'primary_comparison': 'No water safeguarded (no nearby domestic wells)'
        }
    
    # Updated estimates for modern AI models (2024)
    # GPT-4 training estimated at ~2.5M liters (2500 m³) - larger than GPT-3
    # GPT-4 inference: ~1.2 liters per complex query (~0.0012 m³)
    # Claude-3 similar usage patterns
    
    equivalents = {
        'gpt4_training_equivalent': round(water_m3_per_year / 2500, 2),
        'gpt4_queries_per_year': int(water_m3_per_year / 0.0012),
        'claude_queries_per_year': int(water_m3_per_year / 0.0012),  # Similar to GPT-4
        'h100_cluster_hours': int(water_m3_per_year / 0.05),
        'description': f'{water_m3_per_year:.0f} m³/year water safeguarded'
    }
    
    # Create more interesting human-readable description
    if equivalents['gpt4_training_equivalent'] >= 1:
        equivalents['primary_comparison'] = f"≈ {equivalents['gpt4_training_equivalent']:.1f}× GPT-4 training water use"
    elif equivalents['gpt4_queries_per_year'] >= 1000000:
        million_queries = equivalents['gpt4_queries_per_year'] / 1000000
        equivalents['primary_comparison'] = f"≈ {million_queries:.1f}M GPT-4 queries/year"
    elif equivalents['h100_cluster_hours'] >= 8760:  # 1 year
        years = equivalents['h100_cluster_hours'] / 8760
        equivalents['primary_comparison'] = f"≈ {years:.1f} years of H100 cluster cooling"
    else:
        equivalents['primary_comparison'] = f"≈ {equivalents['h100_cluster_hours']:,} hours of H100 cluster cooling"
    
    return equivalents 