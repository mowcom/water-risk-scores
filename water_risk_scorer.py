import os
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
import zipfile
from io import BytesIO
from shapely.geometry import Point
import warnings
warnings.filterwarnings('ignore')

# --- Constants ---
TARGET_CRS = 'EPSG:3857'
GEOGRAPHIC_CRS = 'EPSG:4326'
DATA_DIR = 'data'

# --- Water Safeguarded Constants ---
DOMESTIC_USE_M3 = 300
ACRE_FT_PER_M3 = 1/1233.5

# --- Enhanced Water Safeguarded Parameters ---
LEAK_RATE_RANGE_M3_DAY = (0.5, 5.9)

# --- DRASTIC Vulnerability Mappings ---
DRASTIC_MAPPING = {
    'Very High': 1.0, 'High': 0.8, 'Moderate': 0.6, 'Low': 0.4, 'Very Low': 0.2
}

# --- Data Downloading ---
def download_and_unzip(url, target_dir, check_file):
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

# --- V2 RISK COMPONENT CALCULATION ---
def calculate_aquifer_score(well, aquifers_gdf):
    metrics = {}
    try:
        intersecting_aquifers = aquifers_gdf[aquifers_gdf.intersects(well.geometry)]
        intersection_score = 20 if not intersecting_aquifers.empty else 0
        metrics['live_aquifer_check'] = 'Intersect' if intersection_score > 0 else 'No Intersect'
    except Exception:
        intersection_score = 0
        metrics['live_aquifer_check'] = 'Error'
    try:
        distance_to_aquifer = aquifers_gdf.distance(well.geometry).min()
        vulnerability_score = 10 * np.exp(-distance_to_aquifer / 5000)
    except Exception:
        vulnerability_score = 0
    metrics['aquifer_score'] = intersection_score + vulnerability_score
    return metrics

def calculate_surface_water_score(well, nhd_flowlines):
    metrics = {}
    try:
        min_dist_m = nhd_flowlines.distance(well.geometry).min()
        metrics['surface_water_dist_m'] = round(min_dist_m, 2)
        score = 20 * np.exp(-(min_dist_m / 500))
        metrics['surface_water_score'] = score
    except Exception as e:
        print(f'Could not calculate surface water distance for well {well.API}: {e}')
        metrics['surface_water_dist_m'] = np.nan
        metrics['surface_water_score'] = 0
    return metrics

def calculate_casing_age_score(well):
    age = 2025 - well.get('completion_year', 2000)
    age_score = min(10, (age / 50) * 10)
    casing_ft = well.get('surface_casing_ft', 500)
    casing_score = 10 * (1 - (min(casing_ft, 1500) / 1500))
    return {'casing_age_score': age_score + casing_score}

def calculate_spill_score(well):
    return {'spill_score': 5.0}

def calculate_receptors_score(well):
    domestic_wells = well.get('domestic_wells_1km', 0)
    return {'receptors_score': min(15, domestic_wells * 3)}

def calculate_risk_components(well, gis_layers):
    all_metrics = {}
    all_metrics.update(calculate_aquifer_score(well, gis_layers['aquifers']))
    all_metrics.update(calculate_surface_water_score(well, gis_layers['flowlines']))
    all_metrics.update(calculate_casing_age_score(well))
    all_metrics.update(calculate_spill_score(well))
    all_metrics.update(calculate_receptors_score(well))
    return all_metrics

# --- FEATURE ENGINEERING & UTILITIES ---
def get_drastic_factor(well_pt, aquifers_gdf):
    try:
        distance = aquifers_gdf.distance(well_pt).min()
        if distance == 0: return 1.0
        factor = 0.2 + 0.8 * np.exp(-distance / 2000)
        return max(0.2, min(1.0, factor))
    except Exception:
        return 0.6

def get_county_water_use_data():
    mock_data = {
        'ALFALFA': {'self_supplied_domestic_m3': 2500000, 'domestic_wells': 850},
        'HASKELL': {'self_supplied_domestic_m3': 1800000, 'domestic_wells': 600},
        'LOGAN': {'self_supplied_domestic_m3': 3200000, 'domestic_wells': 1100},
        'GARFIELD': {'self_supplied_domestic_m3': 4500000, 'domestic_wells': 1500},
        'CUSTER': {'self_supplied_domestic_m3': 2800000, 'domestic_wells': 950}
    }
    return pd.DataFrame.from_dict(mock_data, orient='index').reset_index()

