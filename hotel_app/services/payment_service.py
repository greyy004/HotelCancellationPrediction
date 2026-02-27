from flask import session

from hotel_app.config import PENDING_PAYMENT_SESSION_KEYS
from hotel_app.models import booking_model, db as db_model, extra_facility_model
from hotel_app.services import booking_service


def clear_pending():
    for key in PENDING_PAYMENT_SESSION_KEYS:
        session.pop(key, None)


def create_from_session(booking_data):
    conn = db_model.conn()
    try:
        customer_id = session["user_id"]
        is_valid_guests, guest_error = booking_service.check_guests(
            booking_data.get("room_id"),
            booking_data.get("total_guests"),
        )
        if not is_valid_guests:
            print(f"Booking creation failed: {guest_error}")
            return False

        total_guests = int(booking_data["total_guests"])
        parking = int(booking_data.get("required_car_parking_space") or 0)
        selected_facilities, facility_count, _ = extra_facility_model.summarize(
            booking_data.get("extra_facility_ids", []),
        )
        booking_model.add(
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
            required_car_parking_space=parking,
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
