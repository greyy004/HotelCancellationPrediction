import sqlite3

from hotel_app.models import db as db_model


def list_all():
    conn = db_model.conn()
    rows = conn.execute("SELECT * FROM market_segments").fetchall()
    conn.close()
    return rows


def add(segment_name):
    conn = db_model.conn()
    try:
        conn.execute(
            "INSERT INTO market_segments (segment_name) VALUES (?)",
            (segment_name,),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise
    finally:
        conn.close()
