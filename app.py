import os
import pickle
import sqlite3
import re
from datetime import date, datetime, timedelta
from functools import wraps

import pandas as pd
import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from hotel_app import config
from hotel_app.models import (
    booking_model,
    customer_model,
    db as db_model,
    extra_facility_model,
    market_segment_model,
    meal_plan_model,
    room_model,
)

# Model and risk config values
SEGMENT_MAP = {
    "Online": "Online",
    "Offline": "Offline",
}

HIGH_RISK_THRESHOLD = 0.4
MEDIUM_RISK_THRESHOLD = 0.2
CANCEL_LIKELY_THRESHOLD = 0.3

rf_model = None
encoders = {}
feature_cols = config.DEFAULT_MODEL_FEATURE_COLS.copy()


# Prediction helper functions
def get_val(row, key, default=0):
    # Safe read from dict/sqlite row, with fallback default.
    try:
        value = row[key]
    except Exception:
        value = default
    if value is None:
        return default
    return value


def encode_segment(db_value, encoder, default_model_cat="Offline"):
    # Convert DB market segment text into model encoder integer.
    if encoder is None:
        return -1
    if not hasattr(encoder, "classes_"):
        return -1

    raw_value = ""
    if db_value is not None:
        raw_value = str(db_value).strip()

    if raw_value in encoder.classes_:
        return int(encoder.transform([raw_value])[0])

    mapped_value = SEGMENT_MAP.get(raw_value, default_model_cat)
    if mapped_value in encoder.classes_:
        return int(encoder.transform([mapped_value])[0])

    if default_model_cat in encoder.classes_:
        return int(encoder.transform([default_model_cat])[0])
    return -1


def split_nights(arrival_year, arrival_month, arrival_date, total_stays):
    # Split total stay into weekday and weekend nights.
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
    # Build repeated-guest and previous non-cancel count from history.
    customer_id = get_val(booking_row, "customer_id", None)
    booking_id = get_val(booking_row, "booking_id", None)

    if customer_id is None:
        repeated_guest = int(get_val(booking_row, "repeated_guest", 0))
        previous_not_canceled = int(
            get_val(booking_row, "no_of_previous_bookings_not_canceled", 0)
        )
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
    # Create final model feature dict used by RandomForest.
    total_stays_value = get_val(booking_row, "total_stays", None)
    if total_stays_value is None:
        total_stays_value = get_val(booking_row, "total_nights", 0)
    total_stays = int(total_stays_value)
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


def predict_cancellation(booking_row):
    # Predict cancellation probability (0.0 to 1.0).
    if rf_model is None:
        return 0.0

    segment_encoder = encoders.get("market_segment_type") or encoders.get(
        "market_segment_type_encoded"
    )
    segment_encoded = encode_segment(
        get_val(booking_row, "segment_name", "Offline"), segment_encoder, "Offline"
    )

    df_input = pd.DataFrame([make_features(dict(booking_row), segment_encoded)])
    df_input = df_input.reindex(columns=feature_cols, fill_value=0)
    return float(rf_model.predict_proba(df_input)[0, 1])


def risk_label(probability):
    # Simple risk bucket for admin table badge.
    if probability > HIGH_RISK_THRESHOLD:
        return "High"
    if probability > MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def prediction_label(probability):
    # Human-readable label shown in UI.
    if probability > CANCEL_LIKELY_THRESHOLD:
        return "Likely to Cancel"
    return "Likely to NOT Cancel"


def can_hold_booking(booking):
    # Final rule check before allowing "put on hold".
    if not booking:
        return False, "Booking not found.", "danger"
    if booking["booking_status"] == "Canceled":
        return False, "Canceled bookings cannot be put on hold.", "warning"
    if int(booking["is_on_hold"] or 0) == 1:
        return False, "Booking is already on hold.", "info"
    return True, None, None


# Booking utility functions
def get_stay(data):
    # Convert arrival date + total nights into checkin/checkout dates.
    total_nights = int(data.get("total_nights") or 0)
    checkin = datetime(
        int(data["arrival_year"]),
        int(data["arrival_month"]),
        int(data["arrival_date"]),
    ).date()
    checkout = checkin + timedelta(days=total_nights)
    return checkin, checkout, total_nights


