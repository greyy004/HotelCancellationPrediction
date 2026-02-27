from flask import flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from hotel_app.models import (
    booking_model,
    customer_model,
    db as db_model,
    extra_facility_model,
    market_segment_model,
    meal_plan_model,
    room_model,
)
from hotel_app.services import booking_service


def valid_profile(name, phone, address, current_password):
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if phone and (not phone.isdigit() or not (7 <= len(phone) <= 15)):
        return "Phone number must be 7 to 15 digits."
    if len(address) < 3:
        return "Address must be at least 3 characters."
    if not current_password:
        return "Current password is required."
    return None


def get_unavailable(room_id):
    return booking_service.get_unavailable(room_id)


def error_json(message):
    return jsonify({"success": False, "message": message}), 400


def dash():
    if session.get("is_admin"):
        flash("User access required.", "danger")
        return redirect(url_for("admin_dashboard"))

    available_rooms = room_model.list_all()
    return render_template("user_dashboard.html", available_rooms=available_rooms)


def profile():
    user_id = session["user_id"]
    user = customer_model.get_by_id(user_id)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()
        current_password = request.form.get("current_password") or ""

        validation_error = valid_profile(name, phone, address, current_password)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("user_profile"))

        if not check_password_hash(user["password"], current_password):
            flash("Incorrect current password!", "danger")
            return redirect(url_for("user_profile"))

        customer_model.update(user_id, name, phone, address)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("user_profile"))

    return render_template("user_profile.html", user=user)


def book(room_id):
    room = room_model.get_booking(room_id)
    if not room:
        flash("Room not found!", "danger")
        return redirect(url_for("user_dashboard"))

    meal_plans = meal_plan_model.list_all()
    segments = market_segment_model.list_all()
    extra_facilities = extra_facility_model.list_all()

    if request.method == "POST" and request.is_json:
        customer_id = session["user_id"]
        booking_data = request.get_json() or {}
        selected_room_id = int(room["room_id"])

        conn = db_model.conn()
        try:
            is_valid_guests, guest_error = booking_service.check_guests(
                selected_room_id,
                booking_data.get("total_guests"),
            )
            if not is_valid_guests:
                return error_json(guest_error)

            total_guests = int(booking_data.get("total_guests"))
            parking = int(booking_data.get("required_car_parking_space") or 0)
            checkin, checkout, total_nights = booking_service.get_stay(booking_data)
            if total_nights <= 0:
                return error_json("Stay must be at least 1 night")

            if not booking_service.is_available(selected_room_id, checkin, checkout):
                return error_json("Room unavailable for selected dates.")

            selected_facilities, facility_count, _ = extra_facility_model.summarize(
                booking_data.get("extra_facility_ids", []),
            )

            booking_model.add(
                conn,
                customer_id=customer_id,
                room_id=selected_room_id,
                meal_plan_id=booking_data["meal_plan_id"],
                market_segment_id=booking_data["market_segment_id"],
                lead_time=booking_data["lead_time"],
                arrival_year=booking_data["arrival_year"],
                arrival_month=booking_data["arrival_month"],
                arrival_date=booking_data["arrival_date"],
                avg_price_per_room=booking_data["avg_price_per_room"],
                no_of_special_requests=facility_count,
                total_nights=total_nights,
                total_guests=total_guests,
                required_car_parking_space=parking,
                selected_facilities=selected_facilities,
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
            return error_json("Booking failed.")
        finally:
            conn.close()

    unavailable_ranges = get_unavailable(room_id)

    return render_template(
        "book_room.html",
        room=room,
        meal_plans=meal_plans,
        segments=segments,
        extra_facilities=extra_facilities,
        unavailable_ranges=unavailable_ranges,
    )


def bookings():
    user_id = session["user_id"]
    bookings = booking_model.list_user(user_id)
    return render_template("my_bookings.html", bookings=bookings)


def cancel(booking_id):
    user_id = session["user_id"]
    booking = booking_model.get_user(booking_id, user_id)

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("my_bookings"))

    if booking["booking_status"] == "Canceled":
        flash("Already canceled.", "info")
        return redirect(url_for("my_bookings"))

    booking_model.set_status(booking_id, "Canceled")
    flash("Booking canceled successfully.", "success")
    return redirect(url_for("my_bookings"))
