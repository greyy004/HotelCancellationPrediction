from flask import session

from hotel_app.config import PENDING_PAYMENT_SESSION_KEYS
from hotel_app.models.booking_model import insert_booking
from hotel_app.models.db import get_db_connection
from hotel_app.models.extra_facility_model import summarize_selected_facilities
from hotel_app.services.booking_service import validate_guest_limit


def clear_pending_payment_session():
    for key in PENDING_PAYMENT_SESSION_KEYS:
        session.pop(key, None)


def create_booking_from_session(booking_data):
    conn = get_db_connection()
    try:
        customer_id = session["user_id"]
        is_valid_guests, guest_error = validate_guest_limit(
            booking_data.get("room_id"),
            booking_data.get("total_guests"),
            conn=conn,
        )
        if not is_valid_guests:
            print(f"Booking creation failed: {guest_error}")
            return False

        total_guests = int(booking_data["total_guests"])
        selected_facilities, facility_count, _ = summarize_selected_facilities(
            booking_data.get("extra_facility_ids", []),
            conn=conn,
        )
        insert_booking(
            conn,
            customer_id=customer_id,
            room_id=booking_data["room_id"],
            meal_plan_id=booking_data["meal_plan_id"],
            market_segment_id=booking_data["market_segment_id"],
            lead_time=booking_data["lead_time"],
            arrival_year=booking_data["arrival_year"],
            arrival_month=booking_data["arrival_month"],
            arrival_date=booking_data["arrival_date"],
            avg_price_per_room=booking_data["avg_price_per_room"],
            no_of_special_requests=facility_count,
            total_nights=booking_data["total_nights"],
            total_guests=total_guests,
            selected_facilities=selected_facilities,
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Booking creation failed: {e}")
        return False
    finally:
        conn.close()
