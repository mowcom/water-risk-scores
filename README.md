# Orphan Well Water Pollution Risk Assessment

This project provides a reproducible workflow and an interactive Streamlit application to assess the potential water pollution risk from orphan oil and gas wells in Oklahoma. It ingests an initial list of wells, automatically downloads required public GIS data, scores each well based on a customizable weighted rubric, and presents the findings through an interactive dashboard.

## Features

- **Automated Data Ingestion**: Downloads required GIS layers from public sources (OWRB, NHD).
- **Reproducible Scoring**: Calculates a risk score for each well based on proximity to aquifers, surface water, and other factors.
- **Water Safeguarded Metric**: Quantifies the annual volume of potable water supply that would be protected by plugging each well.
- **Interactive Dashboard**: A Streamlit application allows users to view overall scores and drill down into a detailed map and metrics for each individual well.
- **Cached Analysis**: The initial data processing and analysis is cached, allowing the application to load almost instantly after the first run.
- **Exportable Outputs**: Automatically generates a `water_risk_scores.csv` file, a `well_metrics.json` file, and high-resolution PNG maps for each well.

## Enhanced Water Safeguarded Methodology

The application now features an **enhanced Water Safeguarded calculation** that incorporates advanced modeling techniques for more robust risk assessment.

### Enhanced Methodology

**Core Formula**: `Distance-Weighted Domestic Demand × Leak Probability`

**Components**:
1. **DRASTIC Vulnerability Assessment**: Aquifer susceptibility to contamination (1.0 = Very High ... 0.2 = Very Low)
2. **Distance-Weighted Domestic Demand**: County-specific water use data weighted by distance to domestic wells within 1km
3. **Sigmoid Probability Model**: Converts risk scores to leak probabilities using: `P = 1/(1 + exp(-(score-50)/7.5))`
4. **Optional Monte Carlo Simulation**: Provides uncertainty quantification with 5th, 50th, and 95th percentiles

### Enhanced Results Summary

| Well | Risk Score | Leak Prob | Distance-Weighted Demand | Enhanced Water Safeguarded |
|------|------------|-----------|-------------------------|----------------------------|
| KING-OH #38A | 75 (High) | 0.772 | 6,308 m³/yr | 3.95 ac-ft/yr |
| SCHNITZER #2 | 77 (High) | 0.779 | 2,275 m³/yr | 1.44 ac-ft/yr |
| BLAKE A-1 | 43 (Moderate) | 0.226 | 1,775 m³/yr | 0.33 ac-ft/yr |
| RAYMOND #3-1 | 37 (Moderate) | 0.120 | 0 m³/yr | 0.00 ac-ft/yr |
| JUDITH #1-2 | 26 (Low) | 0.031 | 0 m³/yr | 0.00 ac-ft/yr |

**Total Enhanced Water Safeguarded**: 5.72 acre-feet/year

### Additional Metrics

- **Contaminant Load Avoided**: Annual volume of potential contamination prevented (based on leak rates 0.5-5.9 m³/day)
- **DRASTIC Classification**: Aquifer vulnerability assessment for each well location
- **County-Specific Water Use**: Integrated USGS county-level domestic water consumption data

### Parameters

- `LEAK_RATE_RANGE_M3_DAY = (0.5, 5.9)`: Range of potential leak rates
- `RUN_MONTE_CARLO = False`: Toggle for uncertainty quantification  
- `MONTE_CARLO_ITERATIONS = 10,000`: Number of simulation runs

This enhanced methodology provides more scientifically robust estimates for prioritizing well plugging efforts and quantifying environmental protection benefits.

*Note: One acre-foot is approximately enough to meet indoor water demand for 6-7 rural households for a year.*

## Setup and Installation

To run this project, you will need to have Conda installed.

1.  **Clone the repository (or download the files):**
    ```bash
    git clone <your-repo-url>
    cd water-pollution-risk
    ```

2.  **Create and activate the Conda environment:**
    The required packages are listed in the script headers, but you can create the environment with the following command:
    ```bash
    conda create --name water-risk -c conda-forge python=3.9 geopandas matplotlib streamlit pandas pillow -y
    conda activate water-risk
    ```

## How to Run the Application

Once the environment is activated, you can launch the Streamlit application by running the following command in your terminal:

```bash
streamlit run app.py
```

The app will open in your web browser. The first time it runs, it will download the necessary GIS data (~700 MB) and perform the analysis. This may take a few minutes. Subsequent launches will be much faster due to caching.

## Project Structure

-   `app.py`: The main Streamlit application file. This is the entry point for running the interactive dashboard.
-   `water_risk_scorer.py`: Contains the core data processing and risk scoring logic. It handles downloading data and calculating metrics for each well.
-   `run_analysis.py`: Contains the logic for generating the output files (CSV, JSON, PNG maps). It is called by both the main analysis script and the Streamlit app.
-   `wells_input.csv`: The initial input file containing the list of orphan wells to be analyzed.
-   `output/`: This directory is created automatically and will contain all the generated reports and maps.

## Data Sources

-   **Well Data**: Provided initially in `wells_input.csv`.
-   **Aquifers**: Oklahoma Water Resources Board (OWRB).
-   **Flowlines**: National Hydrography Dataset (NHDPlus HR).
-   **Domestic Well Counts**: Estimated from dossier analysis of nearby households on private water supply. 