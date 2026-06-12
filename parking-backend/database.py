import os
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "1234"),
    "dbname": os.getenv("DB_NAME", "parking_vkr"),
}

PARKING_ADDRESS = os.getenv("PARKING_ADDRESS", "Санкт-Петербург, демо-парковка IRS")


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    id SERIAL PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    balance REAL DEFAULT 0,
                    api_user_id TEXT UNIQUE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Vehicles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    plate_number TEXT UNIQUE NOT NULL,
                    model TEXT DEFAULT '',
                    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ParkingSessions (
                    id SERIAL PRIMARY KEY,
                    vehicle_id INTEGER,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    total_cost REAL DEFAULT 0,
                    is_paid INTEGER DEFAULT 0 CHECK (is_paid IN (0, 1)),
                    parking_slot INTEGER NOT NULL,
                    photo_path TEXT,
                    plate_number TEXT,
                    FOREIGN KEY(vehicle_id) REFERENCES Vehicles(id) ON DELETE SET NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    plate_number TEXT NOT NULL,
                    message TEXT NOT NULL,
                    level TEXT NOT NULL DEFAULT 'info',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    is_read INTEGER DEFAULT 0 CHECK (is_read IN (0, 1)),
                    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute(
                "ALTER TABLE Users ADD COLUMN IF NOT EXISTS api_user_id TEXT UNIQUE"
            )
            cursor.execute(
                "ALTER TABLE Vehicles ADD COLUMN IF NOT EXISTS model TEXT DEFAULT ''"
            )
            cursor.execute(
                "ALTER TABLE ParkingSessions ADD COLUMN IF NOT EXISTS plate_number TEXT"
            )

            conn.commit()
            print("База данных PostgreSQL успешно инициализирована.")


def sync_user(full_name: str, email: str, api_user_id: str | None = None):
    email_norm = email.strip().lower()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if api_user_id:
                cursor.execute(
                    "SELECT id FROM Users WHERE api_user_id = %s OR email = %s",
                    (api_user_id, email_norm),
                )
            else:
                cursor.execute("SELECT id FROM Users WHERE email = %s", (email_norm,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                cursor.execute(
                    "UPDATE Users SET full_name = %s, api_user_id = COALESCE(%s, api_user_id) WHERE id = %s",
                    (full_name, api_user_id, user_id),
                )
                conn.commit()
                return user_id

            cursor.execute(
                "INSERT INTO Users (full_name, email, balance, api_user_id) VALUES (%s, %s, 0, %s) RETURNING id",
                (full_name, email_norm, api_user_id),
            )
            user_id = cursor.fetchone()[0]
            conn.commit()
            return user_id


def get_user_by_api_id(api_user_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, full_name, email, balance FROM Users WHERE api_user_id = %s",
                (api_user_id,),
            )
            return cursor.fetchone()


def get_user_by_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, full_name, email, balance FROM Users WHERE email = %s",
                (email.strip().lower(),),
            )
            return cursor.fetchone()


def add_user(full_name: str, email: str, initial_balance: float = 0.0):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Users (full_name, email, balance) VALUES (%s, %s, %s) RETURNING id",
                    (full_name, email.strip().lower(), initial_balance),
                )
                user_id = cursor.fetchone()[0]
                conn.commit()
                return user_id
    except psycopg2.errors.UniqueViolation:
        return None


def add_vehicle(user_id: int, plate_number: str, model: str = ""):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Vehicles (user_id, plate_number, model) VALUES (%s, %s, %s) RETURNING id",
                    (user_id, plate_number.upper(), model),
                )
                vehicle_id = cursor.fetchone()[0]
                conn.commit()
                return vehicle_id
    except psycopg2.errors.UniqueViolation:
        return None


def list_vehicles(user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, plate_number, model FROM Vehicles WHERE user_id = %s ORDER BY id",
                (user_id,),
            )
            return cursor.fetchall()


def check_vehicle_exists(plate_number: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, user_id FROM Vehicles WHERE plate_number = %s",
                (plate_number.upper(),),
            )
            return cursor.fetchone()


def start_parking_session(plate_number: str, parking_slot: int, photo_path: str | None = None):
    plate = plate_number.upper()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM Vehicles WHERE plate_number = %s", (plate,))
            vehicle = cursor.fetchone()
            vehicle_id = vehicle[0] if vehicle else None
            entry_time = datetime.now()

            cursor.execute(
                '''
                INSERT INTO ParkingSessions
                    (vehicle_id, entry_time, parking_slot, photo_path, is_paid, plate_number)
                VALUES (%s, %s, %s, %s, 0, %s) RETURNING id
                ''',
                (vehicle_id, entry_time, parking_slot, photo_path, plate),
            )
            session_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Машина {plate} заняла слот {parking_slot} в {entry_time:%Y-%m-%d %H:%M:%S}")
            return session_id


def end_parking_session(plate_number: str):
    plate = plate_number.upper()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE ParkingSessions
                SET exit_time = %s
                WHERE plate_number = %s AND exit_time IS NULL
                RETURNING id
                ''',
                (datetime.now(), plate),
            )
            row = cursor.fetchone()
            conn.commit()
            return row[0] if row else None


def get_active_session(plate_number: str):
    plate = plate_number.upper()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT ps.id, ps.entry_time, ps.vehicle_id, v.user_id, ps.is_paid
                FROM ParkingSessions ps
                LEFT JOIN Vehicles v ON ps.vehicle_id = v.id
                WHERE ps.plate_number = %s AND ps.exit_time IS NULL
                ORDER BY ps.id DESC LIMIT 1
                ''',
                (plate,),
            )
            return cursor.fetchone()


def add_notification(user_id: int, plate_number: str, message: str, level: str = "info"):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO Notifications (user_id, plate_number, message, level, created_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                ''',
                (user_id, plate_number.upper(), message, level, datetime.now()),
            )
            notif_id = cursor.fetchone()[0]
            conn.commit()
            print(f"[УВЕДОМЛЕНИЕ] user={user_id} plate={plate_number}: {message}")
            return notif_id


def get_notifications(user_id: int, limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT id, plate_number, message, level, created_at, is_read
                FROM Notifications
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (user_id, limit),
            )
            return cursor.fetchall()


def get_parking_history(user_id: int, limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT ps.id, COALESCE(v.plate_number, ps.plate_number) AS plate,
                       ps.entry_time, ps.exit_time, ps.photo_path, ps.parking_slot
                FROM ParkingSessions ps
                LEFT JOIN Vehicles v ON ps.vehicle_id = v.id
                WHERE v.user_id = %s
                   OR ps.plate_number IN (
                       SELECT plate_number FROM Vehicles WHERE user_id = %s
                   )
                ORDER BY ps.entry_time DESC
                LIMIT %s
                ''',
                (user_id, user_id, limit),
            )
            return cursor.fetchall()


if __name__ == "__main__":
    init_db()
