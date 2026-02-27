from hotel_app.models import db as db_model

EXTRA_FACILITY_SUMMARY_JOIN = """
LEFT JOIN (
    SELECT booking_id,
           COUNT(*) AS extra_facility_count,
           SUM(facility_price) AS extra_facility_total
    FROM booking_extra_facilities
    GROUP BY booking_id
) ef ON b.booking_id = ef.booking_id
"""

BOOKING_HOLD_JOIN = "LEFT JOIN booking_hold h ON b.booking_id = h.booking_id"


def add(
    conn,
    customer_id,
    room_id,
    meal_plan_id,
    market_segment_id,
    lead_time,
    arrival_year,
    arrival_month,
    arrival_date,
    avg_price_per_room,
    no_of_special_requests,
    total_nights,
    total_guests,
    required_car_parking_space=0,
    selected_facilities=None,
):
    cursor = conn.execute(
        """
        INSERT INTO bookings (
            customer_id, room_id, meal_plan_id, market_segment_id, booking_status,
            lead_time, arrival_year, arrival_month, arrival_date,
            avg_price_per_room, no_of_special_requests, total_nights, total_guests,
            required_car_parking_space
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """,
        (
            customer_id,
            room_id,
            meal_plan_id,
            market_segment_id,
            "Not_Canceled",
            lead_time,
            arrival_year,
            arrival_month,
            arrival_date,
            avg_price_per_room,
            no_of_special_requests,
            total_nights,
            total_guests,
            required_car_parking_space,
        ),
    )
    booking_id = cursor.lastrowid

    if selected_facilities:
        conn.executemany(
            """
            INSERT INTO booking_extra_facilities (
                booking_id, facility_id, facility_name, facility_price
            ) VALUES (?, ?, ?, ?)
        """,
            [
                (
                    booking_id,
                    int(f["facility_id"]),
                    str(f["facility_name"]),
                    float(f["price"] or 0),
                )
                for f in selected_facilities
            ],
        )

    return booking_id


def list_active_windows(room_id):
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT arrival_year, arrival_month, arrival_date, total_nights
        FROM bookings
        WHERE room_id = ? AND booking_status = 'Not_Canceled'
    """,
        (room_id,),
    ).fetchall()
    conn.close()
    return rows


def list_active_room(room_id):
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT room_id, arrival_year, arrival_month, arrival_date, total_nights, booking_status
        FROM bookings
        WHERE room_id = ? AND booking_status = 'Not_Canceled'
    """,
        (room_id,),
    ).fetchall()
    conn.close()
    return rows


def list_user(user_id):
    conn = db_model.conn()
    rows = conn.execute(
        f"""
        SELECT b.booking_id, r.room_number, t.room_type_name, m.meal_plan_name, s.segment_name,
               b.total_nights, b.total_guests,
               b.booking_status, b.created_at, b.avg_price_per_room, t.image_path,
               ef.extra_facility_total,
               ef.extra_facility_count,
               h.is_on_hold,
               h.hold_reason,
               h.noted_at AS hold_noted_at
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        LEFT JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        LEFT JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        {EXTRA_FACILITY_SUMMARY_JOIN}
        {BOOKING_HOLD_JOIN}
        WHERE b.customer_id = ?
        ORDER BY b.created_at DESC
    """,
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_user(booking_id, user_id):
    conn = db_model.conn()
    row = conn.execute(
        "SELECT * FROM bookings WHERE booking_id = ? AND customer_id = ?",
        (booking_id, user_id),
    ).fetchone()
    conn.close()
    return row


def set_status(booking_id, status):
    conn = db_model.conn()
    conn.execute("UPDATE bookings SET booking_status = ? WHERE booking_id = ?", (status, booking_id))
    conn.commit()
    conn.close()


def count():
    conn = db_model.conn()
    count = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    conn.close()
    return count


def list_recent(limit=5):
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT b.booking_id,
               c.name as customer_name,
               r.room_number as room_number,
               t.room_type_name as room_type_name,
               m.meal_plan_name,
               s.segment_name,
               b.total_guests as total_guests,
               b.total_nights,
               b.booking_status,
               b.created_at
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        ORDER BY b.created_at DESC
        LIMIT ?
    """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_hold_review(booking_id):
    conn = db_model.conn()
    row = conn.execute(
        f"""
        SELECT b.*,
               c.name AS customer_name,
               c.email AS customer_email,
               c.phone AS customer_phone,
               c.address AS customer_address,
               r.room_number AS room_number,
               t.room_type_name AS room_type_name,
               m.meal_plan_name,
               s.segment_name,
               ef.extra_facility_count AS extra_facility_count,
               ef.extra_facility_total AS extra_facility_total,
               h.is_on_hold AS is_on_hold,
               h.hold_reason AS hold_reason,
               h.noted_at
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        LEFT JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        {EXTRA_FACILITY_SUMMARY_JOIN}
        {BOOKING_HOLD_JOIN}
        WHERE b.booking_id = ?
    """,
        (booking_id,),
    ).fetchone()
    conn.close()
    return row


def get_hold_action(booking_id):
    conn = db_model.conn()
    row = conn.execute(
        """
        SELECT b.*, s.segment_name, m.meal_plan_name, h.is_on_hold AS is_on_hold
        FROM bookings b
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        LEFT JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        LEFT JOIN booking_hold h ON b.booking_id = h.booking_id
        WHERE b.booking_id = ?
    """,
        (booking_id,),
    ).fetchone()
    conn.close()
    return row


def save_hold(booking_id, hold_reason, noted_by_admin_id):
    conn = db_model.conn()
    conn.execute(
        """
        INSERT INTO booking_hold (
            booking_id, is_on_hold, hold_reason, noted_by_admin_id, noted_at
        )
        VALUES (?, 1, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(booking_id) DO UPDATE SET
            is_on_hold = 1,
            hold_reason = excluded.hold_reason,
            noted_by_admin_id = excluded.noted_by_admin_id,
            noted_at = CURRENT_TIMESTAMP
    """,
        (booking_id, hold_reason, noted_by_admin_id),
    )
    conn.commit()
    conn.close()


def list_admin():
    conn = db_model.conn()
    rows = conn.execute(
        f"""
        SELECT b.*,
               r.room_number as room_number,
               t.room_type_name as room_type_name,
               m.meal_plan_name,
               s.segment_name,
               ef.extra_facility_count AS extra_facility_count,
               ef.extra_facility_total AS extra_facility_total,
               h.is_on_hold AS is_on_hold
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        LEFT JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        {EXTRA_FACILITY_SUMMARY_JOIN}
        {BOOKING_HOLD_JOIN}
        ORDER BY b.created_at DESC
    """
    ).fetchall()
    conn.close()
    return rows


def customer_history(customer_id, before_booking_id=None):
    conn = db_model.conn()
    if before_booking_id is None:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS previous_total,
                SUM(CASE WHEN booking_status = 'Not_Canceled' THEN 1 ELSE 0 END) AS previous_not_canceled
            FROM bookings
            WHERE customer_id = ?
        """,
            (customer_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS previous_total,
                SUM(CASE WHEN booking_status = 'Not_Canceled' THEN 1 ELSE 0 END) AS previous_not_canceled
            FROM bookings
            WHERE customer_id = ? AND booking_id < ?
        """,
            (customer_id, before_booking_id),
        ).fetchone()
    conn.close()

    previous_total = int((row["previous_total"] or 0) if row else 0)
    previous_not_canceled = int((row["previous_not_canceled"] or 0) if row else 0)
    return previous_total, previous_not_canceled
