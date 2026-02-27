from hotel_app.routes.admin_routes import reg as reg_admin
from hotel_app.routes.auth_routes import reg as reg_auth
from hotel_app.routes.payment_routes import reg as reg_pay
from hotel_app.routes.public_routes import reg as reg_public
from hotel_app.routes.user_routes import reg as reg_user


def reg_all(app):
    route_registrars = [
        reg_public,
        reg_auth,
        reg_pay,
        reg_user,
        reg_admin,
    ]
    for reg in route_registrars:
        reg(app)