def get_stay_row(row):
    # Same as get_stay, but for DB row.
    total_nights = int(row["total_nights"] or 0)
    checkin = datetime(row["arrival_year"], row["arrival_month"], row["arrival_date"]).date()
    checkout = checkin + timedelta(days=total_nights)
    return checkin, checkout, total_nights


def get_unavailable_ranges(room_id):
    # Return booked date ranges for calendar blocking on frontend.
    rows = booking_model.list_active_windows(room_id)
    ranges = []
    for row in rows:
        start, end, nights = get_stay_row(row)
        if nights > 0:
            ranges.append({"start": start.isoformat(), "end": end.isoformat()})
    return ranges


def is_room_available(room_id, checkin, checkout):
    # Basic overlap check against active bookings of that room.
    rows = booking_model.list_active_room(room_id)
    for row in rows:
        existing_checkin, existing_checkout, _ = get_stay_row(row)
        if checkin < existing_checkout and checkout > existing_checkin:
            return False
    return True


def check_guests(room_id, total_guests):
    # Validate guest count against room max capacity.
    total_guests_int = int(total_guests or 0)
    if total_guests_int < 1:
        return False, "At least 1 guest is required."

    room = room_model.find_max_guests_for_room(room_id)
    if not room:
        return False, "Room not found."

    max_guests = int(room["max_guests"] or 2)
    if total_guests_int > max_guests:
        return False, f"This room allows a maximum of {max_guests} guests."
    return True, None


def validate_booking_request(room_id, booking_data):
    is_valid_guests, guest_error = check_guests(room_id, booking_data.get("total_guests"))
    if not is_valid_guests:
        return False, guest_error, None, None, None

    try:
        checkin, checkout, total_nights = get_stay(booking_data)
    except Exception:
        return False, "Invalid date selection", None, None, None

    if total_nights <= 0:
        return False, "Stay must be at least 1 night", None, None, None

    if not is_room_available(room_id, checkin, checkout):
        return False, "Room unavailable for selected dates", None, None, None

    return True, None, checkin, checkout, total_nights


def create_booking_record(conn, customer_id, room_id, booking_data, total_nights=None):
    total_guests = int(booking_data["total_guests"])
    parking = int(booking_data.get("required_car_parking_space") or 0)
    selected_facilities, facility_count, _ = extra_facility_model.summarize_selected_facilities(
        booking_data.get("extra_facility_ids", []),
    )
    booking_model.create_booking(
        conn,
        customer_id=customer_id,
        room_id=room_id,
        meal_plan_id=booking_data["meal_plan_id"],
        market_segment_id=booking_data["market_segment_id"],
        lead_time=booking_data["lead_time"],
        arrival_year=booking_data["arrival_year"],
        arrival_month=booking_data["arrival_month"],
        arrival_date=booking_data["arrival_date"],
        avg_price_per_room=booking_data["avg_price_per_room"],
        no_of_special_requests=facility_count,
        total_nights=total_nights if total_nights is not None else booking_data["total_nights"],
        total_guests=total_guests,
        required_car_parking_space=parking,
        selected_facilities=selected_facilities,
    )


def normalize_payment_booking_data(booking_data, room):
    extra_facility_ids = booking_data.get("extra_facility_ids") or []
    facilities_total = float(booking_data.get("extra_facilities_total") or 0)
    room_price = float(booking_data.get("avg_price_per_room") or room["price_per_night"] or 0)

    normalized = dict(booking_data)
    normalized["room_id"] = int(room["room_id"])
    normalized["room_number"] = room["room_number"]
    normalized["avg_price_per_room"] = room_price
    normalized["extra_facility_ids"] = [int(f_id) for f_id in extra_facility_ids]
    normalized["extra_facilities_total"] = facilities_total
    normalized["required_car_parking_space"] = int(
        normalized.get("required_car_parking_space") or 0
    )
    return normalized, room_price, facilities_total


def build_khalti_payload(booking_data, amount, purchase_order_id, user):
    return {
        "return_url": url_for("payment_success", _external=True),
        "website_url": url_for("landing", _external=True),
        "amount": amount,
        "purchase_order_id": purchase_order_id,
        "purchase_order_name": f"Hotel Room - {booking_data['room_number']}",
        "customer_info": {
            "name": user["name"] if user else "Guest",
            "email": user["email"] if user else "guest@hotel.com",
            "phone": user["phone"] if user and user["phone"] else "9800000000",
        },
    }


