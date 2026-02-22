from hotel_app.models.db import get_db_connection


def create_customer(name, email, phone, address, password_hash):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO customers (name, email, phone, address, password) VALUES (?, ?, ?, ?, ?)",
        (name, email, phone, address, password_hash),
    )
    conn.commit()
    conn.close()


def get_customer_by_email(email):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM customers WHERE lower(email)=?", (email,)).fetchone()
    conn.close()
    return row


def get_customer_by_id(customer_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    conn.close()
    return row


def update_customer_profile(customer_id, name, phone, address):
    conn = get_db_connection()
    conn.execute(
        "UPDATE customers SET name = ?, phone = ?, address = ? WHERE customer_id = ?",
        (name, phone, address, customer_id),
    )
    conn.commit()
    conn.close()


def get_customer_contact(customer_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT name, email, phone FROM customers WHERE customer_id=?",
        (customer_id,),
    ).fetchone()
    conn.close()
    return row


def count_non_admin_users():
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE is_admin=0"
    ).fetchone()[0]
    conn.close()
    return count


def list_non_admin_users_with_booking_counts():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT
            c.customer_id,
            c.name,
            c.email,
            c.phone,
            c.address,
            COUNT(b.booking_id) AS total_bookings,
            SUM(CASE WHEN b.booking_status = 'Not_Canceled' THEN 1 ELSE 0 END) AS active_bookings
        FROM customers c
        LEFT JOIN bookings b ON b.customer_id = c.customer_id
        WHERE c.is_admin = 0
        GROUP BY c.customer_id, c.name, c.email, c.phone, c.address
        ORDER BY c.customer_id DESC
    """
    ).fetchall()
    conn.close()
    return rows
