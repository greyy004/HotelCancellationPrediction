import os
import pickle
from datetime import datetime, timedelta

import pandas as pd

from hotel_app.config import (
    DEFAULT_MODEL_FEATURE_COLS,
    ENCODERS_PATH,
    FEATURE_COLS_PATH,
    RF_MODEL_PATH,
)

SEGMENT_MAP = {
    "Online": "Online",
    "Offline": "Offline",
}

rf_model = None
encoders = {}
feature_cols = DEFAULT_MODEL_FEATURE_COLS.copy()


def load_prediction_artifacts():
    global rf_model, encoders, feature_cols

    if os.path.exists(RF_MODEL_PATH):
        try:
            with open(RF_MODEL_PATH, "rb") as f:
                rf_model = pickle.load(f)
        except Exception as e:
            print("Could not load RF model:", e)

    if os.path.exists(ENCODERS_PATH):
        try:
            with open(ENCODERS_PATH, "rb") as f:
                encoders = pickle.load(f)
        except Exception as e:
            print("Could not load encoders:", e)

    if os.path.exists(FEATURE_COLS_PATH):
        try:
            with open(FEATURE_COLS_PATH, "rb") as f:
                feature_cols = pickle.load(f)
        except Exception as e:
            print("Could not load feature columns:", e)


def is_model_available():
    return rf_model is not None


def encode_segment(db_value, encoder, default_model_cat="Offline"):
    if encoder is None or not hasattr(encoder, "classes_"):
        return -1

    raw_value = str(db_value).strip() if db_value is not None else ""
    model_cat = SEGMENT_MAP.get(raw_value)
    if model_cat is None:
        lowered = raw_value.lower()
        if lowered == "online":
            model_cat = "Online"
        elif lowered == "offline":
            model_cat = "Offline"
        else:
            model_cat = default_model_cat

    if model_cat in encoder.classes_:
        return int(encoder.transform([model_cat])[0])
    if default_model_cat in encoder.classes_:
        return int(encoder.transform([default_model_cat])[0])
    return -1


def derive_night_split(arrival_year, arrival_month, arrival_date, total_nights):
    try:
        nights = max(0, int(total_nights or 0))
        checkin = datetime(int(arrival_year), int(arrival_month), int(arrival_date)).date()
    except Exception:
        return 0, 0

    weekend_nights = 0
    current = checkin
    for _ in range(nights):
        if current.weekday() in (4, 5):
            weekend_nights += 1
        current += timedelta(days=1)

    week_nights = max(0, nights - weekend_nights)
    return weekend_nights, week_nights


def build_model_features_from_booking(booking_row, seg_enc):
    arrival_year = int((booking_row["arrival_year"] or 0))
    arrival_month = int((booking_row["arrival_month"] or 0))
    arrival_date = int((booking_row["arrival_date"] or 0))
    total_nights = int((booking_row["total_nights"] or 0))

    weekend_nights, week_nights = derive_night_split(
        arrival_year,
        arrival_month,
        arrival_date,
        total_nights,
    )

    return {
        "lead_time": int((booking_row["lead_time"] or 0)),
        "avg_price_per_room": float((booking_row["avg_price_per_room"] or 0)),
        "no_of_special_requests": int((booking_row["no_of_special_requests"] or 0)),
        "arrival_month": arrival_month,
        "market_segment_type_encoded": seg_enc,
        "arrival_date": arrival_date,
        "total_nights": total_nights,
        "arrival_year": arrival_year,
        "no_of_week_nights": week_nights,
        "no_of_weekend_nights": weekend_nights,
    }


def predict_booking_cancellation_probability(booking_row):
    if rf_model is None:
        return 0.0

    seg_encoder = encoders.get("market_segment_type") or encoders.get(
        "market_segment_type_encoded"
    )
    seg_enc = encode_segment(booking_row["segment_name"], seg_encoder, "Offline")
    df_input = pd.DataFrame([build_model_features_from_booking(booking_row, seg_enc)])
    df_input = df_input.reindex(columns=feature_cols, fill_value=0)
    return float(rf_model.predict_proba(df_input)[0, 1])
