from hotel_app.models import db as db_model


def list_all():
    conn = db_model.conn()
    rows = conn.execute("SELECT * FROM meal_plans").fetchall()
    conn.close()
    return rows


def count():
    conn = db_model.conn()
    count = conn.execute("SELECT COUNT(*) FROM meal_plans").fetchone()[0]
    conn.close()
    return count


def add(meal_plan_name, image_path):
    conn = db_model.conn()
    conn.execute(
        "INSERT INTO meal_plans (meal_plan_name, image_path) VALUES (?, ?)",
        (meal_plan_name, image_path),
    )
    conn.commit()
    conn.close()


def get_by_id(meal_id):
    conn = db_model.conn()
    row = conn.execute(
        "SELECT meal_plan_id, meal_plan_name, image_path FROM meal_plans WHERE meal_plan_id = ?",
        (meal_id,),
    ).fetchone()
    conn.close()
    return row


def used(meal_id):
    conn = db_model.conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE meal_plan_id = ?",
        (meal_id,),
    ).fetchone()[0]
    conn.close()
    return count


def remove(meal_id):
    conn = db_model.conn()
    conn.execute("DELETE FROM meal_plans WHERE meal_plan_id = ?", (meal_id,))
    conn.commit()
    conn.close()

