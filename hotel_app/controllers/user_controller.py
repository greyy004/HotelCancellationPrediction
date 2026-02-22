from flask import flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from hotel_app.models.booking_model import (
    get_user_booking,
    insert_booking,
    list_user_bookings_with_hold,
    set_booking_status,
)
from hotel_app.models.customer_model import get_customer_by_id, update_customer_profile
from hotel_app.models.db import get_db_connection
from hotel_app.models.extra_facility_model import (
    list_extra_facilities,
    summarize_selected_facilities,
)
from hotel_app.models.market_segment_model import list_market_segments
from hotel_app.models.meal_plan_model import list_meal_plans
from hotel_app.models.room_model import get_room_for_booking, list_rooms_with_types
from hotel_app.services.booking_service import (
    booking_window_from_payload,
    get_unavailable_ranges_for_room,
    is_room_available,
    validate_guest_limit,
)


def user_dashboard():
    if session.get("is_admin"):
        flash("User access required.", "danger")
        return redirect(url_for("admin_dashboard"))

    available_rooms = list_rooms_with_types()
    return render_template("user_dashboard.html", available_rooms=available_rooms)


def user_profile():
    user_id = session["user_id"]
    user = get_customer_by_id(user_id)

    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        current_password = request.form["current_password"]

        if not check_password_hash(user["password"], current_password):
            flash("Incorrect current password!", "danger")
            return redirect(url_for("user_profile"))

        update_customer_profile(user_id, name, phone, address)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("user_profile"))

    return render_template("user_profile.html", user=user)


def book_room(room_id):
    room = get_room_for_booking(room_id)
    if not room:
        flash("Room not found!", "danger")
        return redirect(url_for("user_dashboard"))

    meal_plans = list_meal_plans()
    segments = list_market_segments()
    extra_facilities = list_extra_facilities()

    if request.method == "POST" and request.is_json:
        customer_id = session["user_id"]
        booking_data = request.get_json()
        selected_room_id = int(room["room_id"])

        conn = get_db_connection()
        try:
            is_valid_guests, guest_error = validate_guest_limit(
                selected_room_id,
                booking_data.get("total_guests"),
                conn=conn,
            )
            if not is_valid_guests:
                return jsonify({"success": False, "message": guest_error}), 400

            total_guests = int(booking_data.get("total_guests"))
            checkin, checkout, total_nights = booking_window_from_payload(booking_data)
            if total_nights <= 0:
                raise ValueError("Stay must be at least 1 night")

            if not is_room_available(selected_room_id, checkin, checkout):
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Room unavailable for selected dates.",
                        }
                    ),
                    400,
                )

            selected_facilities, facility_count, _ = summarize_selected_facilities(
                booking_data.get("extra_facility_ids", []),
                conn=conn,
            )

            insert_booking(
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
            return jsonify({"success": False, "message": "Booking failed."}), 400
        finally:
            conn.close()

    conn = get_db_connection()
    unavailable_ranges = get_unavailable_ranges_for_room(conn, room_id)
    conn.close()

    return render_template(
        "book_room.html",
        room=room,
        meal_plans=meal_plans,
        segments=segments,
        extra_facilities=extra_facilities,
        unavailable_ranges=unavailable_ranges,
    )


def my_bookings():
    user_id = session["user_id"]
    bookings = list_user_bookings_with_hold(user_id)
    return render_template("my_bookings.html", bookings=bookings)


def cancel_booking(booking_id):
    user_id = session["user_id"]
    booking = get_user_booking(booking_id, user_id)

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("my_bookings"))

    if booking["booking_status"] == "Canceled":
        flash("Already canceled.", "info")
        return redirect(url_for("my_bookings"))

    set_booking_status(booking_id, "Canceled")
    flash("Booking canceled successfully.", "success")
    return redirect(url_for("my_bookings"))
