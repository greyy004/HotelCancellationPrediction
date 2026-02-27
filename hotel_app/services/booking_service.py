from datetime import datetime, timedelta

from hotel_app.models import booking_model, room_model


def check_guests(room_id, total_guests):
    total_guests_int = int(total_guests or 0)

    if total_guests_int < 1:
        return False, "At least 1 guest is required."

    room = room_model.get_max_guests(room_id)

    if not room:
        return False, "Room not found."

    max_guests = int(room["max_guests"] or 2)
    if total_guests_int > max_guests:
        return False, f"This room allows a maximum of {max_guests} guests."
    return True, None


def get_stay(data):
    total_nights = int(data.get("total_nights") or 0)
    checkin = datetime(
        int(data["arrival_year"]), int(data["arrival_month"]), int(data["arrival_date"])
    ).date()
    checkout = checkin + timedelta(days=total_nights)
    return checkin, checkout, total_nights


def get_stay_row(row):
    total_nights = int(row["total_nights"] or 0)
    checkin = datetime(row["arrival_year"], row["arrival_month"], row["arrival_date"]).date()
    checkout = checkin + timedelta(days=total_nights)
    return checkin, checkout, total_nights


def get_unavailable(room_id):
    rows = booking_model.list_active_windows(room_id)
    ranges = []
    for row in rows:
        start, end, nights = get_stay_row(row)
        if nights > 0:
            ranges.append({"start": start.isoformat(), "end": end.isoformat()})
    return ranges


def is_available(room_id, checkin, checkout):
    rows = booking_model.list_active_room(room_id)
    for row in rows:
        existing_checkin, existing_checkout, _ = get_stay_row(row)
        if checkin < existing_checkout and checkout > existing_checkin:
            return False
    return True
