import os

from hotel_app import create_app


app = create_app()


if __name__ == "__main__":
    debug_mode = str(os.getenv("FLASK_DEBUG", "")).lower() in ("1", "true", "yes")
    app.run(debug=debug_mode)
