from hotel_app.controllers import payment_controller
from hotel_app.middleware.auth import need_login


def reg(app):
    routes = [
        (
            "/api/khalti/create-payment",
            "create_khalti_payment",
            payment_controller.create,
            ["POST"],
        ),
        ("/payment-success", "payment_success", payment_controller.success, None),
        ("/payment-cancel", "payment_cancel", payment_controller.cancel, None),
    ]
    for rule, endpoint, view_func, methods in routes:
        app.add_url_rule(
            rule,
            endpoint=endpoint,
            view_func=need_login(view_func),
            methods=methods,
        )
