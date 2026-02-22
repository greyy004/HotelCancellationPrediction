from hotel_app.models.db import get_db_connection


def list_meal_plans():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM meal_plans").fetchall()
    conn.close()
    return rows


def count_meal_plans():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM meal_plans").fetchone()[0]
    conn.close()
    return count


def insert_meal_plan(meal_plan_name, image_path):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO meal_plans (meal_plan_name, image_path) VALUES (?, ?)",
        (meal_plan_name, image_path),
    )
    conn.commit()
    conn.close()


def get_meal_plan_by_id(meal_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT meal_plan_id, meal_plan_name, image_path FROM meal_plans WHERE meal_plan_id = ?",
        (meal_id,),
    ).fetchone()
    conn.close()
    return row


def count_bookings_using_meal_plan(meal_id):
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE meal_plan_id = ?",
        (meal_id,),
    ).fetchone()[0]
    conn.close()
    return count


def delete_meal_plan_by_id(meal_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM meal_plans WHERE meal_plan_id = ?", (meal_id,))
    conn.commit()
    conn.close()
