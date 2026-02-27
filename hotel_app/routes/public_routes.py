from hotel_app.controllers import public_controller


def reg(app):
    routes = [
        (
            "/api/rooms/<int:room_id>/unavailable",
            "room_unavailable_ranges",
            public_controller.ranges,
            ["GET"],
        ),
        ("/", "landing", public_controller.home, None),
        ("/view_room/<int:room_id>", "view_room", public_controller.room, None),
    ]
    for rule, endpoint, view_func, methods in routes:
        app.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)
