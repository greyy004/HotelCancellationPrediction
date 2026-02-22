from hotel_app.controllers import admin_controller
from hotel_app.middleware.auth import admin_required


def register_admin_routes(app):
    app.add_url_rule(
        "/admin_dashboard",
        endpoint="admin_dashboard",
        view_func=admin_required(admin_controller.admin_dashboard),
    )
    app.add_url_rule(
        "/admin/room_types",
        endpoint="manage_room_types",
        view_func=admin_required(admin_controller.manage_room_types),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/admin/rooms",
        endpoint="manage_rooms",
        view_func=admin_required(admin_controller.manage_rooms),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/admin/manage_meal_plans",
        endpoint="manage_meal_plans",
        view_func=admin_required(admin_controller.manage_meal_plans),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/admin/extra_facilities",
        endpoint="manage_extra_facilities",
        view_func=admin_required(admin_controller.manage_extra_facilities),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/admin/delete_meal_plan/<int:meal_id>",
        endpoint="delete_meal_plan",
        view_func=admin_required(admin_controller.delete_meal_plan),
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/market_segments",
        endpoint="manage_market_segments",
        view_func=admin_required(admin_controller.manage_market_segments),
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/admin/rooms/delete/<int:room_id>",
        endpoint="delete_room",
        view_func=admin_required(admin_controller.delete_room),
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/bookings/<int:booking_id>/view",
        endpoint="admin_view_booking_for_hold",
        view_func=admin_required(admin_controller.admin_view_booking_for_hold),
    )
    app.add_url_rule(
        "/admin/bookings/<int:booking_id>/hold",
        endpoint="admin_hold_booking",
        view_func=admin_required(admin_controller.admin_hold_booking),
        methods=["POST"],
    )
    app.add_url_rule(
        "/admin/bookings",
        endpoint="admin_view_bookings",
        view_func=admin_required(admin_controller.admin_view_bookings),
    )
    app.add_url_rule(
        "/admin/users",
        endpoint="admin_view_users",
        view_func=admin_required(admin_controller.admin_view_users),
    )
