import sqlite3

from hotel_app.models.db import get_db_connection


def list_extra_facilities():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT facility_id, facility_name, price, created_at
        FROM extra_facilities
        ORDER BY facility_name
    """
    ).fetchall()
    conn.close()
    return rows


def count_extra_facilities():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM extra_facilities").fetchone()[0]
    conn.close()
    return count


def insert_extra_facility(facility_name, price):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO extra_facilities (facility_name, price) VALUES (?, ?)",
            (facility_name, price),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise
    conn.close()


def normalize_facility_ids(raw_facility_ids):
    if not isinstance(raw_facility_ids, list):
        return []

    unique_ids = []
    seen = set()
    for raw in raw_facility_ids:
        try:
            facility_id = int(raw)
        except (TypeError, ValueError):
            continue
        if facility_id <= 0 or facility_id in seen:
            continue
        unique_ids.append(facility_id)
        seen.add(facility_id)
    return unique_ids


def get_extra_facilities_by_ids(facility_ids, conn=None):
    normalized_ids = normalize_facility_ids(facility_ids)
    if not normalized_ids:
        return []

    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    placeholders = ",".join("?" * len(normalized_ids))
    rows = conn.execute(
        f"""
        SELECT facility_id, facility_name, price
        FROM extra_facilities
        WHERE facility_id IN ({placeholders})
        ORDER BY facility_name
    """,
        normalized_ids,
    ).fetchall()

    if owns_conn:
        conn.close()
    return rows


def summarize_selected_facilities(facility_ids, conn=None):
    selected_facilities = get_extra_facilities_by_ids(facility_ids, conn=conn)
    total_count = len(selected_facilities)
    total_price = round(sum(float(f["price"] or 0) for f in selected_facilities), 2)
    return selected_facilities, total_count, total_price
