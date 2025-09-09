# Sorter Clubbing Optimizer - Comprehensive Business Document

## Executive Summary
- **Objective**: Consolidate, analyze, and optimize origin-destination flows to determine optimal branch bagging and sorting locations for two metrics: `Volume` and `Billed Wt`.
- **Approach**: Transform raw OD flow data into structured datasets; compute branch inclusion thresholds; apply elbow/knee detection for optimal branch counts; quantify final sorting location requirements; and visualize/operate via interactive Streamlit dashboards.
- **Key Outputs**:
  - `all_data.csv`, `all_data_percentage.csv`: Region × Service_Type × Type wide matrices of absolute values and percentages by destination branch
  - `bag_summary.csv`: Branches above threshold and cumulative % per (Region, Service_Type, Type)
  - `optimal_branches.csv`: Elbow-based optimal number of branches and lists per group
  - `final_sorting_location.csv`: Sorting location requirement per region and type
  - Streamlit dashboards: `bags.py` (bagging optimizer UI) and `geoplot.py` (map of branches with OD summaries)

## Data Sources
- `origin_destination_flow.csv`: Raw OD matrix (wide) with mixed headers/labels
- `office_location.csv`: Branch geocoding and descriptive names
- Mapping JSONs produced from processed `data.csv`:
  - `org_mappings.json`: Origin hierarchy Zone → Region → City → BranchCode → BranchName
  - `des_mappings.json`: Destination hierarchy Zone → Region → City → BranchCode → BranchName (validated identical across `Type`)

## Processing Pipeline

1) Raw data preparation (Notebook: `raw_data_processor.ipynb`)
- Standardize region codes (e.g., EUP/WUP → UPT; NDL/SDL/GGN → DDL)
- Fill missing hierarchical labels (vertical/horizontal forward-fill)
- Restrict to `NON DOCUMENTS` service types; drop hub/apex columns/rows
- Normalize fourth column into `branch_code` and `branch_name`; derive `service_type` from `org_product` (Air Red, Air White, Ground)
- Clean numeric block (7th row onward) to floats (remove commas, default 0) and convert to per-day using /25
- Output: `data.csv` with 6 destination header levels and 5+ origin index levels
- Derive mappings (`org_mappings.json`, `des_mappings.json`) with validation of destination parity across `Volume` and `Billed Wt`

2) Aggregations (Notebook: `raw_data_processor.ipynb`)
- `org_summary.csv`: Sum by origin branch and service type per `type` (Volume/Billed Wt)
- `des_summary.csv`: Sum by destination branch and service type per `type`

3) Bagging data construction (Notebook: `bags.ipynb`)
- From `data.csv` build `all_data.csv` (absolute) and `all_data_percentage.csv` (branch % share of total by group)
- Melt wide→long and merge to create `df_merge` with absolute `Value` and `Percentage`
- Threshold filter per Type (defaults used in notebooks: Volume ≥ 25, Billed Wt ≥ 35; Streamlit UI allows dynamic)
- Produce `bag_summary.csv` with for each (Region, Service_Type, Type): number of branches above threshold, cumulative % share, and branch list

4) Elbow-based optimal branches (Notebook: `bags.ipynb`)
- For each row in `bag_summary.csv`, sort candidate branches by share, compute cumulative %, apply elbow detection using maximum perpendicular distance to line between endpoints
- Save per-group optimal k, cumulative %, and branch shortlist into `optimal_branches.csv`
- Persist elbow plot images in `elbow_plots/`

5) Final sorting location estimation (Notebook: `bags.ipynb` and `processing.py`)
- Flatten `des_mappings.json` to count `Self_Branches` per Region
- Sum optimal branches across Service Types within each (Region, Type) to get `Sorting_Locations_for_Optimal_Branches`
- Compute `Sorting_Location_Needed = Sorting_Locations_for_Optimal_Branches + 60 + 2 * Self_Branches`
- Output: `final_sorting_location.csv`

