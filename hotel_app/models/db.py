import sqlite3

from hotel_app.config import DB_PATH

DEFAULT_MARKET_SEGMENTS = [
    "Online",
    "Offline",
]


def _create_schema(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1))
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
            max_guests INTEGER NOT NULL DEFAULT 2 CHECK(max_guests >= 1)
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
            price REAL NOT NULL DEFAULT 0 CHECK(price >= 0)
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
            booking_status TEXT NOT NULL CHECK(booking_status IN ('Canceled','Not_Canceled')),
            lead_time INTEGER NOT NULL DEFAULT 0 CHECK(lead_time >= 0),
            arrival_year INTEGER NOT NULL,
            arrival_month INTEGER NOT NULL CHECK(arrival_month BETWEEN 1 AND 12),
            arrival_date INTEGER NOT NULL CHECK(arrival_date BETWEEN 1 AND 31),
            avg_price_per_room REAL NOT NULL DEFAULT 0 CHECK(avg_price_per_room >= 0),
            no_of_special_requests INTEGER NOT NULL DEFAULT 0 CHECK(no_of_special_requests >= 0),
            total_nights INTEGER NOT NULL DEFAULT 1 CHECK(total_nights >= 1),
            total_guests INTEGER NOT NULL DEFAULT 1 CHECK(total_guests >= 1),
            required_car_parking_space INTEGER NOT NULL DEFAULT 0 CHECK(required_car_parking_space IN (0,1)),
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
            facility_price REAL NOT NULL DEFAULT 0 CHECK(facility_price >= 0),
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
            FOREIGN KEY(booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
            FOREIGN KEY(noted_by_admin_id) REFERENCES customers(customer_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bookings_customer_booking_status
        ON bookings(customer_id, booking_id, booking_status)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bookings_customer_status
        ON bookings(customer_id, booking_status)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bookings_room_status_arrival
        ON bookings(room_id, booking_status, arrival_year, arrival_month, arrival_date)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bookings_created_at
        ON bookings(created_at)
    """
    )


def _seed_static_data(cursor):
    for segment_name in DEFAULT_MARKET_SEGMENTS:
        cursor.execute(
            "INSERT OR IGNORE INTO market_segments (segment_name) VALUES (?)",
            (segment_name,),
        )


def init():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    _create_schema(cursor)
    _seed_static_data(cursor)

    conn.commit()
    conn.close()


def conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
