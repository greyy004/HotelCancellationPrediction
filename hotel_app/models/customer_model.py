from hotel_app.models import db as db_model


def create_customer(name, email, phone, address, password_hash):
    conn = db_model.conn()
    conn.execute(
        "INSERT INTO customers (name, email, phone, address, password) VALUES (?, ?, ?, ?, ?)",
        (name, email, phone, address, password_hash),
    )
    conn.commit()
    conn.close()


def find_by_email(email):
    conn = db_model.conn()
    row = conn.execute("SELECT * FROM customers WHERE lower(email)=?", (email,)).fetchone()
    conn.close()
    return row


def find_by_id(customer_id):
    conn = db_model.conn()
    row = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    conn.close()
    return row


def update_profile(customer_id, name, phone, address):
    conn = db_model.conn()
    conn.execute(
        "UPDATE customers SET name = ?, phone = ?, address = ? WHERE customer_id = ?",
        (name, phone, address, customer_id),
    )
    conn.commit()
    conn.close()


def get_contact_info(customer_id):
    conn = db_model.conn()
    row = conn.execute(
        "SELECT name, email, phone FROM customers WHERE customer_id=?",
        (customer_id,),
    ).fetchone()
    conn.close()
    return row


def count_non_admin_users():
    conn = db_model.conn()
    count = conn.execute("SELECT COUNT(*) FROM customers WHERE is_admin=0").fetchone()[0]
    conn.close()
    return count


def list_users_with_booking_stats():
    conn = db_model.conn()
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

