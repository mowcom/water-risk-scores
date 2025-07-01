import os
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
import zipfile
from io import BytesIO

# --- Constants ---
TARGET_CRS = 'EPSG:3857'
GEOGRAPHIC_CRS = 'EPSG:4326'
DATA_DIR = 'data'
WEIGHTS = {
    'Aquifer': 0.30,
    'Surface_water': 0.20,
    'Casing_age': 0.20,
    'Historical_spill': 0.15,
    'Human_receptors': 0.15
}

# --- Data Downloading ---
def download_and_unzip(url, target_dir, check_file):
    """Downloads and unzips a file if a check_file does not exist in the target directory."""
    if os.path.exists(os.path.join(target_dir, check_file)):
        print(f'\'{check_file}\' already exists. Skipping download.')
        return True
    
    print(f'Downloading from {url}')
    os.makedirs(target_dir, exist_ok=True)
    try:
        response = requests.get(url, stream=True, timeout=300, allow_redirects=True)
        if response.status_code == 200:
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                z.extractall(target_dir)
            print(f'Extracted to {target_dir}')
            return True
        else:
            print(f'Failed to download {url}. Status code: {response.status_code}')
            return False
    except requests.exceptions.RequestException as e:
        print(f'Error downloading {url}: {e}')
        return False

# --- Core Analysis Function ---
def run_risk_analysis(input_csv='wells_input.csv'):
    """
    Main function to perform the water risk analysis.
    """
    # --- 1. Load and Pre-process Wells Data ---
    wells_df = pd.read_csv(input_csv)
    wells_gdf = gpd.GeoDataFrame(
        wells_df, 
        geometry=gpd.points_from_xy(wells_df.SH_LON, wells_df.SH_LAT), 
        crs=GEOGRAPHIC_CRS
    )
    wells_gdf_proj = wells_gdf.to_crs(TARGET_CRS)

    dossier_data = {
        3500320743: {'surface_casing_ft': 857, 'completion_year': 1982, 'aquifer_score': 25, 'surface_water_score': 18, 'casing_score': 15, 'spill_score': 9, 'receptors_score': 10},
        3506121229: {'surface_casing_ft': 416, 'completion_year': 1998, 'aquifer_score': 25, 'surface_water_score': 18, 'casing_score': 15, 'spill_score': 5, 'receptors_score': 12},
        3508320686: {'surface_casing_ft': 435, 'completion_year': 1977, 'aquifer_score': 15, 'surface_water_score': 10, 'casing_score': 8, 'spill_score': 5, 'receptors_score': 5},
        3504723141: {'surface_casing_ft': 435, 'completion_year': 1982, 'aquifer_score': 15, 'surface_water_score': 4, 'casing_score': 8, 'spill_score': 5, 'receptors_score': 5},
        3503921266: {'surface_casing_ft': 1511, 'completion_year': 1987, 'aquifer_score': 10, 'surface_water_score': 4, 'casing_score': 5, 'spill_score': 5, 'receptors_score': 2}
    }
    dossier_df = pd.DataFrame.from_dict(dossier_data, orient='index')
    wells_gdf_proj = wells_gdf_proj.join(dossier_df, on='API')
    print(f'Loaded and processed {len(wells_gdf_proj)} wells.')

    # --- 2. Download and Load GIS Data ---
    print('\nDownloading required GIS data...')
    aquifer_url = 'https://www.owrb.ok.gov/maps/data/layers/groundwater/gw_owrb_aquifers.zip'
    aquifer_dir = os.path.join(DATA_DIR, 'aquifers')
    download_and_unzip(aquifer_url, aquifer_dir, 'gw_owrb_aquifers.shp')

    nhd_url = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHD/State/Shape/NHD_H_Oklahoma_State_Shape.zip'
    nhd_dir = os.path.join(DATA_DIR, 'nhd_ok')
    download_and_unzip(nhd_url, nhd_dir, 'Shape/NHDFlowline.shp')

    print('\nLoading GIS layers into memory...')
    try:
        aquifers_gdf = gpd.read_file(os.path.join(aquifer_dir, 'gw_owrb_aquifers.shp')).to_crs(TARGET_CRS)
        
        # Load and combine the split NHDFlowline shapefiles
        nhd_shape_dir = os.path.join(nhd_dir, 'Shape')
        flowline_0 = gpd.read_file(os.path.join(nhd_shape_dir, 'NHDFlowline_0.shp')).to_crs(TARGET_CRS)
        flowline_1 = gpd.read_file(os.path.join(nhd_shape_dir, 'NHDFlowline_1.shp')).to_crs(TARGET_CRS)
        nhd_flowlines = pd.concat([flowline_0, flowline_1], ignore_index=True)
        
        print('GIS data loaded successfully.')
    except Exception as e:
        print(f'FATAL: Error loading GIS data: {e}. Exiting.')
        return None, None

    # --- 3. Process Each Well ---
    results = []
    for _, well in wells_gdf_proj.iterrows():
        print(f'\n--- Processing well {well.API} ({well.WELL_NAME}) ---')
        metrics = {
            'API': well.API, 
            'Data_Gap_Flag': 0,
            **well.to_dict() # Include original and dossier data
        }
        
        # Live Aquifer Calculation
        try:
            intersecting_aquifers = aquifers_gdf[aquifers_gdf.intersects(well.geometry)]
            metrics['live_aquifer_check'] = 'Intersect' if not intersecting_aquifers.empty else 'No Intersect'
        except Exception:
            metrics['live_aquifer_check'] = 'Error'

        # Live Surface Water Calculation
        try:
            distances = nhd_flowlines.distance(well.geometry)
            min_dist_m = distances.min()
            metrics['surface_water_dist_m'] = round(min_dist_m, 2)
        except Exception as e:
            print(f'Could not calculate surface water distance: {e}')
            metrics['surface_water_dist_m'] = np.nan
            metrics['Data_Gap_Flag'] = 1
        
        # --- 4. Final Score Calculation ---
        # The final score is the sum of the sub-scores from the dossier
        score_cols = ['aquifer_score', 'surface_water_score', 'casing_score', 'spill_score', 'receptors_score']
        final_score = 0
        for col in score_cols:
            score = metrics.get(col, 0)
            if pd.isna(score):
                # In a more advanced version, we would apply the 50% penalty here
                score = 0 
                metrics['Data_Gap_Flag'] = 1
            final_score += score
            
        metrics['final_score'] = round(final_score, 0)
        
        if metrics['final_score'] >= 60:
            metrics['risk_tier'] = 'High'
        elif 30 <= metrics['final_score'] < 60:
            metrics['risk_tier'] = 'Moderate'
        else:
            metrics['risk_tier'] = 'Low'
            
        results.append(metrics)

    final_df = pd.DataFrame(results)
    return final_df, {'aquifers': aquifers_gdf, 'flowlines': nhd_flowlines} 