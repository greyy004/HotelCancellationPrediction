import sqlite3

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from hotel_app.models.customer_model import create_customer, get_customer_by_email


def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("landing"))


def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"].strip().lower()
        phone = request.form["phone"]
        address = request.form["address"]
        password_hash = generate_password_hash(request.form["password"])

        try:
            create_customer(name, email, phone, address, password_hash)
            flash("Registration successful! You can now login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists!", "danger")

    return render_template("register.html")


def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = get_customer_by_email(email)
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["customer_id"]
            session["is_admin"] = bool(user["is_admin"])
            session["user_name"] = user["name"]
            flash("Login successful!", "success")

            next_url = request.args.get("next") or request.form.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(
                url_for("admin_dashboard" if user["is_admin"] else "user_dashboard")
            )

        flash("Invalid credentials", "danger")

    return render_template("login.html", next=request.args.get("next"))
