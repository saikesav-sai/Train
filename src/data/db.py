import os
import sqlite3

from config import DB_FILE_NAME


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
        connection.commit()
