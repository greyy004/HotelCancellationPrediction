from hotel_app.controllers import user_controller
from hotel_app.middleware.auth import login_required


def register_user_routes(app):
    app.add_url_rule(
        "/user_dashboard",
        endpoint="user_dashboard",
        view_func=login_required(user_controller.user_dashboard),
    )
    app.add_url_rule(
        "/user_profile",
        endpoint="user_profile",
        view_func=login_required(user_controller.user_profile),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/book_room/<int:room_id>",
        endpoint="book_room",
        view_func=login_required(user_controller.book_room),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/my_bookings",
        endpoint="my_bookings",
        view_func=login_required(user_controller.my_bookings),
    )
    app.add_url_rule(
        "/cancel_booking/<int:booking_id>",
        endpoint="cancel_booking",
        view_func=login_required(user_controller.cancel_booking),
        methods=["POST"],
    )
