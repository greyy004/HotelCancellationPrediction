from hotel_app.models import db as db_model


def list_all_public_rooms():
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT t1.*, t2.image_path, t2.room_type_name, t2.description
        FROM rooms t1
        LEFT JOIN room_types t2 ON t1.room_type_id = t2.room_type_id
    """
    ).fetchall()
    conn.close()
    return rows


def find_public_room(room_id):
    conn = db_model.conn()
    row = conn.execute(
        """
        SELECT r.room_id, r.room_number, r.price_per_night, t.room_type_name, t.image_path, t.description
        FROM rooms r
        JOIN room_types t ON r.room_type_id = t.room_type_id
        WHERE r.room_id=?
    """,
        (room_id,),
    ).fetchone()
    conn.close()
    return row


def find_room_for_booking(room_id):
    conn = db_model.conn()
    row = conn.execute(
        """
        SELECT r.room_id, r.room_number, r.price_per_night, t.room_type_name, t.image_path, t.description,
               t.max_guests AS max_guests
        FROM rooms r
        JOIN room_types t ON r.room_type_id = t.room_type_id
        WHERE r.room_id=?
    """,
        (room_id,),
    ).fetchone()
    conn.close()
    return row


def list_room_types():
    conn = db_model.conn()
    rows = conn.execute("SELECT * FROM room_types").fetchall()
    conn.close()
    return rows


def list_room_types_for_dashboard():
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT room_type_id, room_type_name, description, price_per_night, max_guests
        FROM room_types
        ORDER BY room_type_id
    """
    ).fetchall()
    conn.close()
    return rows


def count_rooms():
    conn = db_model.conn()
    count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    conn.close()
    return count


def create_room_type(name, description, price_per_night, image_path, max_guests):
    conn = db_model.conn()
    conn.execute(
        "INSERT INTO room_types (room_type_name,description,price_per_night,image_path,max_guests) VALUES (?,?,?,?,?)",
        (name, description, price_per_night, image_path, max_guests),
    )
    conn.commit()
    conn.close()


def find_room_type_price(room_type_id):
    conn = db_model.conn()
    row = conn.execute(
        "SELECT price_per_night FROM room_types WHERE room_type_id=?",
        (room_type_id,),
    ).fetchone()
    conn.close()
    return row


def create_room(room_number, room_type_id, price_per_night):
    conn = db_model.conn()
    conn.execute(
        "INSERT INTO rooms (room_number, room_type_id, price_per_night) VALUES (?, ?, ?)",
        (room_number, room_type_id, price_per_night),
    )
    conn.commit()
    conn.close()


def list_rooms_for_admin():
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT r.room_id, r.room_number, t.room_type_name, t.image_path, r.price_per_night,
               t.price_per_night AS type_default_price
        FROM rooms r
        JOIN room_types t ON r.room_type_id = t.room_type_id
        ORDER BY r.room_number
    """
    ).fetchall()
    conn.close()
    return rows


def find_room_by_id(room_id):
    conn = db_model.conn()
    row = conn.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,)).fetchone()
    conn.close()
    return row


def delete_room(room_id):
    conn = db_model.conn()
    conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()


def find_max_guests_for_room(room_id):
    conn = db_model.conn()
    row = conn.execute(
        """
        SELECT t.max_guests AS max_guests
        FROM rooms r
        JOIN room_types t ON r.room_type_id = t.room_type_id
        WHERE r.room_id = ?
    """,
        (room_id,),
    ).fetchone()

    conn.close()
    return row

