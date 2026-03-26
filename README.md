# Hotel Cancellation Prediction (Flask + Random Forest)

This project is a hotel booking web app with cancellation risk prediction.

## Stack
- Flask
- SQLite
- scikit-learn (Random Forest)
- Jinja templates + static CSS

## Project Structure
- `app.py`: thin entrypoint
- `hotel_app/config.py`: app config and paths
- `hotel_app/routes/`: route registration
- `hotel_app/controllers/`: request/response handlers
- `hotel_app/models/`: DB query layer
- `hotel_app/services/`: business logic (booking, payment, prediction, hold rules)
- `templates/`: HTML templates
- `static/`: CSS and uploads
- `model_files/`: model artifacts (`.pkl`, feature files)

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables:
   - `APP_SECRET_KEY`
   - `KHALTI_SECRET_KEY` (required for online payments)
   - `FLASK_DEBUG` (optional: `1` or `true`)

## Run
```bash
python app.py
```

## Optional Demo Seed (after DB reset)
If you reset the database and want quick test data (1 room type, 1 room, 2 facilities):
```bash
python seed_demo_data.py
```

To seed a demo normal user account:
```bash
python seed_demo_user.py
```

To create an admin account:
```bash
python create_admin.py
```

## Model Artifacts
Prediction uses:
- `model_files/random_forest_model.pkl`
- `model_files/encoders.pkl`
- `model_files/feature_cols.pkl`

If `feature_cols.pkl` cannot be loaded, fallback features in `hotel_app/config.py` are used.
