# train.ipynb Training Report

This report summarizes the current `train.ipynb` pipeline and the latest executed results.

## 1) Goal

Predict whether a hotel reservation will be canceled (`cancellation = 1`) or not (`cancellation = 0`) using a Random Forest model.

## 2) Dataset Summary

- Source file: `hotel.csv`
- Initial shape: `36275 rows x 19 columns`
- Target source column: `booking_status`
  - `Not_Canceled` = `0`
  - `Canceled` = `1`

## 3) Data Cleaning

- Removed extreme outliers in children count:
  - kept rows where `no_of_children <= 3`
- Shape after this cleanup: `36272 rows`
- Created derived features and removed zero-stay rows:
  - Final modeling rows: `36194`

## 4) Feature Engineering

The notebook now uses simpler derived features for deployment alignment:

- `total_guests = no_of_adults + no_of_children`
- `total_stays = no_of_week_nights + no_of_weekend_nights`

Currency conversion step:

- Converted `avg_price_per_room` from EUR to NPR using live rate with fallback.
- Live rate used in latest run: `1 EUR = 171.518275 NPR`
- Original EUR value is retained as `avg_price_per_room_eur` (for analysis only).

## 5) Encoding

- Target encoded to binary in `cancellation`
- Label encoders used for:
  - `type_of_meal_plan` -> `type_of_meal_plan_encoded`
  - `market_segment_type` -> `market_segment_type_encoded`

Encoder classes from latest run:

- Meal classes: `['Meal Plan 1', 'Meal Plan 2', 'Meal Plan 3', 'Not Selected']`
- Segment classes: `['Aviation', 'Complementary', 'Corporate', 'Offline', 'Online']`

## 6) EDA and Correlation Findings

EDA plots included:

- Booking status count
- Lead time distribution
- Avg price (NPR) vs cancellation
- Cancellation rate by market segment
- Full numeric correlation heatmap

Top correlations with `cancellation` (latest run):

1. `lead_time`: `0.438389`
2. `no_of_special_requests`: `-0.253227`
3. `arrival_year`: `0.179650`
4. `avg_price_per_room`: `0.139900`
5. `market_segment_type_encoded`: `0.136248`
6. `total_stays`: `0.101416`
7. `total_guests`: `0.090149`
8. `required_car_parking_space`: `-0.086489`

## 7) Final Model Features

Selected features used for training and saved for app inference:

1. `lead_time`
2. `no_of_special_requests`
3. `arrival_year`
4. `avg_price_per_room`
5. `total_stays`
6. `required_car_parking_space`
7. `type_of_meal_plan_encoded`
8. `market_segment_type_encoded`
9. `total_guests`

## 8) Train/Test Split

- Train size: `28955`
- Test size: `7239`
- Split method: `test_size=0.20`, `random_state=42`, `stratify=y`

## 9) Model Results

### Baseline Random Forest

- Accuracy: `0.8888`
- ROC-AUC: `0.9453`
- Confusion matrix:
  - `[[4495, 368],`
  - ` [ 437, 1939]]`

### Tuned Random Forest (GridSearchCV)

- Best params:
  - `max_depth=20`
  - `max_features='sqrt'`
  - `min_samples_leaf=1`
  - `min_samples_split=5`
  - `n_estimators=300`
- Best CV ROC-AUC: `0.9390`
- Test Accuracy: `0.8860`
- Test ROC-AUC: `0.9483`
- Confusion matrix:
  - `[[4429, 434],`
  - ` [ 391, 1985]]`

Note: tuned model improved AUC but slightly reduced accuracy.

## 10) Saved Artifacts

Generated files in `model_files/`:

- `random_forest_model.pkl`
- `encoders.pkl`
- `feature_cols.pkl`
- `feature_importance_full.csv`
- `selected_features.csv`

## 11) App Alignment Check

`feature_cols.pkl` matches `hotel_app/config.py` `DEFAULT_MODEL_FEATURE_COLS` exactly, so inference in the Flask app is aligned with this training notebook.
