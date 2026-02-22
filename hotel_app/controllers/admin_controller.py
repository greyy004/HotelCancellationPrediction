import os
import sqlite3
from datetime import datetime, timedelta

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from hotel_app.models.booking_model import (
    count_bookings,
    get_booking_for_hold_action,
    get_booking_for_hold_review,
    list_admin_bookings_with_hold,
    list_recent_bookings,
    upsert_booking_hold,
)
from hotel_app.models.customer_model import (
    count_non_admin_users,
    list_non_admin_users_with_booking_counts,
)
from hotel_app.models.extra_facility_model import (
    count_extra_facilities,
    insert_extra_facility,
    list_extra_facilities,
)
from hotel_app.models.market_segment_model import (
    insert_market_segment,
    list_market_segments,
)
from hotel_app.models.meal_plan_model import (
    count_bookings_using_meal_plan,
    count_meal_plans,
    delete_meal_plan_by_id,
    get_meal_plan_by_id,
    insert_meal_plan,
    list_meal_plans,
)
from hotel_app.models.room_model import (
    count_rooms,
    delete_room_by_id,
    get_room_by_id,
    get_room_type_price,
    insert_room,
    insert_room_type,
    list_room_types,
    list_room_types_dashboard,
    list_rooms_for_admin,
)
from hotel_app.services.booking_service import allowed_file
from hotel_app.services.hold_service import (
    prediction_label_from_probability,
    risk_level_from_probability,
    validate_hold_request,
)
from hotel_app.services.prediction_service import (
    is_model_available,
    predict_booking_cancellation_probability,
)


def admin_dashboard():
    total_bookings = count_bookings()
    available_rooms = count_rooms()
    total_meal_plans = count_meal_plans()
    total_extra_facilities = count_extra_facilities()
    total_users = count_non_admin_users()
    recent_bookings = list_recent_bookings(limit=5)
    room_types = list_room_types_dashboard()

    return render_template(
        "admin_dashboard.html",
        total_bookings=total_bookings,
        available_rooms=available_rooms,
        total_meal_plans=total_meal_plans,
        total_extra_facilities=total_extra_facilities,
        total_users=total_users,
        recent_bookings=recent_bookings,
        room_types=room_types,
    )


def manage_room_types():
    if request.method == "POST":
        name = request.form["room_type_name"]
        desc = request.form.get("description", "")
        price = request.form.get("price_per_night", 0)
        max_guests_raw = request.form.get("max_guests", 2)

        try:
            max_guests = int(max_guests_raw)
            if max_guests < 1:
                raise ValueError
        except (TypeError, ValueError):
            flash("Max guests must be a whole number greater than 0.", "danger")
            return render_template(
                "manage_room_types.html", room_types=list_room_types()
            )

        file = request.files.get("image_file")
        img_filename = None
        if file and allowed_file(file.filename):
            img_filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], img_filename))

        try:
            insert_room_type(name, desc, price, img_filename, max_guests)
            flash("Room type added!", "success")
        except sqlite3.IntegrityError:
            flash("Room type exists!", "danger")

    return render_template("manage_room_types.html", room_types=list_room_types())


def manage_rooms():
    room_types = list_room_types()

    if request.method == "POST":
        room_number = request.form.get("room_number")
        room_type_id = request.form.get("room_type_id")

        if not room_number or not room_type_id:
            flash("Room number and type are required.", "danger")
        else:
            try:
                room_type_id = int(room_type_id)
            except ValueError:
                flash("Invalid room type selected.", "danger")
            else:
                row = get_room_type_price(room_type_id)
                default_price = row[0] if row else 0.0

                price_input = request.form.get("price_per_night")
                try:
                    price = float(price_input) if price_input else default_price
                except ValueError:
                    price = default_price

                try:
                    insert_room(room_number, room_type_id, price)
                    flash("Room added successfully!", "success")
                except sqlite3.IntegrityError:
                    flash("A room with this number already exists!", "danger")

    rooms = list_rooms_for_admin()
    return render_template("manage_rooms.html", rooms=rooms, room_types=room_types)


def manage_meal_plans():
    if request.method == "POST":
        meal_plan_name = request.form["meal_plan_name"]
        image_file = request.files.get("image_file")

        image_filename = None
        if image_file and image_file.filename != "":
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(
                current_app.config["MENU_PLAN_UPLOAD_FOLDER"], image_filename
            )
            image_file.save(image_path)

        insert_meal_plan(meal_plan_name, image_filename)
        flash("Meal plan added!", "success")
        return redirect(url_for("manage_meal_plans"))

    return render_template("manage_meal_plans.html", meal_plans=list_meal_plans())