## Algorithms & Formulas
- **Thresholding**: Keep branches with absolute Value ≥ `threshold[Type]`; thresholds configurable (UI sliders)
- **Elbow detection**: Index of max distance between cumulative curve and chord linking first and last points
- **Final sorting estimation**: Region-wise sum of optimal branches plus buffer (60) and per-self-branch uplift (×2)

## Interactive Dashboards

1) `bags.py` (Optimal Bagging Dashboard)
- Inputs: Threshold sliders, `Type` (Volume/Billed Wt), Region selector
- Views:
  - Sorting Location Requirement table with totals, optimal units, % through optimal, not-through-optimal metrics
  - All-India summary for selected Type (when Region = All India)
  - Comprehensive Service Type summary across metrics (downloadable CSV)
  - Threshold Branch Summary with names (branch code → name via `office_location.csv`)
  - Optimal Branches Summary with names
  - Service Type Analysis: elbow plots and optimal k per service type

2) `geoplot.py` (Branch Map Dashboard)
- Inputs: Data Type, Service Type filters, optional branch centering
- Map: Folium markers colored by zone with popups showing origin/destination totals, tooltips, and optional tile layers. Utilizes `branch_locations.csv`, `org_summary.csv`, `des_summary.csv`.

## Key Results & Artifacts
- `bag_summary.csv`: Summarizes thresholded branches and cumulative shares
- `optimal_branches.csv`: Provides optimal counts and branch lists per (Region, Service_Type, Type). Example:
  - AMD, Air White, Billed Wt → Optimal 66 branches, 40.75% cumulative
  - BLR, Air White, Billed Wt → Optimal 70 branches, 47.73% cumulative
- `final_sorting_location.csv`: Region × Type sorting capacity requirement, e.g.:
  - DDL, Billed Wt → 329 optimal branches, 29 self, need 447
  - BLR, Volume → 63 optimal branches, 35 self, need 193

## Data Model & Structures
- `data.csv` multi-index/multi-column structure in `algorithms.filter_and_sum`:
  - Index: `[org_zone, org_region, org_city, org_branch_code, org_branch_name, service_type, org_product]`
  - Columns: `[type, des_zone, des_region, des_city, des_branch_code, des_branch_name]`
- End-user utility: `filter_and_sum(...)` supports flexible slicing across origin/destination hierarchies and returns numeric sum

## Governance & Assumptions
- Per-day normalization assumes 25 working days
- Non-documents only, hubs/apex excluded from analysis and destination headers
- Destination branch mappings validated invariant across `Type`
- Region-first-letter ignore rule in `bags.ipynb` initial step prevents self-region first-letter branch inflation during melting

## How to Run
- Environment: see `requirements.txt`
- Notebooks: Execute `raw_data_processor.ipynb` to generate `data.csv` and mappings; then `bags.ipynb` to generate summaries, optimal branches, plots, and final sorting estimation
- Dashboards:
  - `streamlit run bags.py`
  - `streamlit run geoplot.py`

## Recommendations & Next Steps
- Parameterize thresholds by (Region, Service_Type, Type) based on optimization goals or SLA targets
- Add confidence intervals/sensitivity analysis around elbow choice (e.g., top-k ± δ)
- Integrate cost model (fixed vs variable) to convert optimal branches into operational savings and ROI
- Validate geocoding accuracy for overlapping lat/lon (multiple offices share coordinates) and refine with clustering
- Promote `filter_and_sum` into a service/API for downstream tooling
- Automate pipeline with Makefile or orchestrator (prefect/airflow) including artifact checks

## Appendix
- Datasets generated: `all_data.csv`, `all_data_percentage.csv`, `bag_summary.csv`, `optimal_branches.csv`, `final_sorting_location.csv`, `org_summary.csv`, `des_summary.csv`, `branch_locations.csv`, `hub_locations.csv`
- Elbow plots: `elbow_plots/*.png`
- Mapping JSON samples: see `org_mappings.json`, `des_mappings.json`
