# Orphan Well Water Pollution Risk Assessment

This project provides a reproducible workflow and an interactive Streamlit application to assess the potential water pollution risk from orphan oil and gas wells in Oklahoma. It ingests an initial list of wells, automatically downloads required public GIS data, scores each well based on a dynamic, data-driven rubric, and presents the findings through an interactive dashboard.

## Features

- **Automated Data Ingestion**: Downloads required GIS layers from public sources (OWRB, NHD).
- **Data-Driven Scoring (V2)**: Calculates a risk score for each well based on five dynamically calculated components.
- **Water Safeguarded Metric**: Quantifies the annual volume of potable water supply that would be protected by plugging each well.
- **Interactive Dashboard**: A Streamlit application allows users to view overall scores and drill down into a detailed map and metrics for each individual well.
- **Cached Analysis**: The initial data processing and analysis is cached, allowing the application to load almost instantly after the first run.
- **Exportable Outputs**: Automatically generates a `water_risk_scores.csv` file, a `well_metrics.json` file, and high-resolution PNG maps for each well.

## V2 Risk Scoring Methodology

The risk score is the sum of five components, each assessing a different aspect of water pollution risk. The raw component scores are summed to produce a `final_score` out of 100.

### 1. Aquifer Vulnerability (30 points)
- **Direct Intersection (20 pts)**: A well receives 20 points if its location directly intersects with a mapped major aquifer from the Oklahoma Water Resources Board (OWRB).
- **Proximity Vulnerability (10 pts)**: An additional 10 points are scaled based on the well's proximity to the nearest aquifer boundary, using an exponential decay function. A well inside an aquifer gets the full 10 points, while the score decreases as the distance increases.

### 2. Surface Water Proximity (20 points)
- Calculated based on the well's distance to the nearest surface water feature (rivers, streams) from the National Hydrography Dataset (NHD).
- The score is scaled using an inverse exponential function, awarding a higher score to wells closer to water bodies, as they pose a more immediate threat of contamination.

### 3. Well Integrity (Age/Casing) (20 points)
- **Well Age (10 pts)**: Risk increases with age. The score is scaled linearly, with a 50-year-old well receiving the full 10 points.
- **Surface Casing (10 pts)**: Inadequate surface casing is a major risk factor. This score rewards wells with deeper surface casing. A well with 0 feet of casing receives the full 10 points, while a well with 1500 feet or more receives 0 points.

### 4. Historical Spills (15 points)
- **Placeholder**: In the absence of a reliable historical spill dataset, this component currently assigns a neutral, baseline score of 5 points to all wells. This acknowledges the importance of this factor without penalizing wells due to a data gap.

### 5. Human Receptors (15 points)
- This score is based on the number of domestic water wells within a 1-kilometer radius of the orphan well.
- The score escalates with the number of nearby domestic wells, reflecting the increased potential impact on human populations. A well with 5 or more domestic wells nearby receives the maximum 15 points.

## Setup and Installation

To run this project, you will need to have Conda installed.

1.  **Clone the repository (or download the files):**
    ```bash
    git clone <your-repo-url>
    cd water-pollution-risk
    ```

2.  **Create and activate the Conda environment:**
    ```bash
    conda create --name water-risk -c conda-forge python=3.9 geopandas matplotlib streamlit pandas pillow fpdf2 -y
    conda activate water-risk
    ```

## How to Run the Application

Once the environment is activated, you can launch the Streamlit application by running the following command in your terminal:

```bash
streamlit run app.py
```

The app will open in your web browser. The first time it runs, it will download the necessary GIS data (~700 MB) and perform the analysis. Subsequent launches will be much faster due to caching.

## Next Steps & Future Improvements

- **Integrate Real Spill Data**: Source and integrate a dataset of historical oil and gas spills to replace the placeholder score in the 'Historical Spills' component.
- **Refine DRASTIC Model**: The current DRASTIC factor is a proxy based on aquifer proximity. A future version could incorporate official DRASTIC raster data for Oklahoma for a more precise hydrogeological vulnerability assessment.
- **Add More Receptor Types**: Expand the 'Human Receptors' component to include other sensitive locations, such as schools, hospitals, and public water supply intakes.

## Project Structure

-   `app.py`: The main Streamlit application file.
-   `water_risk_scorer.py`: The core data processing and V2 risk scoring logic.
-   `run_analysis.py`: A script to execute the analysis and generate all output files.
-   `wells_input.csv`: The primary input file containing the list of orphan wells and their attributes.
-   `output/`: Directory where all generated reports and maps are saved.