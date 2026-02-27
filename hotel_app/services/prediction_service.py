import os
import pickle
from datetime import date, timedelta

import pandas as pd

from hotel_app import config
from hotel_app.models import booking_model

SEGMENT_MAP = {
    "Online": "Online",
    "Offline": "Offline",
    "Corporate": "Corporate",
    "Complementary": "Complementary",
    "Airline Guest": "Aviation",
    "Aviation": "Aviation",
}

rf_model = None
encoders = {}
feature_cols = config.DEFAULT_MODEL_FEATURE_COLS.copy()


def load_file(path, label):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as file_obj:
            return pickle.load(file_obj)
    except Exception as e:
        print(f"Could not load {label}:", e)
        return None


def load():
    global rf_model, encoders, feature_cols

    loaded_model = load_file(config.RF_MODEL_PATH, "RF model")
    if loaded_model is not None:
        rf_model = loaded_model

    loaded_encoders = load_file(config.ENCODERS_PATH, "encoders")
    if loaded_encoders is not None:
        encoders = loaded_encoders

    loaded_feature_cols = load_file(config.FEATURE_COLS_PATH, "feature columns")
    if loaded_feature_cols is not None:
        feature_cols = loaded_feature_cols


def get_val(row, key, default=0):
    try:
        value = row[key]
    except Exception:
        value = default
    if value is None:
        return default
    return value


def enc_segment(db_value, encoder, default_model_cat="Offline"):
    if encoder is None or not hasattr(encoder, "classes_"):
        return -1

    raw_value = str(db_value).strip() if db_value is not None else ""
    if raw_value in encoder.classes_:
        return int(encoder.transform([raw_value])[0])

    mapped_value = SEGMENT_MAP.get(raw_value, default_model_cat)
    if mapped_value in encoder.classes_:
        return int(encoder.transform([mapped_value])[0])

    if default_model_cat in encoder.classes_:
        return int(encoder.transform([default_model_cat])[0])
    return -1


def split_nights(arrival_year, arrival_month, arrival_date, total_stays):
    try:
        checkin = date(int(arrival_year), int(arrival_month), int(arrival_date))
    except Exception:
        return 0, 0

    weekend_nights = 0
    for day_idx in range(max(0, int(total_stays))):
        current_day = checkin + timedelta(days=day_idx)
        if current_day.weekday() in (4, 5):
            weekend_nights += 1

    week_nights = max(0, int(total_stays) - weekend_nights)
    return week_nights, weekend_nights


def history_features(booking_row):
    customer_id = get_val(booking_row, "customer_id", None)
    booking_id = get_val(booking_row, "booking_id", None)

    if customer_id is None:
        repeated_guest = int(get_val(booking_row, "repeated_guest", 0))
        previous_not_canceled = int(get_val(booking_row, "no_of_previous_bookings_not_canceled", 0))
        return repeated_guest, previous_not_canceled

    try:
        customer_id = int(customer_id)
    except Exception:
        return 0, 0

    try:
        booking_id = int(booking_id) if booking_id is not None else None
    except Exception:
        booking_id = None

    previous_total, previous_not_canceled = booking_model.customer_history(customer_id, booking_id)
    repeated_guest = 1 if previous_total > 0 else 0
    return repeated_guest, previous_not_canceled


def make_features(booking_row, segment_encoded):
    total_stays = int(get_val(booking_row, "total_stays", get_val(booking_row, "total_nights", 0)))
    if total_stays > 30:
        total_stays = 30

    arrival_year = int(get_val(booking_row, "arrival_year", 0))
    arrival_month = int(get_val(booking_row, "arrival_month", 1))
    arrival_date = int(get_val(booking_row, "arrival_date", 1))
    no_of_week_nights, no_of_weekend_nights = split_nights(
        arrival_year,
        arrival_month,
        arrival_date,
        total_stays,
    )
    repeated_guest, previous_not_canceled = history_features(booking_row)

    return {
        "lead_time": int(get_val(booking_row, "lead_time", 0)),
        "no_of_special_requests": int(get_val(booking_row, "no_of_special_requests", 0)),
        "avg_price_per_room": float(get_val(booking_row, "avg_price_per_room", 0.0)),
        "market_segment_type_encoded": int(segment_encoded),
        "repeated_guest": int(repeated_guest),
        "total_stays": total_stays,
        "no_of_week_nights": int(no_of_week_nights),
        "total_guests": int(get_val(booking_row, "total_guests", 0)),
        "required_car_parking_space": int(get_val(booking_row, "required_car_parking_space", 0)),
        "no_of_weekend_nights": int(no_of_weekend_nights),
        "no_of_previous_bookings_not_canceled": int(previous_not_canceled),
    }


def predict(booking_row):
    if rf_model is None:
        return 0.0

    segment_encoder = encoders.get("market_segment_type") or encoders.get(
        "market_segment_type_encoded"
    )
    segment_encoded = enc_segment(
        get_val(booking_row, "segment_name", "Offline"), segment_encoder, "Offline"
    )

    enriched_row = dict(booking_row)

    df_input = pd.DataFrame([make_features(enriched_row, segment_encoded)])
    model_feature_cols = feature_cols
    if rf_model is not None and hasattr(rf_model, "feature_names_in_"):
        model_feature_cols = list(rf_model.feature_names_in_)
    df_input = df_input.reindex(columns=model_feature_cols, fill_value=0)

    return float(rf_model.predict_proba(df_input)[0, 1])
