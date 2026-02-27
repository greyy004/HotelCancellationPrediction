from datetime import datetime

import requests
from flask import flash, jsonify, redirect, request, session, url_for

from hotel_app.config import KHALTI_GATEWAY_URL, KHALTI_SECRET_KEY
from hotel_app.models import customer_model, room_model
from hotel_app.services import booking_service, payment_service


def error_json(message, status_code=400):
    return jsonify({"success": False, "error": message}), status_code


def data_error(message, status_code=400):
    return None, error_json(message, status_code)


def khalti_headers():
    return {
        "Authorization": f"Key {KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def prep_payment(data):
    if not data or "booking_data" not in data:
        return data_error("Invalid request data", 400)

    booking_data = data["booking_data"]

    try:
        checkin, checkout, total_nights = booking_service.get_stay(booking_data)
    except Exception:
        return data_error("Invalid date selection", 400)

    if total_nights <= 0:
        return data_error("Stay must be at least 1 night", 400)

    if not booking_service.is_available(booking_data["room_id"], checkin, checkout):
        return data_error("Room unavailable for selected dates", 400)

    is_valid_guests, guest_error = booking_service.check_guests(
        booking_data.get("room_id"), booking_data.get("total_guests")
    )
    if not is_valid_guests:
        return data_error(guest_error, 400)

    room = room_model.get_booking(booking_data.get("room_id"))
    if not room:
        return data_error("Room not found", 400)

    extra_facility_ids = booking_data.get("extra_facility_ids") or []
    facility_count = len(extra_facility_ids)
    facilities_total = float(booking_data.get("extra_facilities_total") or 0)
    room_price = float(booking_data.get("avg_price_per_room") or room["price_per_night"] or 0)
    expected_total = round((total_nights * room_price) + facilities_total, 2)

    normalized_booking_data = dict(booking_data)
    normalized_booking_data["room_id"] = int(room["room_id"])
    normalized_booking_data["room_number"] = room["room_number"]
    normalized_booking_data["avg_price_per_room"] = room_price
    normalized_booking_data["extra_facility_ids"] = [int(f_id) for f_id in extra_facility_ids]
    normalized_booking_data["extra_facilities_total"] = facilities_total
    normalized_booking_data["no_of_special_requests"] = facility_count
    normalized_booking_data["required_car_parking_space"] = int(
        booking_data.get("required_car_parking_space") or 0
    )

    return (
        {
            "booking_data": normalized_booking_data,
            "expected_total": expected_total,
            "amount": int(expected_total * 100),
        },
        None,
    )


def go_dashboard(message, category):
    flash(message, category)
    return redirect(url_for("user_dashboard"))


def create():
    if not KHALTI_SECRET_KEY:
        return error_json(
            "Online payment is not configured. Set KHALTI_SECRET_KEY and restart the server.",
            503,
        )

    data = request.get_json()
    payment_data, error_response = prep_payment(data)
    if error_response:
        return error_response

    booking_data = payment_data["booking_data"]
    expected_total = payment_data["expected_total"]
    amount = payment_data["amount"]

    user = customer_model.get_contact(session["user_id"])

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

    try:
        response = requests.post(
            f"{KHALTI_GATEWAY_URL}/epayment/initiate/",
            json=payload,
            headers=khalti_headers(),
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
        return error_json(f"Payment initiation failed: {error_detail}", 400)

    except requests.exceptions.RequestException as e:
        print(f"Khalti API request error: {e}")
        return error_json("Unable to connect to payment gateway", 500)
    except Exception as e:
        print(f"Unexpected error in payment initiation: {e}")
        return error_json("Payment initiation failed", 500)


def success():
    if not KHALTI_SECRET_KEY:
        return go_dashboard(
            "Online payment is not configured. Contact admin.", "danger"
        )

    pidx = request.args.get("pidx")

    if not pidx:
        return go_dashboard("Invalid payment response.", "danger")

    try:
        response = requests.post(
            f"{KHALTI_GATEWAY_URL}/epayment/lookup/",
            json={"pidx": pidx},
            headers=khalti_headers(),
            timeout=30,
        )

        if response.status_code != 200:
            return go_dashboard(
                "Unable to verify payment. Contact support if charged.",
                "danger",
            )

        payment_data = response.json()
        payment_status = payment_data.get("status", "").lower()

        if payment_status == "completed":
            booking_data = session.get("pending_booking")
            if not booking_data:
                payment_service.clear_pending()
                return go_dashboard(
                    "Booking data not found. Contact support.",
                    "danger",
                )

            if payment_service.create_from_session(booking_data):
                payment_service.clear_pending()
                flash("Payment successful! Booking confirmed.", "success")
                return redirect(url_for("my_bookings"))

            return go_dashboard(
                "Payment received but booking failed.",
                "danger",
            )

        if payment_status in ["pending", "initiated", "user_initiated"]:
            return go_dashboard(
                "Payment processing. Please wait and refresh.",
                "info",
            )

        flash(f"Payment {payment_status}. Please try again.", "warning")
        payment_service.clear_pending()
        return redirect(url_for("user_dashboard"))

    except Exception as e:
        print(f"Payment verification error: {e}")
        return go_dashboard(
            "Error verifying payment. Contact support if charged.",
            "danger",
        )


def cancel():
    payment_service.clear_pending()
    flash("Payment cancelled. You can try booking again.", "info")
    return redirect(url_for("user_dashboard"))
