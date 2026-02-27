import os

from flask import Flask

from hotel_app import config
from hotel_app.models import db as db_model
from hotel_app.routes import reg_all
from hotel_app.services import prediction_service


def build():
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static"),
        static_url_path="/static",
    )
    app.secret_key = config.APP_SECRET_KEY

    upload_paths = {
        "UPLOAD_FOLDER": os.path.join(config.BASE_DIR, config.UPLOAD_FOLDER),
        "MENU_PLAN_UPLOAD_FOLDER": os.path.join(
            config.BASE_DIR, config.MENU_PLAN_UPLOAD_FOLDER
        ),
    }
    for config_key, path in upload_paths.items():
        os.makedirs(path, exist_ok=True)
        app.config[config_key] = path

    db_model.init()
    prediction_service.load()
    reg_all(app)

    return app