def distance_weighted_demand(well_pt, domestic_wells_gdf, county_use_df, county_name):
    if domestic_wells_gdf is None or len(domestic_wells_gdf) == 0: return 0.0
    county_data = county_use_df[county_use_df['index'] == county_name]
    annual_use_per_well = (county_data.iloc[0]['self_supplied_domestic_m3'] / county_data.iloc[0]['domestic_wells']) if not county_data.empty else DOMESTIC_USE_M3
    distances = domestic_wells_gdf.distance(well_pt)
    weights = np.maximum(0, 1 - distances/1000)
    return np.sum(annual_use_per_well * weights)

def sigmoid_prob(score):
    return 1 / (1 + np.exp(-(score - 50)/7.5))

def water_to_ai_compute_equivalent(water_m3_per_year):
    if water_m3_per_year <= 0:
        return {
            'primary_comparison': 'No water safeguarded',
            'gpt4_training_equivalent': 0,
            'gpt4_queries_per_year': 0,
            'claude_queries_per_year': 0,
            'h100_cluster_hours': 0,
            'gpt4_training_equivalent_str': '0x GPT-4 training',
            'gpt4_queries_per_year_str': '0 GPT-4 queries',
            'claude_queries_per_year_str': '0 Claude queries',
            'h100_cluster_hours_str': '0 hours H100 cooling'
        }
    equivalents = {
        'gpt4_training_equivalent': round(water_m3_per_year / 2500, 2),
        'gpt4_queries_per_year': int(water_m3_per_year / 0.0012),
        'claude_queries_per_year': int(water_m3_per_year / 0.0012),
        'h100_cluster_hours': int(water_m3_per_year / 0.05)
    }

    # Generate formatted strings for each metric
    equivalents['gpt4_training_equivalent_str'] = f"{equivalents['gpt4_training_equivalent']:.2f}x GPT-4 training"
    equivalents['gpt4_queries_per_year_str'] = f"{equivalents['gpt4_queries_per_year']:,} GPT-4 queries"
    equivalents['claude_queries_per_year_str'] = f"{equivalents['claude_queries_per_year']:,} Claude queries"
    equivalents['h100_cluster_hours_str'] = f"{equivalents['h100_cluster_hours']:,} hours H100 cooling"

    if equivalents['gpt4_training_equivalent'] >= 1:
        equivalents['primary_comparison'] = f"≈ {equivalents['gpt4_training_equivalent']:.1f}× GPT-4 training water use"
    elif equivalents['gpt4_queries_per_year'] >= 1000000:
        equivalents['primary_comparison'] = f"≈ {equivalents['gpt4_queries_per_year'] / 1000000:.1f}M GPT-4 queries/year"
    elif equivalents['h100_cluster_hours'] >= 8760: # 1 year
        equivalents['primary_comparison'] = f"≈ {equivalents['h100_cluster_hours'] / 8760:.1f} years of H100 cluster cooling"
    else:
        equivalents['primary_comparison'] = f"≈ {equivalents['h100_cluster_hours']:,} hours of H100 cluster cooling"
    return equivalents

