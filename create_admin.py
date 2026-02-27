import sqlite3

from werkzeug.security import generate_password_hash

DB_FILE = "hotel_booking.db"


def add_admin(name, email, phone, password):
    hashed_password = generate_password_hash(password)
    normalized_email = email.strip().lower()

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                INSERT INTO customers (name, email, phone, password, is_admin)
                VALUES (?, ?, ?, ?, ?)
            """,
                (name, normalized_email, phone, hashed_password, 1),
            )
        print("Admin created successfully!")
    except sqlite3.IntegrityError:
        print("Error: Email already exists.")


if __name__ == "__main__":
    print("=== Create Admin User ===")
    name = input("Enter admin name: ")
    email = input("Enter admin email: ")
    phone = input("Enter admin phone: ")
    password = input("Enter admin password: ")

    add_admin(name, email, phone, password)
