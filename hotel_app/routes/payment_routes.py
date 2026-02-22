from hotel_app.controllers import payment_controller
from hotel_app.middleware.auth import login_required


def register_payment_routes(app):
    app.add_url_rule(
        "/api/khalti/create-payment",
        endpoint="create_khalti_payment",
        view_func=login_required(payment_controller.create_khalti_payment),
        methods=["POST"],
    )
    app.add_url_rule(
        "/payment-success",
        endpoint="payment_success",
        view_func=login_required(payment_controller.payment_success),
    )
    app.add_url_rule(
        "/payment-cancel",
        endpoint="payment_cancel",
        view_func=login_required(payment_controller.payment_cancel),
    )
