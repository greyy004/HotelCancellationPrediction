import sqlite3

from hotel_app.models import db as db_model


def list_all():
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT facility_id, facility_name, price, created_at
        FROM extra_facilities
        ORDER BY facility_name
    """
    ).fetchall()
    conn.close()
    return rows


def count():
    conn = db_model.conn()
    count = conn.execute("SELECT COUNT(*) FROM extra_facilities").fetchone()[0]
    conn.close()
    return count


def add(facility_name, price):
    conn = db_model.conn()
    try:
        conn.execute(
            "INSERT INTO extra_facilities (facility_name, price) VALUES (?, ?)",
            (facility_name, price),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise
    finally:
        conn.close()


def norm_ids(raw_facility_ids):
    if not isinstance(raw_facility_ids, list):
        return []

    unique_ids = []
    seen = set()
    for raw in raw_facility_ids:
        raw_str = str(raw).strip()
        if not raw_str.isdigit():
            continue
        facility_id = int(raw_str)

        if facility_id > 0 and facility_id not in seen:
            unique_ids.append(facility_id)
            seen.add(facility_id)

    return unique_ids


def get_by_ids(facility_ids):
    normalized_ids = norm_ids(facility_ids)
    if not normalized_ids:
        return []

    placeholders = ",".join("?" * len(normalized_ids))
    conn = db_model.conn()
    rows = conn.execute(
        f"""
        SELECT facility_id, facility_name, price
        FROM extra_facilities
        WHERE facility_id IN ({placeholders})
        ORDER BY facility_name
    """,
        normalized_ids,
    ).fetchall()
    conn.close()
    return rows


def summarize(facility_ids):
    selected_facilities = get_by_ids(facility_ids)
    total_count = len(selected_facilities)
    total_price = round(sum(float(f["price"] or 0) for f in selected_facilities), 2)
    return selected_facilities, total_count, total_price
