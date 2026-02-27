import os
import sqlite3
from datetime import datetime, timedelta

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from hotel_app.models import (
    booking_model,
    customer_model,
    extra_facility_model,
    market_segment_model,
    meal_plan_model,
    room_model,
)
from hotel_app.services import hold_service, prediction_service


def dash():
    total_bookings = booking_model.count()
    available_rooms = room_model.count()
    total_meal_plans = meal_plan_model.count()
    total_extra_facilities = extra_facility_model.count()
    total_users = customer_model.count_users()
    recent_bookings = booking_model.list_recent(limit=5)
    room_types = room_model.list_types_dash()

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


def types():
    if request.method == "POST":
        name = request.form["room_type_name"]
        desc = request.form.get("description", "")
        price = request.form.get("price_per_night", 0)
        max_guests = int(request.form.get("max_guests") or 2)
        if max_guests < 1:
            max_guests = 2

        file = request.files.get("image_file")
        img_filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            img_filename = filename

        try:
            room_model.add_type(name, desc, price, img_filename, max_guests)
            flash("Room type added!", "success")
        except sqlite3.IntegrityError:
            flash("Room type exists!", "danger")

    return render_template("manage_room_types.html", room_types=room_model.list_types())


def rooms():
    room_types = room_model.list_types()

    if request.method == "POST":
        room_number = (request.form.get("room_number") or "").strip()
        room_type_id = int(request.form.get("room_type_id") or 0)

        if not room_number or room_type_id < 1:
            flash("Room number and type are required.", "danger")
        else:
            row = room_model.get_type_price(room_type_id)
            default_price = row[0] if row else 0.0

            price_input = request.form.get("price_per_night")
            price = float(price_input) if price_input else default_price

            try:
                room_model.add(room_number, room_type_id, price)
                flash("Room added successfully!", "success")
            except sqlite3.IntegrityError:
                flash("A room with this number already exists!", "danger")

    rooms = room_model.list_admin()
    return render_template("manage_rooms.html", rooms=rooms, room_types=room_types)


def meals():
    if request.method == "POST":
        meal_plan_name = request.form["meal_plan_name"]
        image_file = request.files.get("image_file")

        image_filename = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(
                current_app.config["MENU_PLAN_UPLOAD_FOLDER"], filename
            )
            image_file.save(save_path)
            image_filename = filename

        meal_plan_model.add(meal_plan_name, image_filename)
        flash("Meal plan added!", "success")
        return redirect(url_for("manage_meal_plans"))

    return render_template("manage_meal_plans.html", meal_plans=meal_plan_model.list_all())


def extras():
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
            extra_facility_model.add(facility_name, price)
            flash("Extra facility added!", "success")
        except sqlite3.IntegrityError:
            flash("Facility already exists.", "danger")

        return redirect(url_for("manage_extra_facilities"))

    return render_template(
        "manage_extra_facilities.html",
        facilities=extra_facility_model.list_all(),
    )


def del_meal(meal_id):
    meal_plan = meal_plan_model.get_by_id(meal_id)
    if not meal_plan:
        flash("Meal plan not found!", "danger")
        return redirect(url_for("manage_meal_plans"))

    bookings_count = meal_plan_model.used(meal_id)
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

        meal_plan_model.remove(meal_id)
        flash("Meal plan deleted successfully!", "success")
    except sqlite3.IntegrityError as e:
        flash(f"Cannot delete meal plan: {str(e)}", "danger")
    except Exception as e:
        flash(f"Error deleting meal plan: {str(e)}", "danger")

    return redirect(url_for("manage_meal_plans"))


def segments():
    if request.method == "POST":
        name = request.form["segment_name"]
        try:
            market_segment_model.add(name)
            flash("Segment added!", "success")
        except sqlite3.IntegrityError:
            flash("Segment exists!", "danger")

    return render_template(
        "manage_market_segments.html",
        segments=market_segment_model.list_all(),
    )


def del_room(room_id):
    room = room_model.get_by_id(room_id)
    if room is None:
        flash("Room not found!", "danger")
        return redirect(url_for("manage_rooms"))

    room_model.remove(room_id)
    flash("Room deleted successfully!", "success")
    return redirect(url_for("manage_rooms"))


def hold_view(booking_id):
    booking = booking_model.get_hold_review(booking_id)
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("admin_view_bookings"))

    prob = prediction_service.predict(booking)
    risk_level = hold_service.risk(prob)

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


def hold_set(booking_id):
    hold_reason = (request.form.get("hold_reason") or "").strip()
    if not hold_reason:
        flash("Please provide a reason before putting a booking on hold.", "warning")
        return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

    booking = booking_model.get_hold_action(booking_id)
    prob = prediction_service.predict(booking) if booking else 0.0
    is_valid, message, category = hold_service.can_hold(
        booking=booking,
        probability=prob,
    )
    if not is_valid:
        flash(message, category)
        return redirect(url_for("admin_view_booking_for_hold", booking_id=booking_id))

    booking_model.save_hold(booking_id, hold_reason, session.get("user_id"))
    flash(f"Booking #{booking_id} has been placed on hold.", "success")
    return redirect(url_for("admin_view_bookings"))


def bookings():
    bookings = booking_model.list_admin()

    booking_preds = []
    for booking in bookings:
        prob = prediction_service.predict(booking)
        booking_preds.append(
            {
                "booking_id": booking["booking_id"],
                "cancellation_probability": round(prob, 3),
                "prediction": hold_service.label(prob),
                "risk_level": hold_service.risk(prob),
            }
        )

    return render_template(
        "admin_bookings.html",
        bookings=bookings,
        bookings_combined=zip(bookings, booking_preds),
    )


def users():
    users = customer_model.list_users()
    return render_template("admin_users.html", users=users)

