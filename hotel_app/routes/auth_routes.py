from hotel_app.controllers import auth_controller


def reg(app):
    routes = [
        ("/logout", "logout", auth_controller.logout, None),
        ("/register", "register", auth_controller.register, ["GET", "POST"]),
        ("/login", "login", auth_controller.login, ["GET", "POST"]),
    ]
    for rule, endpoint, view_func, methods in routes:
        app.add_url_rule(rule, endpoint=endpoint, view_func=view_func, methods=methods)
