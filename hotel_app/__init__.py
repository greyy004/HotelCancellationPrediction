import os

from flask import Flask

from hotel_app.config import (
    APP_SECRET_KEY,
    BASE_DIR,
    MENU_PLAN_UPLOAD_FOLDER,
    UPLOAD_FOLDER,
)
from hotel_app.models.db import init_db
from hotel_app.routes import register_all_routes
from hotel_app.services.prediction_service import load_prediction_artifacts


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
        static_url_path="/static",
    )
    app.secret_key = APP_SECRET_KEY

    room_upload_path = os.path.join(BASE_DIR, UPLOAD_FOLDER)
    meal_upload_path = os.path.join(BASE_DIR, MENU_PLAN_UPLOAD_FOLDER)

    os.makedirs(room_upload_path, exist_ok=True)
    os.makedirs(meal_upload_path, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = room_upload_path
    app.config["MENU_PLAN_UPLOAD_FOLDER"] = meal_upload_path

    init_db()
    load_prediction_artifacts()
    register_all_routes(app)

    return app
