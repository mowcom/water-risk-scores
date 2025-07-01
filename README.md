# Orphan Well Water Pollution Risk Assessment

This project provides a reproducible workflow and an interactive Streamlit application to assess the potential water pollution risk from orphan oil and gas wells in Oklahoma. It ingests an initial list of wells, automatically downloads required public GIS data, scores each well based on a customizable weighted rubric, and presents the findings through an interactive dashboard.

## Features

- **Automated Data Ingestion**: Downloads required GIS layers from public sources (OWRB, NHD).
- **Reproducible Scoring**: Calculates a risk score for each well based on proximity to aquifers, surface water, and other factors.
- **Interactive Dashboard**: A Streamlit application allows users to view overall scores and drill down into a detailed map and metrics for each individual well.
- **Cached Analysis**: The initial data processing and analysis is cached, allowing the application to load almost instantly after the first run.
- **Exportable Outputs**: Automatically generates a `water_risk_scores.csv` file, a `well_metrics.json` file, and high-resolution PNG maps for each well.

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
-   `data/wells_input.csv`: The initial input file containing the list of orphan wells to be analyzed.
-   `output/`: This directory is created automatically and will contain all the generated reports and maps.

## Data Sources

-   **Well Data**: Provided initially in `data/wells_input.csv`.
-   **Aquifers**: Oklahoma Water Resources Board (OWRB).
-   **Flowlines**: National Hydrography Dataset (NHDPlus HR). 