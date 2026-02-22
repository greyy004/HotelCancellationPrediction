from datetime import datetime, timedelta

from hotel_app.config import ALLOWED_EXTENSIONS
from hotel_app.models.booking_model import (
    list_active_booking_windows,
    list_active_bookings_for_room,
)
from hotel_app.models.db import get_db_connection
from hotel_app.models.room_model import get_room_max_guests


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_guest_limit(room_id, total_guests, conn=None):
    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    try:
        total_guests_int = int(total_guests)
    except (TypeError, ValueError):
        if owns_conn:
            conn.close()
        return False, "Invalid total guests value."

    if total_guests_int < 1:
        if owns_conn:
            conn.close()
        return False, "At least 1 guest is required."

    room = get_room_max_guests(room_id, conn=conn)

    if owns_conn:
        conn.close()

    if not room:
        return False, "Room not found."

    max_guests = int(room["max_guests"] or 2)
    if total_guests_int > max_guests:
        return False, f"This room allows a maximum of {max_guests} guests."
    return True, None


def compute_total_nights_from_row(row):
    total_nights = row["total_nights"]
    if total_nights is not None:
        return int(total_nights)
    return 0


def booking_window_from_payload(data):
    total_nights = int(data.get("total_nights") or 0)
    checkin = datetime(
        int(data["arrival_year"]), int(data["arrival_month"]), int(data["arrival_date"])
    ).date()
    checkout = checkin + timedelta(days=total_nights)
    return checkin, checkout, total_nights


def booking_window_from_row(row):
    total_nights = compute_total_nights_from_row(row)
    checkin = datetime(row["arrival_year"], row["arrival_month"], row["arrival_date"]).date()
    checkout = checkin + timedelta(days=total_nights)
    return checkin, checkout, total_nights


def get_unavailable_ranges_for_room(conn, room_id):
    rows = list_active_booking_windows(room_id, conn=conn)

    ranges = []
    for row in rows:
        start, end, total_nights = booking_window_from_row(row)
        if total_nights <= 0:
            continue
        ranges.append({"start": start.isoformat(), "end": end.isoformat()})
    return ranges


def is_room_available(room_id, checkin, checkout):
    rows = list_active_bookings_for_room(room_id)
    for row in rows:
        existing_checkin, existing_checkout, _ = booking_window_from_row(row)
        if checkin < existing_checkout and checkout > existing_checkin:
            return False
    return True
