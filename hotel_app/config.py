import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "hotel_booking.db")


def _load_env_file():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file()

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY") or os.urandom(32).hex()

MODEL_DIR = os.path.join(BASE_DIR, "model_files")
RF_MODEL_PATH = os.path.join(MODEL_DIR, "random_forest_model.pkl")
ENCODERS_PATH = os.path.join(MODEL_DIR, "encoders.pkl")
FEATURE_COLS_PATH = os.path.join(MODEL_DIR, "feature_cols.pkl")

UPLOAD_FOLDER = os.path.join("static", "uploads", "rooms")
MENU_PLAN_UPLOAD_FOLDER = os.path.join("static", "uploads", "menu_plans")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

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
    "arrival_year",
    "avg_price_per_room",
    "market_segment_type_encoded",
    "total_nights",
]
