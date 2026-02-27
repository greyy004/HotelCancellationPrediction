import sqlite3

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from hotel_app.models import customer_model


def dash_route(is_admin):
    return "admin_dashboard" if is_admin else "user_dashboard"


def valid_email(email):
    if not email or " " in email or "@" not in email:
        return False
    local_part, domain_part = email.rsplit("@", 1)
    return bool(local_part and "." in domain_part and not domain_part.startswith("."))


def strong_pass(password):
    if len(password) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_letter and has_digit

def valid_register(name, email, phone, address, password, confirm_password):
    if len(name) < 2:
        return "Name must be at least 2 characters."
    if not valid_email(email):
        return "Please enter a valid email address."
    if phone and (not phone.isdigit() or not (7 <= len(phone) <= 15)):
        return "Phone number must be 7 to 15 digits."
    if len(address) < 3:
        return "Address must be at least 3 characters."
    if not strong_pass(password):
        return "Password must be 8+ characters with letters and numbers."
    if password != confirm_password:
        return "Passwords do not match."
    return None


def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("landing"))


def register():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password", "")

        validation_error = valid_register(
            name,
            email,
            phone,
            address,
            password,
            confirm_password,
        )
        if validation_error:
            flash(validation_error, "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        try:
            customer_model.add(name, email, phone, address, password_hash)
            flash("Registration successful! You can now login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists!", "danger")

    return render_template("register.html")


def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not valid_email(email) or not password:
            flash("Please enter a valid email and password.", "danger")
            return render_template("login.html", next=request.args.get("next"))

        user = customer_model.get_by_email(email)
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["customer_id"]
            session["is_admin"] = bool(user["is_admin"])
            session["user_name"] = user["name"]
            flash("Login successful!", "success")

            next_url = request.args.get("next") or request.form.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(url_for(dash_route(user["is_admin"])))

        flash("Invalid credentials", "danger")

    return render_template("login.html", next=request.args.get("next"))
