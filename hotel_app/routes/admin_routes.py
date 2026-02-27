from hotel_app.controllers import admin_controller
from hotel_app.middleware.auth import need_admin


def reg(app):
    routes = [
        ("/admin_dashboard", "admin_dashboard", admin_controller.dash, None),
        (
            "/admin/room_types",
            "manage_room_types",
            admin_controller.types,
            ["GET", "POST"],
        ),
        (
            "/admin/rooms",
            "manage_rooms",
            admin_controller.rooms,
            ["GET", "POST"],
        ),
        (
            "/admin/manage_meal_plans",
            "manage_meal_plans",
            admin_controller.meals,
            ["GET", "POST"],
        ),
        (
            "/admin/extra_facilities",
            "manage_extra_facilities",
            admin_controller.extras,
            ["GET", "POST"],
        ),
        (
            "/admin/delete_meal_plan/<int:meal_id>",
            "delete_meal_plan",
            admin_controller.del_meal,
            ["POST"],
        ),
        (
            "/admin/market_segments",
            "manage_market_segments",
            admin_controller.segments,
            ["GET", "POST"],
        ),
        (
            "/admin/rooms/delete/<int:room_id>",
            "delete_room",
            admin_controller.del_room,
            ["POST"],
        ),
        (
            "/admin/bookings/<int:booking_id>/view",
            "admin_view_booking_for_hold",
            admin_controller.hold_view,
            None,
        ),
        (
            "/admin/bookings/<int:booking_id>/hold",
            "admin_hold_booking",
            admin_controller.hold_set,
            ["POST"],
        ),
        (
            "/admin/bookings",
            "admin_view_bookings",
            admin_controller.bookings,
            None,
        ),
        ("/admin/users", "admin_view_users", admin_controller.users, None),
    ]
    for rule, endpoint, view_func, methods in routes:
        app.add_url_rule(
            rule,
            endpoint=endpoint,
            view_func=need_admin(view_func),
            methods=methods,
        )
