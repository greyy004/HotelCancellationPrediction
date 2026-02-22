import sqlite3

from hotel_app.config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS room_types (
            room_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_type_name TEXT UNIQUE NOT NULL,
            description TEXT,
            price_per_night INTEGER,
            image_path TEXT,
            max_guests INTEGER NOT NULL DEFAULT 2
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type_id INTEGER NOT NULL,
            price_per_night INTEGER,
            FOREIGN KEY(room_type_id) REFERENCES room_types(room_type_id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_plans (
            meal_plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_plan_name TEXT UNIQUE NOT NULL,
            image_path TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS market_segments (
            market_segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_name TEXT UNIQUE NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS extra_facilities (
            facility_id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL DEFAULT 0 CHECK(price >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            meal_plan_id INTEGER NOT NULL,
            market_segment_id INTEGER NOT NULL,
            booking_status TEXT CHECK(booking_status IN ('Canceled','Not_Canceled')) NOT NULL,
            lead_time INTEGER NOT NULL,
            arrival_year INTEGER NOT NULL,
            arrival_month INTEGER NOT NULL,
            arrival_date INTEGER NOT NULL,
            avg_price_per_room REAL NOT NULL,
            no_of_special_requests INTEGER DEFAULT 0,
            total_nights INTEGER,
            total_guests INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(room_id) REFERENCES rooms(room_id),
            FOREIGN KEY(meal_plan_id) REFERENCES meal_plans(meal_plan_id),
            FOREIGN KEY(market_segment_id) REFERENCES market_segments(market_segment_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_extra_facilities (
            booking_extra_facility_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            facility_id INTEGER NOT NULL,
            facility_name TEXT NOT NULL,
            facility_price REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(booking_id, facility_id),
            FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
            FOREIGN KEY(facility_id) REFERENCES extra_facilities(facility_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_hold (
            hold_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL UNIQUE,
            is_on_hold INTEGER NOT NULL DEFAULT 1 CHECK(is_on_hold IN (0,1)),
            hold_reason TEXT NOT NULL DEFAULT '',
            noted_by_admin_id INTEGER,
            noted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
            FOREIGN KEY(noted_by_admin_id) REFERENCES customers(customer_id)
        )
    """
    )

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
