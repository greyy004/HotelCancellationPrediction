from datetime import datetime

import requests
from flask import flash, jsonify, redirect, request, session, url_for

from hotel_app.config import KHALTI_GATEWAY_URL, KHALTI_SECRET_KEY
from hotel_app.models.customer_model import get_customer_contact
from hotel_app.models.extra_facility_model import summarize_selected_facilities
from hotel_app.models.room_model import get_room_for_booking
from hotel_app.services.booking_service import (
    booking_window_from_payload,
    is_room_available,
    validate_guest_limit,
)
from hotel_app.services.payment_service import (
    clear_pending_payment_session,
    create_booking_from_session,
)


def create_khalti_payment():
    if not KHALTI_SECRET_KEY:
        return (
            jsonify(
                {
                    "success": False,
                    "error": (
                        "Online payment is not configured. "
                        "Set KHALTI_SECRET_KEY and restart the server."
                    ),
                }
            ),
            503,
        )

    data = request.get_json()

    if not data or "amount" not in data or "booking_data" not in data:
        return jsonify({"success": False, "error": "Invalid request data"}), 400

    try:
        checkin, checkout, total_nights = booking_window_from_payload(data["booking_data"])
    except Exception:
        return jsonify({"success": False, "error": "Invalid date selection"}), 400

    if total_nights <= 0:
        return jsonify({"success": False, "error": "Stay must be at least 1 night"}), 400

    if not is_room_available(data["booking_data"]["room_id"], checkin, checkout):
        return (
            jsonify({"success": False, "error": "Room unavailable for selected dates"}),
            400,
        )

    is_valid_guests, guest_error = validate_guest_limit(
        data["booking_data"].get("room_id"), data["booking_data"].get("total_guests")
    )
    if not is_valid_guests:
        return jsonify({"success": False, "error": guest_error}), 400

    room = get_room_for_booking(data["booking_data"].get("room_id"))
    if not room:
        return jsonify({"success": False, "error": "Room not found"}), 400

    selected_facilities, facility_count, facilities_total = summarize_selected_facilities(
        data["booking_data"].get("extra_facility_ids", [])
    )
    room_price = float(room["price_per_night"] or 0)
    expected_total = round((total_nights * room_price) + facilities_total, 2)

    try:
        submitted_total = round(float(data["amount"]), 2)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid payment amount"}), 400

    if abs(submitted_total - expected_total) > 0.01:
        return jsonify({"success": False, "error": "Booking amount mismatch"}), 400

    booking_data = data["booking_data"]
    booking_data["room_id"] = int(room["room_id"])
    booking_data["room_number"] = room["room_number"]
    booking_data["avg_price_per_room"] = room_price
    booking_data["extra_facility_ids"] = [int(f["facility_id"]) for f in selected_facilities]
    booking_data["extra_facilities_total"] = facilities_total
    booking_data["no_of_special_requests"] = facility_count

    amount = int(expected_total * 100)
    user = get_customer_contact(session["user_id"])

    purchase_order_id = f"ORDER_{session['user_id']}_{int(datetime.now().timestamp())}"

    payload = {
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

    headers = {
        "Authorization": f"Key {KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{KHALTI_GATEWAY_URL}/epayment/initiate/",
            json=payload,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            payment_data = response.json()

            session["pending_booking"] = booking_data
            session["pending_amount"] = expected_total
            session["pending_pidx"] = payment_data.get("pidx")
            session["purchase_order_id"] = purchase_order_id

            return jsonify(
                {
                    "success": True,
                    "payment_url": payment_data.get("payment_url"),
                    "pidx": payment_data.get("pidx"),
                }
            )

        error_data = response.json() if response.text else {}
        error_detail = error_data.get(
            "detail", error_data.get("error_message", "Unknown error")
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Payment initiation failed: {error_detail}",
                }
            ),
            400,
        )

    except requests.exceptions.RequestException as e:
        print(f"Khalti API request error: {e}")
        return (
            jsonify({"success": False, "error": "Unable to connect to payment gateway"}),
            500,
        )
    except Exception as e:
        print(f"Unexpected error in payment initiation: {e}")
        return jsonify({"success": False, "error": "Payment initiation failed"}), 500