def manage_extra_facilities():
    if request.method == "POST":
        facility_name = (request.form.get("facility_name") or "").strip()
        price_raw = (request.form.get("price") or "").strip()

        if not facility_name:
            flash("Facility name is required.", "danger")
            return redirect(url_for("manage_extra_facilities"))

        try:
            price = float(price_raw or 0)
        except ValueError:
            flash("Price must be a valid number.", "danger")
            return redirect(url_for("manage_extra_facilities"))

        if price < 0:
            flash("Price cannot be negative.", "danger")
            return redirect(url_for("manage_extra_facilities"))

        try:
            insert_extra_facility(facility_name, price)
            flash("Extra facility added!", "success")
        except sqlite3.IntegrityError:
            flash("Facility already exists.", "danger")

        return redirect(url_for("manage_extra_facilities"))

    return render_template(
        "manage_extra_facilities.html",
        facilities=list_extra_facilities(),
    )


def delete_meal_plan(meal_id):
    meal_plan = get_meal_plan_by_id(meal_id)
    if not meal_plan:
        flash("Meal plan not found!", "danger")
        return redirect(url_for("manage_meal_plans"))

    bookings_count = count_bookings_using_meal_plan(meal_id)
    if bookings_count > 0:
        flash(
            "Cannot delete this meal plan because it is used by existing bookings.",
            "danger",
        )
        return redirect(url_for("manage_meal_plans"))

    try:
        if meal_plan["image_path"]:
            img_path = os.path.join(
                current_app.config["MENU_PLAN_UPLOAD_FOLDER"], meal_plan["image_path"]
            )
            if os.path.exists(img_path):
                os.remove(img_path)

        delete_meal_plan_by_id(meal_id)
        flash("Meal plan deleted successfully!", "success")
    except sqlite3.IntegrityError as e:
        flash(f"Cannot delete meal plan: {str(e)}", "danger")
    except Exception as e:
        flash(f"Error deleting meal plan: {str(e)}", "danger")

    return redirect(url_for("manage_meal_plans"))


def manage_market_segments():
    if request.method == "POST":
        name = request.form["segment_name"]
        try:
            insert_market_segment(name)
            flash("Segment added!", "success")
        except sqlite3.IntegrityError:
            flash("Segment exists!", "danger")

    return render_template("manage_market_segments.html", segments=list_market_segments())


def delete_room(room_id):
    room = get_room_by_id(room_id)
    if room is None:
        flash("Room not found!", "danger")
        return redirect(url_for("manage_rooms"))

    delete_room_by_id(room_id)
    flash("Room deleted successfully!", "success")
    return redirect(url_for("manage_rooms"))


def admin_view_booking_for_hold(booking_id):
    booking = get_booking_for_hold_review(booking_id)
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("admin_view_bookings"))

    prob = predict_booking_cancellation_probability(booking)
    risk_level = risk_level_from_probability(prob)

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
        risk_level=risk_level,
        checkin=checkin.isoformat(),
        checkout=checkout.isoformat(),
    )


def admin_hold_booking(booking_id):
    hold_reason = (request.form.get("hold_reason") or "").strip()
    if not hold_reason:
        flash("Please provide a reason before putting a booking on hold.", "warning")
        return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

    booking = get_booking_for_hold_action(booking_id)
    prob = predict_booking_cancellation_probability(booking) if booking else 0.0
    is_valid, message, category = validate_hold_request(
        booking=booking,
        model_available=is_model_available(),
        probability=prob,
    )
    if not is_valid:
        flash(message, category)
        return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

    upsert_booking_hold(booking_id, hold_reason, session.get("user_id"))
    flash(f"Booking #{booking_id} has been placed on hold.", "success")
    return redirect(url_for("admin_view_bookings"))


def admin_view_bookings():
    bookings = list_admin_bookings_with_hold()

    booking_preds = []
    for booking in bookings:
        prob = predict_booking_cancellation_probability(booking)
        booking_preds.append(
            {
                "booking_id": booking["booking_id"],
                "cancellation_probability": round(prob, 3),
                "prediction": prediction_label_from_probability(prob),
                "risk_level": risk_level_from_probability(prob),
            }
        )

    return render_template(
        "admin_bookings.html",
        bookings=bookings,
        bookings_combined=zip(bookings, booking_preds),
    )


def admin_view_users():
    users = list_non_admin_users_with_booking_counts()
    return render_template("admin_users.html", users=users)