def khalti_headers():
    return {
        "Authorization": f"Key {config.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def save_uploaded_file(file_storage, folder_path):
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    save_path = os.path.join(folder_path, filename)
    file_storage.save(save_path)
    return filename


def delete_uploaded_file(folder_path, filename):
    if not filename:
        return

    file_path = os.path.join(folder_path, filename)
    if os.path.exists(file_path):
        os.remove(file_path)


# Session + booking create flow
def clear_pending_payment():
    # Clear temporary booking data saved before payment callback.
    for key in config.PENDING_PAYMENT_SESSION_KEYS:
        session.pop(key, None)


def create_booking_from_session_data(booking_data):
    # Create final booking after successful payment.
    conn = db_model.conn()
    try:
        customer_id = session["user_id"]
        is_valid, error_message, _, _, _ = validate_booking_request(
            booking_data.get("room_id"),
            booking_data,
        )
        if not is_valid:
            print(f"Booking creation failed: {error_message}")
            return False

        create_booking_record(
            conn=conn,
            customer_id=customer_id,
            room_id=booking_data["room_id"],
            booking_data=booking_data,
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Booking creation failed: {e}")
        return False
    finally:
        conn.close()


# Auth decorators
def need_admin(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login", next=request.url))
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def need_user(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login", next=request.url))
        if session.get("is_admin"):
            flash("User access required.", "danger")
            return redirect(url_for("admin_dashboard"))
        return view_func(*args, **kwargs)

    return wrapped

# Flask app + all routes
def build():
    global rf_model, encoders, feature_cols
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static"),
        static_url_path="/static",
    )
    app.secret_key = config.APP_SECRET_KEY

    app.config["UPLOAD_FOLDER"] = os.path.join(config.BASE_DIR, config.UPLOAD_FOLDER)
    app.config["MENU_PLAN_UPLOAD_FOLDER"] = os.path.join(
        config.BASE_DIR, config.MENU_PLAN_UPLOAD_FOLDER
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MENU_PLAN_UPLOAD_FOLDER"], exist_ok=True)

    # Init DB and load prediction model artifacts.
    db_model.init()
    if os.path.exists(config.RF_MODEL_PATH):
        try:
            with open(config.RF_MODEL_PATH, "rb") as file_obj:
                rf_model = pickle.load(file_obj)
        except Exception as e:
            print(f"Could not load RF model: {e}")

    if os.path.exists(config.ENCODERS_PATH):
        try:
            with open(config.ENCODERS_PATH, "rb") as file_obj:
                encoders = pickle.load(file_obj)
        except Exception as e:
            print(f"Could not load encoders: {e}")

    if os.path.exists(config.FEATURE_COLS_PATH):
        try:
            with open(config.FEATURE_COLS_PATH, "rb") as file_obj:
                feature_cols = pickle.load(file_obj)
        except Exception as e:
            print(f"Could not load feature columns: {e}")

    # Public pages
    @app.get("/")
    def landing():
        available_rooms = room_model.list_all_public_rooms()
        return render_template("landing.html", available_rooms=available_rooms)

    @app.get("/view_room/<int:room_id>")
    def view_room(room_id):
        room = room_model.find_public_room(room_id)
        if not room:
            flash("Room not found!", "danger")
            return redirect(url_for("landing"))

        meal_plans = meal_plan_model.list_meal_plans()
        unavailable_ranges = get_unavailable_ranges(room_id)

        return render_template(
            "view_room.html",
            room=room,
            meal_plans=meal_plans,
            unavailable_ranges=unavailable_ranges,
        )

    @app.get("/api/rooms/<int:room_id>/unavailable")
    def room_unavailable_ranges(room_id):
        return jsonify({"ranges": get_unavailable_ranges(room_id)})

    # Authentication routes
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            phone = (request.form.get("phone") or "").strip()
            address = (request.form.get("address") or "").strip()
            password = request.form.get("password") or ""
            confirm_password = request.form.get("confirm_password", "")

            if len(name) < 2:
                flash("Name must be at least 2 characters.", "danger")
                return render_template("register.html")
            if not (email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)):
                flash("Please enter a valid email address.", "danger")
                return render_template("register.html")
            if phone and (not phone.isdigit() or not (7 <= len(phone) <= 15)):
                flash("Phone number must be 7 to 15 digits.", "danger")
                return render_template("register.html")
            if len(address) < 3:
                flash("Address must be at least 3 characters.", "danger")
                return render_template("register.html")
            has_letter = any(ch.isalpha() for ch in password)
            has_digit = any(ch.isdigit() for ch in password)
            if len(password) < 8 or not has_letter or not has_digit:
                flash("Password must be 8+ characters with letters and numbers.", "danger")
                return render_template("register.html")
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return render_template("register.html")

            password_hash = generate_password_hash(password)
            try:
                customer_model.create_customer(name, email, phone, address, password_hash)
                flash("Registration successful! You can now login.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email already exists!", "danger")

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""

            if not (email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)) or not password:
                flash("Please enter a valid email and password.", "danger")
                return render_template("login.html", next=request.args.get("next"))

            user = customer_model.find_by_email(email)
            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["customer_id"]
                session["is_admin"] = bool(user["is_admin"])
                session["user_name"] = user["name"]
                flash("Login successful!", "success")

                next_url = request.args.get("next") or request.form.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect(url_for("admin_dashboard" if user["is_admin"] else "user_dashboard"))

            flash("Invalid credentials", "danger")

        return render_template("login.html", next=request.args.get("next"))

    @app.get("/logout")
    def logout():
        session.clear()
        flash("Logged out", "success")
        return redirect(url_for("landing"))

    # User/customer routes
    @app.get("/user_dashboard")
    @need_user
    def user_dashboard():
        available_rooms = room_model.list_all_public_rooms()
        return render_template("user_dashboard.html", available_rooms=available_rooms)

    @app.route("/user_profile", methods=["GET", "POST"])
    @need_user
    def user_profile():
        user_id = session["user_id"]
        user = customer_model.find_by_id(user_id)

        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            phone = (request.form.get("phone") or "").strip()
            address = (request.form.get("address") or "").strip()
            current_password = request.form.get("current_password") or ""

            if len(name) < 2:
                flash("Name must be at least 2 characters.", "danger")
                return redirect(url_for("user_profile"))
            if phone and (not phone.isdigit() or not (7 <= len(phone) <= 15)):
                flash("Phone number must be 7 to 15 digits.", "danger")
                return redirect(url_for("user_profile"))
            if len(address) < 3:
                flash("Address must be at least 3 characters.", "danger")
                return redirect(url_for("user_profile"))
            if not current_password:
                flash("Current password is required.", "danger")
                return redirect(url_for("user_profile"))
            if not check_password_hash(user["password"], current_password):
                flash("Incorrect current password!", "danger")
                return redirect(url_for("user_profile"))

            customer_model.update_profile(user_id, name, phone, address)
            flash("Profile updated successfully!", "success")
            return redirect(url_for("user_profile"))

        return render_template("user_profile.html", user=user)

    @app.route("/book_room/<int:room_id>", methods=["GET", "POST"])
    @need_user
    def book_room(room_id):
        # Main booking flow: validate dates, guests, and create booking.
        room = room_model.find_room_for_booking(room_id)
        if not room:
            flash("Room not found!", "danger")
            return redirect(url_for("user_dashboard"))

        meal_plans = meal_plan_model.list_meal_plans()
        segments = market_segment_model.list_market_segments()
        extra_facilities = extra_facility_model.list_extra_facilities()

        if request.method == "POST" and request.is_json:
            customer_id = session["user_id"]
            booking_data = request.get_json() or {}
            selected_room_id = int(room["room_id"])

            conn = db_model.conn()
            try:
                is_valid, error_message, _, _, total_nights = validate_booking_request(
                    selected_room_id,
                    booking_data,
                )
                if not is_valid:
                    return jsonify({"success": False, "message": error_message}), 400

                create_booking_record(
                    conn=conn,
                    customer_id=customer_id,
                    room_id=selected_room_id,
                    booking_data=booking_data,
                    total_nights=total_nights,
                )
                conn.commit()
                return jsonify(
                    {
                        "success": True,
                        "message": f"Room {room['room_number']} booked! Pay at reception.",
                    }
                )
            except Exception as e:
                conn.rollback()
                print(f"Offline booking failed: {e}")
                return jsonify({"success": False, "message": "Booking failed."}), 400
            finally:
                conn.close()

        unavailable_ranges = get_unavailable_ranges(room_id)
        return render_template(
            "book_room.html",
            room=room,
            meal_plans=meal_plans,
            segments=segments,
            extra_facilities=extra_facilities,
            unavailable_ranges=unavailable_ranges,
        )

    @app.get("/my_bookings")
    @need_user
    def my_bookings():
        bookings = booking_model.list_user_bookings(session["user_id"])
        return render_template("my_bookings.html", bookings=bookings)

    @app.post("/cancel_booking/<int:booking_id>")
    @need_user
    def cancel_booking(booking_id):
        # User cancels their own booking.
        booking = booking_model.find_user_booking(booking_id, session["user_id"])
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for("my_bookings"))
        if booking["booking_status"] == "Canceled":
            flash("Already canceled.", "info")
            return redirect(url_for("my_bookings"))

        booking_model.update_booking_status(booking_id, "Canceled")
        flash("Booking canceled successfully.", "success")
        return redirect(url_for("my_bookings"))

    # Payment routes (Khalti)
    @app.post("/api/khalti/create-payment")
    @need_user
    def create_khalti_payment():
        # Create payment request for Khalti (online payment).
        if not config.KHALTI_SECRET_KEY:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Online payment is not configured. Set KHALTI_SECRET_KEY and restart the server.",
                    }
                ),
                503,
            )

        data = request.get_json()
        if not data or "booking_data" not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        booking_data = data["booking_data"]
        is_valid, error_message, _, _, total_nights = validate_booking_request(
            booking_data.get("room_id"),
            booking_data,
        )
        if not is_valid:
            return jsonify({"success": False, "error": error_message}), 400

        room = room_model.find_room_for_booking(booking_data.get("room_id"))
        if not room:
            return jsonify({"success": False, "error": "Room not found"}), 400

        booking_data, room_price, facilities_total = normalize_payment_booking_data(booking_data, room)
        expected_total = round((total_nights * room_price) + facilities_total, 2)
        amount = int(expected_total * 100)

        user = customer_model.get_contact_info(session["user_id"])
        purchase_order_id = f"ORDER_{session['user_id']}_{int(datetime.now().timestamp())}"

        payload = build_khalti_payload(booking_data, amount, purchase_order_id, user)
        headers = khalti_headers()

        try:
            response = requests.post(
                f"{config.KHALTI_GATEWAY_URL}/epayment/initiate/",
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                try:
                    khalti_data = response.json()
                except Exception:
                    print(f"Khalti API response not JSON: {response.text}")
                    return jsonify({"success": False, "error": "Invalid payment gateway response"}), 502
                session["pending_booking"] = booking_data
                session["pending_amount"] = expected_total
                session["pending_pidx"] = khalti_data.get("pidx")
                session["purchase_order_id"] = purchase_order_id
                return jsonify(
                    {
                        "success": True,
                        "payment_url": khalti_data.get("payment_url"),
                        "pidx": khalti_data.get("pidx"),
                    }
                )

            try:
                error_data = response.json() if response.text else {}
            except Exception:
                error_data = {}
            return jsonify({"success": False, "error": "Payment initiation failed: Service temporarily unavailable."}), 502

        except requests.exceptions.RequestException as e:
            print(f"Khalti API request error: {e}")
            return jsonify({"success": False, "error": "Unable to connect to payment gateway"}), 500
        except Exception as e:
            print(f"Unexpected error in payment initiation: {e}")
            return jsonify({"success": False, "error": "Payment initiation failed"}), 500

    @app.get("/payment-success")
    @need_user
    def payment_success():
        # Payment callback: verify payment and confirm booking.
        if not config.KHALTI_SECRET_KEY:
            flash("Online payment is not configured. Contact admin.", "danger")
            return redirect(url_for("user_dashboard"))

        pidx = request.args.get("pidx")
        if not pidx:
            flash("Invalid payment response.", "danger")
            return redirect(url_for("user_dashboard"))

        headers = khalti_headers()

        try:
            response = requests.post(
                f"{config.KHALTI_GATEWAY_URL}/epayment/lookup/",
                json={"pidx": pidx},
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                flash("Unable to verify payment. Contact support if charged.", "danger")
                return redirect(url_for("user_dashboard"))

            try:
                payment_data = response.json()
            except Exception:
                print(f"Khalti lookup response not JSON: {response.text}")
                flash("Payment verification error. Contact support if charged.", "danger")
                return redirect(url_for("user_dashboard"))
            payment_status = payment_data.get("status", "").lower()

            if payment_status == "completed":
                booking_data = session.get("pending_booking")
                if not booking_data:
                    clear_pending_payment()
                    flash("Booking data not found. Contact support.", "danger")
                    return redirect(url_for("user_dashboard"))

                if create_booking_from_session_data(booking_data):
                    clear_pending_payment()
                    flash("Payment successful! Booking confirmed.", "success")
                    return redirect(url_for("my_bookings"))

                flash("Payment received but booking failed.", "danger")
                return redirect(url_for("user_dashboard"))

            if payment_status in ["pending", "initiated", "user_initiated"]:
                flash("Payment processing. Please wait and refresh.", "info")
                return redirect(url_for("user_dashboard"))

            flash(f"Payment {payment_status}. Please try again.", "warning")
            clear_pending_payment()
            return redirect(url_for("user_dashboard"))

        except Exception as e:
            print(f"Payment verification error: {e}")
            flash("Error verifying payment. Contact support if charged.", "danger")
            return redirect(url_for("user_dashboard"))

    @app.get("/payment-cancel")
    @need_user
    def payment_cancel():
        # Payment canceled by user.
        clear_pending_payment()
        flash("Payment cancelled. You can try booking again.", "info")
        return redirect(url_for("user_dashboard"))

    # Admin routes
    @app.get("/admin_dashboard")
    @need_admin
    def admin_dashboard():
        return render_template(
            "admin_dashboard.html",
            total_bookings=booking_model.count_bookings(),
            available_rooms=room_model.count_rooms(),
            total_meal_plans=meal_plan_model.count_meal_plans(),
            total_extra_facilities=extra_facility_model.count_extra_facilities(),
            total_users=customer_model.count_non_admin_users(),
            recent_bookings=booking_model.list_recent_bookings(limit=5),
            room_types=room_model.list_room_types_for_dashboard(),
        )

    @app.route("/admin/room_types", methods=["GET", "POST"])
    @need_admin
    def manage_room_types():
        if request.method == "POST":
            name = request.form["room_type_name"]
            desc = request.form.get("description", "")
            price = request.form.get("price_per_night", 0)
            max_guests = int(request.form.get("max_guests") or 2)
            if max_guests < 1:
                max_guests = 2

            img_filename = save_uploaded_file(
                request.files.get("image_file"),
                app.config["UPLOAD_FOLDER"],
            )

            try:
                room_model.create_room_type(name, desc, price, img_filename, max_guests)
                flash("Room type added!", "success")
            except sqlite3.IntegrityError:
                flash("Room type exists!", "danger")

        return render_template("manage_room_types.html", room_types=room_model.list_room_types())

    @app.route("/admin/rooms", methods=["GET", "POST"])
    @need_admin
    def manage_rooms():
        room_types = room_model.list_room_types()
        if request.method == "POST":
            room_number = (request.form.get("room_number") or "").strip()
            room_type_id = int(request.form.get("room_type_id") or 0)
            if not room_number or room_type_id < 1:
                flash("Room number and type are required.", "danger")
            else:
                row = room_model.find_room_type_price(room_type_id)
                default_price = row[0] if row else 0.0
                price_input = request.form.get("price_per_night")
                price = float(price_input) if price_input else default_price
                try:
                    room_model.create_room(room_number, room_type_id, price)
                    flash("Room added successfully!", "success")
                except sqlite3.IntegrityError:
                    flash("A room with this number already exists!", "danger")

        return render_template("manage_rooms.html", rooms=room_model.list_rooms_for_admin(), room_types=room_types)

    @app.route("/admin/manage_meal_plans", methods=["GET", "POST"])
    @need_admin
    def manage_meal_plans():
        if request.method == "POST":
            meal_plan_name = request.form["meal_plan_name"]
            image_filename = save_uploaded_file(
                request.files.get("image_file"),
                app.config["MENU_PLAN_UPLOAD_FOLDER"],
            )

            meal_plan_model.create_meal_plan(meal_plan_name, image_filename)
            flash("Meal plan added!", "success")
            return redirect(url_for("manage_meal_plans"))

        return render_template("manage_meal_plans.html", meal_plans=meal_plan_model.list_meal_plans())

    @app.route("/admin/extra_facilities", methods=["GET", "POST"])
    @need_admin
    def manage_extra_facilities():
        if request.method == "POST":
            facility_name = (request.form.get("facility_name") or "").strip()
            price_raw = (request.form.get("price") or "").strip()

            if not facility_name:
                flash("Facility name is required.", "danger")
                return redirect(url_for("manage_extra_facilities"))

            price = float(price_raw or 0)
            if price < 0:
                price = 0

            try:
                extra_facility_model.create_extra_facility(facility_name, price)
                flash("Extra facility added!", "success")
            except sqlite3.IntegrityError:
                flash("Facility already exists.", "danger")

            return redirect(url_for("manage_extra_facilities"))

        return render_template(
            "manage_extra_facilities.html",
            facilities=extra_facility_model.list_extra_facilities(),
        )

    @app.post("/admin/room_types/delete/<int:room_type_id>")
    @need_admin
    def delete_room_type(room_type_id):
        room_type = room_model.find_room_type_by_id(room_type_id)
        if not room_type:
            flash("Room type not found.", "danger")
            return redirect(url_for("manage_room_types"))

        rooms_count = room_model.count_rooms_using_type(room_type_id)
        if rooms_count > 0:
            flash("Cannot delete this room type because rooms are still assigned to it.", "danger")
            return redirect(url_for("manage_room_types"))

        try:
            delete_uploaded_file(app.config["UPLOAD_FOLDER"], room_type["image_path"])
            room_model.delete_room_type(room_type_id)
            flash("Room type deleted successfully!", "success")
        except sqlite3.IntegrityError as e:
            flash(f"Cannot delete room type: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error deleting room type: {str(e)}", "danger")

        return redirect(url_for("manage_room_types"))

    @app.post("/admin/extra_facilities/delete/<int:facility_id>")
    @need_admin
    def delete_extra_facility(facility_id):
        facility = extra_facility_model.find_extra_facility_by_id(facility_id)
        if not facility:
            flash("Facility not found.", "danger")
            return redirect(url_for("manage_extra_facilities"))

        bookings_count = extra_facility_model.count_bookings_using_extra_facility(facility_id)
        if bookings_count > 0:
            flash(
                "Cannot delete this facility because it is used by existing bookings.",
                "danger",
            )
            return redirect(url_for("manage_extra_facilities"))

        try:
            extra_facility_model.delete_extra_facility(facility_id)
            flash("Facility deleted successfully!", "success")
        except sqlite3.IntegrityError as e:
            flash(f"Cannot delete facility: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error deleting facility: {str(e)}", "danger")

        return redirect(url_for("manage_extra_facilities"))

    @app.post("/admin/delete_meal_plan/<int:meal_id>")
    @need_admin
    def delete_meal_plan(meal_id):
        meal_plan = meal_plan_model.find_meal_plan_by_id(meal_id)
        if not meal_plan:
            flash("Meal plan not found!", "danger")
            return redirect(url_for("manage_meal_plans"))

        bookings_count = meal_plan_model.count_bookings_using_meal_plan(meal_id)
        if bookings_count > 0:
            flash("Cannot delete this meal plan because it is used by existing bookings.", "danger")
            return redirect(url_for("manage_meal_plans"))

        try:
            delete_uploaded_file(app.config["MENU_PLAN_UPLOAD_FOLDER"], meal_plan["image_path"])
            meal_plan_model.delete_meal_plan(meal_id)
            flash("Meal plan deleted successfully!", "success")
        except sqlite3.IntegrityError as e:
            flash(f"Cannot delete meal plan: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error deleting meal plan: {str(e)}", "danger")

        return redirect(url_for("manage_meal_plans"))

    @app.post("/admin/rooms/delete/<int:room_id>")
    @need_admin
    def delete_room(room_id):
        room = room_model.find_room_by_id(room_id)
        if room is None:
            flash("Room not found!", "danger")
            return redirect(url_for("manage_rooms"))
        try:
            room_model.delete_room(room_id)
            flash("Room deleted successfully!", "success")
        except sqlite3.IntegrityError:
            flash("Cannot delete this room because it is used by existing bookings.", "danger")
        return redirect(url_for("manage_rooms"))

    @app.get("/admin/bookings/<int:booking_id>/view")
    @need_admin
    def admin_view_booking_for_hold(booking_id):
        booking = booking_model.get_hold_review(booking_id)
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for("admin_view_bookings"))

        prob = predict_cancellation(booking)
        checkin = datetime(
            int(booking["arrival_year"]),
            int(booking["arrival_month"]),
            int(booking["arrival_date"]),
        ).date()
        checkout = checkin + timedelta(days=int(booking["total_nights"] or 0))

        return render_template(
            "admin_booking_hold_review.html",
            booking=booking,
            cancellation_probability=round(prob * 100, 2),
            risk_level=risk_label(prob),
            checkin=checkin.isoformat(),
            checkout=checkout.isoformat(),
        )

    @app.post("/admin/bookings/<int:booking_id>/hold")
    @need_admin
    def admin_hold_booking(booking_id):
        # Admin puts a booking on hold with a reason.
        hold_reason = (request.form.get("hold_reason") or "").strip()
        if not hold_reason:
            flash("Please provide a reason before putting a booking on hold.", "warning")
            return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

        booking = booking_model.get_hold_action(booking_id)
        is_valid, message, category = can_hold_booking(booking=booking)
        if not is_valid:
            flash(message, category)
            return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

        booking_model.save_hold(booking_id, hold_reason, session.get("user_id"))
        flash(f"Booking #{booking_id} has been placed on hold.", "success")
        return redirect(url_for("admin_view_bookings"))

    @app.post("/admin/bookings/<int:booking_id>/revoke-hold")
    @need_admin
    def admin_revoke_hold(booking_id):
        # Admin removes an existing hold.
        booking = booking_model.get_hold_action(booking_id)
        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for("admin_view_bookings"))
        if int(booking["is_on_hold"] or 0) != 1:
            flash("Booking is not currently on hold.", "info")
            return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

        booking_model.release_hold(booking_id, session.get("user_id"))
        flash(f"Hold revoked for booking #{booking_id}.", "success")
        return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

    @app.get("/admin/bookings")
    @need_admin
    def admin_view_bookings():
        bookings = booking_model.list_admin_bookings()
        booking_preds = []
        for booking in bookings:
            prob = predict_cancellation(booking)
            booking_preds.append(
                {
                    "booking_id": booking["booking_id"],
                    "cancellation_probability": round(prob, 3),
                    "prediction": prediction_label(prob),
                    "risk_level": risk_label(prob),
                }
            )
        return render_template(
            "admin_bookings.html",
            bookings=bookings,
            bookings_combined=zip(bookings, booking_preds),
        )

    @app.get("/admin/users")
    @need_admin
    def admin_view_users():
        users = customer_model.list_users_with_booking_stats()
        return render_template("admin_users.html", users=users)

    @app.post("/admin/users/delete/<int:user_id>")
    @need_admin
    def delete_user(user_id):
        user = customer_model.find_by_id(user_id)
        if not user or int(user["is_admin"] or 0) == 1:
            flash("User not found.", "danger")
            return redirect(url_for("admin_view_users"))

        if int(session.get("user_id") or 0) == user_id:
            flash("You cannot delete your own account while logged in.", "warning")
            return redirect(url_for("admin_view_users"))

        bookings_count = customer_model.count_bookings_for_user(user_id)
        if bookings_count > 0:
            flash("Cannot delete this user because they have booking records.", "danger")
            return redirect(url_for("admin_view_users"))

        try:
            customer_model.delete_user(user_id)
            flash("User deleted successfully!", "success")
        except sqlite3.IntegrityError as e:
            flash(f"Cannot delete user: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error deleting user: {str(e)}", "danger")
        return redirect(url_for("admin_view_users"))

    return app


app = build()


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug_mode)
