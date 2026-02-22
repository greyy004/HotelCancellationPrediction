from hotel_app.controllers import auth_controller


def register_auth_routes(app):
    app.add_url_rule("/logout", endpoint="logout", view_func=auth_controller.logout)
    app.add_url_rule(
        "/register",
        endpoint="register",
        view_func=auth_controller.register,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/login",
        endpoint="login",
        view_func=auth_controller.login,
        methods=["GET", "POST"],
    )