# --- Core Analysis Function ---
def run_risk_analysis(input_csv='wells_input.csv'):
    wells_df = pd.read_csv(input_csv)
    wells_gdf = gpd.GeoDataFrame(wells_df, geometry=gpd.points_from_xy(wells_df.SH_LON, wells_df.SH_LAT), crs=GEOGRAPHIC_CRS).to_crs(TARGET_CRS)
    print(f'Loaded and processed {len(wells_gdf)} wells.')

    print('\nLoading data sources...')
    county_use_df = get_county_water_use_data()
    domestic_wells_data = []
    for _, well in wells_gdf.iterrows():
        for i in range(int(well.get('domestic_wells_1km', 0))):
            angle, distance = np.random.uniform(0, 2*np.pi), np.random.uniform(100, 1000)
            x_offset, y_offset = distance * np.cos(angle), distance * np.sin(angle)
            domestic_wells_data.append({'geometry': Point(well.geometry.x + x_offset, well.geometry.y + y_offset), 'associated_orphan': well.API})
    domestic_wells_gdf = gpd.GeoDataFrame(domestic_wells_data, crs=TARGET_CRS) if domestic_wells_data else gpd.GeoDataFrame(columns=['geometry'], crs=TARGET_CRS)

    print('\nDownloading and loading GIS data...')
    try:
        aquifer_dir = os.path.join(DATA_DIR, 'aquifers')
        download_and_unzip('https://www.owrb.ok.gov/maps/data/layers/groundwater/gw_owrb_aquifers.zip', aquifer_dir, 'gw_owrb_aquifers.shp')
        aquifers_gdf = gpd.read_file(os.path.join(aquifer_dir, 'gw_owrb_aquifers.shp')).to_crs(TARGET_CRS)
        nhd_dir = os.path.join(DATA_DIR, 'nhd_ok')
        download_and_unzip('https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHD/State/Shape/NHD_H_Oklahoma_State_Shape.zip', nhd_dir, 'Shape/NHDFlowline_0.shp')
        nhd_shape_dir = os.path.join(nhd_dir, 'Shape')
        flowline_parts = []
        for item in os.listdir(nhd_shape_dir):
            if item.startswith('NHDFlowline') and item.endswith('.shp'):
                flowline_parts.append(gpd.read_file(os.path.join(nhd_shape_dir, item)).to_crs(TARGET_CRS))
        nhd_flowlines = pd.concat(flowline_parts, ignore_index=True)
        gis_layers = {'aquifers': aquifers_gdf, 'flowlines': nhd_flowlines}
        print('GIS data loaded successfully.')
    except Exception as e:
        print(f'FATAL: Error loading GIS data: {e}. Exiting.')
        return None, None

    results = []
    for index, well in wells_gdf.iterrows():
        print(f'\n--- Processing well {well.API} ({well.WELL_NAME}) ---')
        metrics = well.to_dict()
        metrics['Data_Gap_Flag'] = 0

        component_metrics = calculate_risk_components(well, gis_layers)
        metrics.update(component_metrics)

        score_cols = ['aquifer_score', 'surface_water_score', 'casing_age_score', 'spill_score', 'receptors_score']
        final_score = sum(metrics.get(col, 0) for col in score_cols)
        metrics['final_score'] = round(final_score, 0)

        if metrics['final_score'] >= 60: metrics['risk_tier'] = 'High'
        elif 30 <= metrics['final_score'] < 60: metrics['risk_tier'] = 'Moderate'
        else: metrics['risk_tier'] = 'Low'

        drastic_factor = get_drastic_factor(well.geometry, aquifers_gdf)
        metrics['Drastic_Factor'] = drastic_factor
        metrics['Drastic_Class'] = next((k for k, v in DRASTIC_MAPPING.items() if abs(v - drastic_factor) < 0.1), 'Moderate')

        nearby_domestic = domestic_wells_gdf[domestic_wells_gdf.distance(well.geometry) <= 1000] if not domestic_wells_gdf.empty else gpd.GeoDataFrame()
        dom_demand_wtd = distance_weighted_demand(well.geometry, nearby_domestic, county_use_df, well.get('COUNTY', 'UNKNOWN'))
        metrics['Domestic_Demand_Wtd_m3_yr'] = round(dom_demand_wtd, 1)

        p_leak = sigmoid_prob(metrics['final_score']) * drastic_factor
        metrics['P_Leak'] = round(p_leak, 3)

        water_safeguarded_m3 = dom_demand_wtd * p_leak
        metrics['Water_Safeguarded_m3_yr'] = round(water_safeguarded_m3, 1)
        metrics['Water_Safeguarded_acft_yr'] = round(water_safeguarded_m3 * ACRE_FT_PER_M3, 3)

        ai_equivalents = water_to_ai_compute_equivalent(water_safeguarded_m3)
        metrics.update({f'AI_{k}': v for k, v in ai_equivalents.items()})

        mean_leak_m3_day = np.mean(LEAK_RATE_RANGE_M3_DAY)
        metrics['Contaminant_Load_Removed_m3_yr'] = round(mean_leak_m3_day * 365 * p_leak, 1)

        print(f'  Component Scores: { {k: round(metrics.get(k, 0), 1) for k in score_cols} }')
        print(f'  Final Score: {metrics["final_score"]} ({metrics["risk_tier"]})')
        print(f'  Water Safeguarded: {metrics["Water_Safeguarded_m3_yr"]} m³/yr')

        results.append(metrics)

    final_df = pd.DataFrame(results)
    return final_df, {**gis_layers, 'domestic_wells': domestic_wells_gdf}

if __name__ == "__main__":
    run_risk_analysis()