def payment_success():
    if not KHALTI_SECRET_KEY:
        flash("Online payment is not configured. Contact admin.", "danger")
        return redirect(url_for("user_dashboard"))

    pidx = request.args.get("pidx")

    if not pidx:
        flash("Invalid payment response.", "danger")
        return redirect(url_for("user_dashboard"))

    if pidx != session.get("pending_pidx"):
        flash("Payment session mismatch. Please try again.", "danger")
        return redirect(url_for("user_dashboard"))

    headers = {
        "Authorization": f"Key {KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{KHALTI_GATEWAY_URL}/epayment/lookup/",
            json={"pidx": pidx},
            headers=headers,
            timeout=30,
        )

        if response.status_code != 200:
            flash("Unable to verify payment. Contact support if charged.", "danger")
            return redirect(url_for("user_dashboard"))

        payment_data = response.json()
        payment_status = payment_data.get("status", "").lower()
        lookup_purchase_order = payment_data.get("purchase_order_id")

        if payment_status == "completed":
            booking_data = session.get("pending_booking")
            expected_amount = int(float(session.get("pending_amount", 0)) * 100)
            actual_amount = payment_data.get("total_amount", 0)
            expected_po = session.get("purchase_order_id")

            if not booking_data:
                flash("Booking data not found. Contact support.", "danger")
                return redirect(url_for("user_dashboard"))

            try:
                checkin, checkout, total_nights = booking_window_from_payload(booking_data)
                if total_nights <= 0:
                    flash("Invalid stay length. Please rebook.", "danger")
                    return redirect(url_for("user_dashboard"))

                if not is_room_available(booking_data["room_id"], checkin, checkout):
                    flash(
                        "Selected room is no longer available for those dates.",
                        "danger",
                    )
                    clear_pending_payment_session()
                    return redirect(url_for("user_dashboard"))

                is_valid_guests, guest_error = validate_guest_limit(
                    booking_data.get("room_id"), booking_data.get("total_guests")
                )
                if not is_valid_guests:
                    flash(guest_error, "danger")
                    clear_pending_payment_session()
                    return redirect(url_for("user_dashboard"))

            except Exception:
                flash("Invalid booking dates. Please rebook.", "danger")
                clear_pending_payment_session()
                return redirect(url_for("user_dashboard"))

            if expected_po and lookup_purchase_order and expected_po != lookup_purchase_order:
                flash("Payment reference mismatch. Contact support.", "danger")
                clear_pending_payment_session()
                return redirect(url_for("user_dashboard"))

            if abs(actual_amount - expected_amount) > 1:
                flash(
                    f"Payment amount mismatch. Contact support with ref: {pidx}",
                    "danger",
                )
                return redirect(url_for("user_dashboard"))

            if create_booking_from_session(booking_data):
                clear_pending_payment_session()
                flash("Payment successful! Booking confirmed.", "success")
                return redirect(url_for("my_bookings"))

            flash("Payment received but booking failed.", "danger")
            return redirect(url_for("user_dashboard"))

        if payment_status in ["pending", "initiated", "user_initiated"]:
            flash("Payment processing. Please wait and refresh.", "info")
            return redirect(url_for("user_dashboard"))

        flash(f"Payment {payment_status}. Please try again.", "warning")
        clear_pending_payment_session()
        return redirect(url_for("user_dashboard"))

    except Exception as e:
        print(f"Payment verification error: {e}")
        flash("Error verifying payment. Contact support if charged.", "danger")
        return redirect(url_for("user_dashboard"))


def payment_cancel():
    clear_pending_payment_session()
    flash("Payment cancelled. You can try booking again.", "info")
    return redirect(url_for("user_dashboard"))
