from hotel_app.models.db import get_db_connection


def insert_booking(
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
    selected_facilities=None,
):
    cursor = conn.execute(
        """
        INSERT INTO bookings (
            customer_id, room_id, meal_plan_id, market_segment_id, booking_status,
            lead_time, arrival_year, arrival_month, arrival_date,
            avg_price_per_room, no_of_special_requests, total_nights, total_guests
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
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


def list_active_booking_windows(room_id, conn=None):
    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    rows = conn.execute(
        """
        SELECT arrival_year, arrival_month, arrival_date, total_nights
        FROM bookings
        WHERE room_id = ? AND booking_status = 'Not_Canceled'
    """,
        (room_id,),
    ).fetchall()

    if owns_conn:
        conn.close()
    return rows


def list_active_bookings_for_room(room_id):
    conn = get_db_connection()
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


def list_user_bookings_with_hold(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT b.booking_id, r.room_number, t.room_type_name, m.meal_plan_name, s.segment_name,
               b.total_nights, COALESCE(b.total_guests, 0) as total_guests,
               b.booking_status, b.created_at, b.avg_price_per_room, t.image_path,
               COALESCE(ef.extra_facility_total, 0) AS extra_facility_total,
               COALESCE(ef.extra_facility_count, 0) AS extra_facility_count,
               COALESCE(h.is_on_hold, 0) AS is_on_hold,
               NULLIF(h.hold_reason, '') AS hold_reason,
               h.noted_at AS hold_noted_at
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        LEFT JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        LEFT JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        LEFT JOIN (
            SELECT booking_id,
                   COUNT(*) AS extra_facility_count,
                   SUM(facility_price) AS extra_facility_total
            FROM booking_extra_facilities
            GROUP BY booking_id
        ) ef ON b.booking_id = ef.booking_id
        LEFT JOIN booking_hold h ON b.booking_id = h.booking_id
        WHERE b.customer_id = ?
        ORDER BY b.created_at DESC
    """,
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_user_booking(booking_id, user_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM bookings WHERE booking_id = ? AND customer_id = ?",
        (booking_id, user_id),
    ).fetchone()
    conn.close()
    return row


def set_booking_status(booking_id, status):
    conn = get_db_connection()
    conn.execute(
        "UPDATE bookings SET booking_status = ? WHERE booking_id = ?",
        (status, booking_id),
    )
    conn.commit()
    conn.close()


def count_bookings():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    conn.close()
    return count


def list_recent_bookings(limit=5):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT b.booking_id,
               c.name as customer_name,
               COALESCE(r.room_number, 'Deleted Room') as room_number,
               COALESCE(t.room_type_name, 'Unknown Type') as room_type_name,
               m.meal_plan_name,
               s.segment_name,
               COALESCE(b.total_guests, 0) as total_guests,
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


def get_booking_for_hold_review(booking_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT b.*,
               c.name AS customer_name,
               c.email AS customer_email,
               c.phone AS customer_phone,
               c.address AS customer_address,
               COALESCE(r.room_number, 'Deleted Room') AS room_number,
               COALESCE(t.room_type_name, 'Unknown Room Type') AS room_type_name,
               m.meal_plan_name,
               s.segment_name,
               COALESCE(ef.extra_facility_count, 0) AS extra_facility_count,
               COALESCE(ef.extra_facility_total, 0) AS extra_facility_total,
               COALESCE(h.is_on_hold, 0) AS is_on_hold,
               NULLIF(h.hold_reason, '') AS hold_reason,
               h.noted_at
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        LEFT JOIN meal_plans m ON b.meal_plan_id = m.meal_plan_id
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        LEFT JOIN (
            SELECT booking_id,
                   COUNT(*) AS extra_facility_count,
                   SUM(facility_price) AS extra_facility_total
            FROM booking_extra_facilities
            GROUP BY booking_id
        ) ef ON b.booking_id = ef.booking_id
        LEFT JOIN booking_hold h ON b.booking_id = h.booking_id
        WHERE b.booking_id = ?
    """,
        (booking_id,),
    ).fetchone()
    conn.close()
    return row


def get_booking_for_hold_action(booking_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT b.*, s.segment_name, COALESCE(h.is_on_hold, 0) AS is_on_hold
        FROM bookings b
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        LEFT JOIN booking_hold h ON b.booking_id = h.booking_id
        WHERE b.booking_id = ?
    """,
        (booking_id,),
    ).fetchone()
    conn.close()
    return row


def upsert_booking_hold(booking_id, hold_reason, noted_by_admin_id):
    conn = get_db_connection()
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


def list_admin_bookings_with_hold():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT b.*,
               COALESCE(r.room_number, 'Deleted Room') as room_number,
               COALESCE(t.room_type_name, 'Unknown Room Type') as room_type_name,
               s.segment_name,
               COALESCE(ef.extra_facility_count, 0) AS extra_facility_count,
               COALESCE(ef.extra_facility_total, 0) AS extra_facility_total,
               COALESCE(h.is_on_hold, 0) AS is_on_hold
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.room_id
        LEFT JOIN room_types t ON r.room_type_id = t.room_type_id
        JOIN market_segments s ON b.market_segment_id = s.market_segment_id
        LEFT JOIN (
            SELECT booking_id,
                   COUNT(*) AS extra_facility_count,
                   SUM(facility_price) AS extra_facility_total
            FROM booking_extra_facilities
            GROUP BY booking_id
        ) ef ON b.booking_id = ef.booking_id
        LEFT JOIN booking_hold h ON b.booking_id = h.booking_id
        ORDER BY b.created_at DESC
    """
    ).fetchall()
    conn.close()
    return rows
