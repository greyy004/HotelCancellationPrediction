from flask import flash, jsonify, redirect, render_template, url_for

from hotel_app.models.db import get_db_connection
from hotel_app.models.meal_plan_model import list_meal_plans
from hotel_app.models.room_model import get_room_for_public, list_rooms_with_types
from hotel_app.services.booking_service import get_unavailable_ranges_for_room


def room_unavailable_ranges(room_id):
    conn = get_db_connection()
    ranges = get_unavailable_ranges_for_room(conn, room_id)
    conn.close()
    return jsonify({"ranges": ranges})


def landing():
    available_rooms = list_rooms_with_types()
    return render_template("landing.html", available_rooms=available_rooms)


def view_room(room_id):
    room = get_room_for_public(room_id)
    if not room:
        flash("Room not found!", "danger")
        return redirect(url_for("landing"))

    meal_plans = list_meal_plans()

    conn = get_db_connection()
    unavailable_ranges = get_unavailable_ranges_for_room(conn, room_id)
    conn.close()

    return render_template(
        "view_room.html",
        room=room,
        meal_plans=meal_plans,
        unavailable_ranges=unavailable_ranges,
    )
