import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "hotel_booking.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY") or os.urandom(32).hex()

MODEL_DIR = os.path.join(BASE_DIR, "model_files")
RF_MODEL_PATH = os.path.join(MODEL_DIR, "random_forest_model.pkl")
ENCODERS_PATH = os.path.join(MODEL_DIR, "encoders.pkl")
FEATURE_COLS_PATH = os.path.join(MODEL_DIR, "feature_cols.pkl")

UPLOAD_FOLDER = os.path.join("static", "uploads", "rooms")
MENU_PLAN_UPLOAD_FOLDER = os.path.join("static", "uploads", "menu_plans")

KHALTI_SECRET_KEY = os.getenv("KHALTI_SECRET_KEY", "").strip()
KHALTI_GATEWAY_URL = "https://dev.khalti.com/api/v2"

PENDING_PAYMENT_SESSION_KEYS = (
    "pending_booking",
    "pending_amount",
    "pending_pidx",
    "purchase_order_id",
)

DEFAULT_MODEL_FEATURE_COLS = [
    "lead_time",
    "no_of_special_requests",
    "avg_price_per_room",
    "market_segment_type_encoded",
    "repeated_guest",
    "total_stays",
    "no_of_week_nights",
    "total_guests",
    "required_car_parking_space",
    "no_of_weekend_nights",
    "no_of_previous_bookings_not_canceled",
]
