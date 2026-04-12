import os
import sqlite3

from config import (DB_FILE_NAME, DEFAULT_CUSTOMER_PASSWORD,
                    DEFAULT_CUSTOMER_USERNAME)


def get_db_path():
    src_dir = os.path.dirname(os.path.dirname(__file__))
    project_root = os.path.dirname(src_dir)
    db_dir = os.path.join(project_root, "db")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, DB_FILE_NAME)

def get_connection():
    connection = sqlite3.connect(get_db_path())
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def initialize_database():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trains (
                train_number TEXT PRIMARY KEY,train_name TEXT NOT NULL,origin_station TEXT NOT NULL,destination_station TEXT NOT NULL,intermediate_stops TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS train_stops (id INTEGER PRIMARY KEY AUTOINCREMENT,train_number TEXT NOT NULL,stop_order INTEGER NOT NULL,station_name TEXT NOT NULL,arrival_time TEXT NOT NULL,departure_time TEXT NOT NULL,FOREIGN KEY (train_number) REFERENCES trains(train_number) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,is_active INTEGER NOT NULL DEFAULT 1)
            """
        )
        cursor.execute("PRAGMA table_info(customers)")
        columns = {row[1] for row in cursor.fetchall()}
        if "name" not in columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN name TEXT")
        if "email" not in columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN email TEXT")
        if "phone" not in columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN phone TEXT")
        if "address" not in columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN address TEXT")
        cursor.execute(
            """
            INSERT OR IGNORE INTO customers (username,password,is_active) VALUES (?, ?, 1)
            """,
            (DEFAULT_CUSTOMER_USERNAME, DEFAULT_CUSTOMER_PASSWORD),
        )
        connection.commit()
