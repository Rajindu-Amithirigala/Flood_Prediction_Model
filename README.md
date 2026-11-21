# Kelani River Basin Flood Early-Warning System

> **Status: Work in Progress.** This project is under active development. The data pipeline is partly complete, no model has been trained yet, and results, scope and design decisions described below may change.

## Overview

This project aims to build a flood early-warning system for Sri Lanka, starting with the Kelani River basin. The research question is:

> Given current and recent rainfall across the Kelani basin, can we predict whether flooding will occur within the next few hours or days?

The long-term goal is a live data pipeline, a machine-learning prediction service, and an interactive risk map. The current phase is **building the training dataset**.

```text
Live rainfall -> Rainfall features -> ML flood model -> Flood probability / warning -> Interactive product
```

## Data Sources

| Source | Purpose | Status |
|---|---|---|
| Disaster Management Centre (DMC), Sri Lanka | Historical water-level reports (PDF), used to derive flood labels | Collected and parsed |
| NASA GPM IMERG (Early run, half-hourly) | Rainfall history and, later, near-real-time rainfall | Download in progress |
| NSDI flood GIS data | Spatial validation | Planned |

IMERG Early run is used for both training and live prediction so the model sees the same product in both settings.

## Progress So Far

### 1. Water-level dataset (DMC reports)
- Scraped the DMC report index and downloaded the report PDFs (`scrape_dmc.py`, `download_dmc.py`).
- Restricted the archive to 2020 onward and identified roughly 2,094 water-level reports.
- Built a PDF table parser (`build_water_level_dataset.py`). It reads the actual table structure rather than raw text, detects column positions per file, and handles layout differences between report years and variant station names.
- Extracted about 11,430 observations for the seven Kelani stations: Nagalagam Street, Hanwella, Glencourse, Kitulgala, Holombuwa, Deraniyagala and Norwood.

### 2. Flood labels
- Compared observed water levels against DMC minor and major flood thresholds to produce `flood_now` and `major_flood_now` labels, aggregated across the seven stations per report time (`build_flood_labels.py`).
- Result: about 1,600 timestamped observations from May 2020 to August 2026, with roughly 8.6% flagged as flooding.
- Grouped flood observations into 17 distinct flood episodes (`event_diagnostic.py`).

### 3. Rainfall data (in progress)
- Chose IMERG Early-run half-hourly data, read directly from NASA at the seven station locations, with only the needed pixels stored (`download_imerg.py`).
- Validated the approach on a test week (27 Nov to 3 Dec 2025): heavy rain on 27 to 28 Nov followed by a dry spell, consistent with the recorded flood episode.
- Running the full 2020 to 2026 download in Google Colab (`colab_imerg_cells.py`), because of home-network data limits. At the last check, 52 of the 76 required months were complete and the remainder still had to be downloaded.
- Wrote the rainfall feature generator (`rainfall_features.py`): rolling rainfall totals over 0.5, 1, 3, 6, 12, 24 and 48 hours per station and basin-wide, with a 4-hour data-latency offset so that training matches live conditions.

## Planned Work

1. **Finish the rainfall download** and confirm all 76 months (May 2020 to August 2026) are present.
2. **Build the training table** by aligning rainfall features with DMC report times (converting Sri Lanka time to UTC).
3. **Create forecast targets** (`flood_next_Nh`) from the flood labels. The proposed approach leaves a target blank when no DMC report falls inside the window, because the outcome is unobserved. Main horizons proposed: 6, 12 and 24 hours, with 3 hours expected to have limited data. *This approach is not yet finalised.*
4. **Add river-state features** (current level and trend) so that a rainfall-only model can be compared with a rainfall-plus-river-state model.
5. **Train and evaluate baseline models**: Logistic Regression, Random Forest and XGBoost, using time-ordered train/test splits to avoid leakage, then assess whether temporal models are justified.
6. **Live pipeline**: scheduled retrieval of near-real-time IMERG data, shared feature code for training and live use, and a prediction output for a dashboard or API.
7. **Later improvements**: per-station labels, terrain data, satellite flood detection, and population exposure.

## Known Limitations

- DMC reports are irregular, roughly twice daily outside floods and more often during them, which limits short-horizon targets.
- Flood events are few (17 episodes), so evaluation will be sensitive to how the data is split.
- IMERG pixels are about 10 km wide, so small tributaries are only coarsely represented.
- The live system will receive rainfall data about four hours old.
- No model has been trained, so no performance claims can be made yet.

## Repository Scripts

| Script | Purpose |
|---|---|
| `scrape_dmc.py` | Scrapes the DMC report index |
| `download_dmc.py` | Downloads report PDFs |
| `build_water_level_dataset.py` | Extracts station observations from PDF tables |
| `build_flood_labels.py` | Derives flood labels from thresholds |
| `event_diagnostic.py` | Groups flood observations into episodes |
| `download_imerg.py` | Extracts IMERG rainfall at the station locations |
| `check_imerg.py` | Sanity checks on downloaded rainfall |
| `rainfall_features.py` | Rolling rainfall features for training and live use |
| `colab_imerg_cells.py` | Notebook cells for running the download on Colab |

*Last updated: November 2026.*
