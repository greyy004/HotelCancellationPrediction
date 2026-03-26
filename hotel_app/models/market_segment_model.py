from hotel_app.models import db as db_model

ALLOWED_SEGMENTS = {"Online", "Offline"}


def list_market_segments():
    conn = db_model.conn()
    rows = conn.execute(
        """
        SELECT * FROM market_segments
        WHERE segment_name IN ('Online', 'Offline')
        ORDER BY market_segment_id
    """
    ).fetchall()
    conn.close()
    return rows


def create_market_segment(segment_name):
    segment_name = (segment_name or "").strip().title()
    if segment_name not in ALLOWED_SEGMENTS:
        raise ValueError("Only Online and Offline segments are allowed.")
    conn = db_model.conn()
    conn.execute(
        "INSERT INTO market_segments (segment_name) VALUES (?)",
        (segment_name,),
    )
    conn.commit()
    conn.close()

