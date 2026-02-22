import sqlite3

from hotel_app.models.db import get_db_connection


def list_market_segments():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM market_segments").fetchall()
    conn.close()
    return rows


def insert_market_segment(segment_name):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO market_segments (segment_name) VALUES (?)",
            (segment_name,),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise
    conn.close()
