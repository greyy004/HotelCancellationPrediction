from hotel_app.routes.admin_routes import register_admin_routes
from hotel_app.routes.auth_routes import register_auth_routes
from hotel_app.routes.payment_routes import register_payment_routes
from hotel_app.routes.public_routes import register_public_routes
from hotel_app.routes.user_routes import register_user_routes


def register_all_routes(app):
    register_public_routes(app)
    register_auth_routes(app)
    register_payment_routes(app)
    register_user_routes(app)
    register_admin_routes(app)
