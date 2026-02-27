from flask import flash, jsonify, redirect, render_template, url_for

from hotel_app.models import meal_plan_model, room_model
from hotel_app.services import booking_service


def get_unavailable(room_id):
    return booking_service.get_unavailable(room_id)


def ranges(room_id):
    return jsonify({"ranges": get_unavailable(room_id)})


def home():
    available_rooms = room_model.list_all()
    return render_template("landing.html", available_rooms=available_rooms)


def room(room_id):
    room = room_model.get_public(room_id)
    if not room:
        flash("Room not found!", "danger")
        return redirect(url_for("landing"))

    meal_plans = meal_plan_model.list_all()
    unavailable_ranges = get_unavailable(room_id)

    return render_template(
        "view_room.html",
        room=room,
        meal_plans=meal_plans,
        unavailable_ranges=unavailable_ranges,
    )
