import os
import json
import matplotlib.pyplot as plt
import geopandas as gpd
from water_risk_scorer import run_risk_analysis, TARGET_CRS

# --- Configuration ---
OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Output Generation Functions ---

def save_outputs(final_df):
    """Saves the final data to CSV and JSON."""
    if final_df is None:
        print("Final DataFrame is None. Skipping output generation.")
        return
        
    # Save to CSV
    output_csv_path = os.path.join(OUTPUT_DIR, 'water_risk_scores.csv')
    csv_cols = [
        'WELL_NAME', 'COUNTY', 'final_score', 'risk_tier', 
        'surface_water_dist_m', 'surface_casing_ft', 'completion_year', 
        'domestic_wells_1km', 'Water_Safeguarded_m3_yr', 'Water_Safeguarded_acft_yr',
        'Data_Gap_Flag'
    ]
    
    # Create a DataFrame with the correct index before saving
    output_df = final_df.copy()
    if 'API' in output_df.columns:
        output_df.set_index('API', inplace=True)

    output_df[csv_cols].to_csv(output_csv_path)
    print(f'\\nScores saved to {output_csv_path}')

    # Save to JSON
    output_json_path = os.path.join(OUTPUT_DIR, 'well_metrics.json')
    
    # Drop the non-serializable geometry column before saving to JSON
    json_df = output_df.drop(columns=['geometry'], errors='ignore')
    
    json_df.to_json(output_json_path, orient='index', indent=4)
    print(f'Metrics saved to {output_json_path}')

def generate_maps(final_df, gis_layers):
    """Generates and saves a map for each well."""
    if final_df is None:
        return
        
    print("\\nGenerating maps for each well...")
    wells_gdf = gpd.GeoDataFrame(
        final_df, 
        geometry=gpd.points_from_xy(final_df.SH_LON, final_df.SH_LAT), 
        crs='EPSG:4326'
    ).to_crs(TARGET_CRS)

    for api, well_data in wells_gdf.iterrows():
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        
        buffer_extent = well_data.geometry.buffer(2500)
        ax.set_xlim(buffer_extent.bounds[0], buffer_extent.bounds[2])
        ax.set_ylim(buffer_extent.bounds[1], buffer_extent.bounds[3])

        # Plot layers
        gis_layers['aquifers'].plot(ax=ax, color='lightblue', edgecolor='blue', alpha=0.5, label='Aquifers')
        gis_layers['flowlines'].plot(ax=ax, color='blue', linewidth=1, label='Flowlines')
        
        # Plot well
        gpd.GeoSeries([well_data.geometry]).plot(ax=ax, marker='*', color='red', markersize=250, edgecolor='black', label=f'Well {well_data.API}')

        # Annotations
        title = f'Water Risk Map for Well {well_data.API} ({well_data.WELL_NAME})\\nScore: {well_data.final_score} ({well_data.risk_tier})'
        ax.set_title(title, fontdict={'fontsize': 14, 'fontweight': 'bold'})
        ax.set_xlabel('Easting (meters, EPSG:3857)')
        ax.set_ylabel('Northing (meters, EPSG:3857)')
        ax.tick_params(axis='x', labelrotation=45)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()
        
        map_filename = os.path.join(OUTPUT_DIR, f'{well_data.API}_map.png')
        plt.savefig(map_filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f'  - Saved map to {map_filename}')

# --- Main Execution Block ---
if __name__ == "__main__":
    print("Starting Water Risk Analysis...")
    
    # Run the core analysis
    final_results_df, gis_data = run_risk_analysis()
    
    # Generate all outputs
    if final_results_df is not None:
        save_outputs(final_results_df)
        generate_maps(final_results_df, gis_data)
        print("\\nAnalysis complete. Outputs are in the 'output' directory.")
    else:
        print("\\nAnalysis failed. Please check the error messages above.") 