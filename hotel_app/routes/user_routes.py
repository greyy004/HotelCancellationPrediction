from hotel_app.controllers import user_controller
from hotel_app.middleware.auth import need_login


def reg(app):
    routes = [
        ("/user_dashboard", "user_dashboard", user_controller.dash, None),
        (
            "/user_profile",
            "user_profile",
            user_controller.profile,
            ["GET", "POST"],
        ),
        ("/book_room/<int:room_id>", "book_room", user_controller.book, ["GET", "POST"]),
        ("/my_bookings", "my_bookings", user_controller.bookings, None),
        (
            "/cancel_booking/<int:booking_id>",
            "cancel_booking",
            user_controller.cancel,
            ["POST"],
        ),
    ]
    for rule, endpoint, view_func, methods in routes:
        app.add_url_rule(
            rule,
            endpoint=endpoint,
            view_func=need_login(view_func),
            methods=methods,
        )
