import argparse
import os
import sys
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from customer.booking import (CLASS_FARES, DEFAULT_CLASS_CAPACITY,
                              ensure_booking_tables)
from data.db import get_connection, get_db_path, initialize_database


def reset_core_tables(connection):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM bookings")
    cursor.execute("DELETE FROM train_class_seats")
    cursor.execute("DELETE FROM train_stops")
    cursor.execute("DELETE FROM trains")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('bookings', 'train_stops', 'customers')")


def insert_customers(connection):
    customers = [
        ("user", "user123", "Default User", "user@example.com", "9000000001", "Chennai", 1),
        ("rahul", "rahul123", "Rahul Kumar", "rahul@example.com", "9000000002", "Delhi", 1),
        ("priya", "priya123", "Priya Singh", "priya@example.com", "9000000003", "Pune", 1),
        ("inactive_user", "inactive123", "Inactive Person", "inactive@example.com", "9000000004", "Hyd", 0),
        ("booking_owner", "book123", "Booking Owner", "owner@example.com", "9000000005", "Mumbai", 1),
        ("other_user", "other123", "Other User", "other@example.com", "9000000006", "Bhopal", 1),
    ]

    cursor = connection.cursor()
    cursor.executemany(
        """
        INSERT INTO customers (username,password,name,email,phone,address,is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        customers,
    )


def insert_train(connection, train_number, train_name, route_points):
    origin = route_points[0][0]
    destination = route_points[-1][0]
    intermediate_stops = ", ".join([item[0] for item in route_points[1:-1]])

    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO trains (train_number,train_name,origin_station,destination_station,intermediate_stops)
        VALUES (?, ?, ?, ?, ?)
        """,
        (train_number, train_name, origin, destination, intermediate_stops),
    )

    for index, (station_name, arrival_time, departure_time) in enumerate(route_points, start=1):
        cursor.execute(
            """
            INSERT INTO train_stops (train_number,stop_order,station_name,arrival_time,departure_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (train_number, index, station_name, arrival_time, departure_time),
        )


def insert_trains(connection):
    now = datetime.now()
    near_departure = (now + timedelta(hours=2)).strftime("%H:%M")
    near_arrival = (now + timedelta(hours=5)).strftime("%H:%M")

    insert_train(
        connection,
        "TR100",
        "South Star",
        [
            ("Chennai", "06:00", "06:10"),
            ("Trichy", "09:00", "09:10"),
            ("Madurai", "12:00", "12:10"),
        ],
    )

    insert_train(
        connection,
        "TR200",
        "Capital Runner",
        [
            ("Delhi", "08:00", "08:10"),
            ("Agra", "11:00", "11:10"),
        ],
    )

    insert_train(
        connection,
        "TR300",
        "Western Breeze",
        [
            ("Pune", "09:00", "09:10"),
            ("Lonavala", "10:00", "10:10"),
            ("Mumbai", "12:00", "12:10"),
        ],
    )

    insert_train(
        connection,
        "TR400",
        "Deccan Link",
        [
            ("Hyderabad", "07:30", "07:40"),
            ("Vijayawada", "12:30", "12:40"),
        ],
    )

    insert_train(
        connection,
        "TR500",
        "Quick Connect",
        [
            ("Bhopal", near_departure, near_departure),
            ("Indore", near_arrival, near_arrival),
        ],
    )


def initialize_seats_for_all_trains(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT train_number FROM trains ORDER BY train_number")
    train_numbers = [row[0] for row in cursor.fetchall()]

    for train_number in train_numbers:
        for class_name, total in DEFAULT_CLASS_CAPACITY.items():
            cursor.execute(
                """
                INSERT INTO train_class_seats (train_number,class_name,total_seats,available_seats)
                VALUES (?, ?, ?, ?)
                """,
                (train_number, class_name, total, total),
            )


def insert_bookings(connection):
    today = datetime.now().date()
    plus_three = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    plus_five = (today + timedelta(days=5)).strftime("%Y-%m-%d")
    plus_two = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    same_day = today.strftime("%Y-%m-%d")

    rows = [
        (
            "booking_owner",
            "TR300",
            "Pune",
            "Mumbai",
            plus_three,
            "SLEEPER",
            2,
            CLASS_FARES["SLEEPER"] * 2,
            "Booked",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            None,
            0,
        ),
        (
            "booking_owner",
            "TR500",
            "Bhopal",
            "Indore",
            same_day,
            "AC",
            1,
            CLASS_FARES["AC"],
            "Booked",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            None,
            0,
        ),
        (
            "booking_owner",
            "TR400",
            "Hyderabad",
            "Vijayawada",
            plus_five,
            "SLEEPER",
            1,
            CLASS_FARES["SLEEPER"],
            "Cancelled",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            CLASS_FARES["SLEEPER"],
        ),
        (
            "other_user",
            "TR200",
            "Delhi",
            "Agra",
            plus_two,
            "AC",
            2,
            CLASS_FARES["AC"] * 2,
            "Booked",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            None,
            0,
        ),
    ]

    cursor = connection.cursor()
    cursor.executemany(
        """
        INSERT INTO bookings (
            username,train_number,origin_station,destination_station,travel_date,
            preferred_class,ticket_count,total_fare,status,booked_at,cancelled_at,refund_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def adjust_available_seats(connection):
    cursor = connection.cursor()
    cursor.execute("UPDATE train_class_seats SET available_seats = total_seats")

    cursor.execute(
        """
        SELECT train_number, preferred_class, COALESCE(SUM(ticket_count), 0)
        FROM bookings
        WHERE LOWER(status) = 'booked'
        GROUP BY train_number, preferred_class
        """
    )

    for train_number, preferred_class, total_booked in cursor.fetchall():
        cursor.execute(
            """
            UPDATE train_class_seats
            SET available_seats = MAX(0, total_seats - ?)
            WHERE train_number = ? AND class_name = ?
            """,
            (total_booked, train_number, preferred_class),
        )


def print_summary():
    print("\nManual test data setup completed.")
    print(f"Database file: {get_db_path()}")
    print("\nLogin users:")
    print("- Admin: admin / admin123")
    print("- Customer active: user / user123")
    print("- Customer active: booking_owner / book123")
    print("- Customer active: other_user / other123")
    print("- Customer inactive: inactive_user / inactive123")

    print("\nTrains created:")
    print("- TR100: Chennai -> Trichy -> Madurai")
    print("- TR200: Delhi -> Agra")
    print("- TR300: Pune -> Lonavala -> Mumbai")
    print("- TR400: Hyderabad -> Vijayawada")
    print("- TR500: Bhopal -> Indore (near-term departure for cancellation-window checks)")

    print("\nBookings created (fixed IDs if DB was reset):")
    print("- ID 1: booking_owner, TR300, Booked, >24h case for full refund")
    print("- ID 2: booking_owner, TR500, Booked, near departure case for zero refund")
    print("- ID 3: booking_owner, TR400, Cancelled")
    print("- ID 4: other_user, TR200, Booked (ownership validation case)")

    print("\nManual test ideas:")
    print("1) Login with inactive_user/inactive123 should fail")
    print("2) Cancel ticket ID 1 as booking_owner with password book123 for full refund")
    print("3) Cancel ticket ID 2 as booking_owner with password book123 for zero refund")
    print("4) Try cancelling ticket ID 4 while logged in as booking_owner should fail ownership check")


def ask_confirmation():
    choice = input("This will reset train/customer/booking data in the app DB. Continue? (yes/no): ").strip().lower()
    return choice == "yes"


def main():
    parser = argparse.ArgumentParser(description="Seed manual testing data for Train Console app")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip reset confirmation prompt",
    )
    args = parser.parse_args()

    initialize_database()

    if not args.yes and not ask_confirmation():
        print("Setup cancelled. No changes were made.")
        return

    with get_connection() as connection:
        ensure_booking_tables(connection)
        reset_core_tables(connection)
        insert_customers(connection)
        insert_trains(connection)
        initialize_seats_for_all_trains(connection)
        insert_bookings(connection)
        adjust_available_seats(connection)
        connection.commit()

    print_summary()


if __name__ == "__main__":
    main()
