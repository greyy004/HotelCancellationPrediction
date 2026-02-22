from hotel_app.controllers import public_controller


def register_public_routes(app):
    app.add_url_rule(
        "/api/rooms/<int:room_id>/unavailable",
        endpoint="room_unavailable_ranges",
        view_func=public_controller.room_unavailable_ranges,
        methods=["GET"],
    )
    app.add_url_rule("/", endpoint="landing", view_func=public_controller.landing)
    app.add_url_rule(
        "/view_room/<int:room_id>",
        endpoint="view_room",
        view_func=public_controller.view_room,
    )
