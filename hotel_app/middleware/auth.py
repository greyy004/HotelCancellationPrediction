from functools import wraps

from flask import flash, redirect, request, session, url_for


def go_login(message, category, next_url=None):
    flash(message, category)
    if next_url:
        return redirect(url_for("login", next=next_url))
    return redirect(url_for("login"))


def need_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return go_login("Please login first.", "warning", request.url)
        return f(*args, **kwargs)

    return decorated


def need_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return go_login("Admin access required.", "danger")
        return f(*args, **kwargs)

    return decorated
