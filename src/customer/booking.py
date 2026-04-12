import sqlite3
from datetime import datetime, timedelta

from config import DB_ERROR_MESSAGE
from data.db import get_connection, initialize_database

CLASS_FARES = {"SLEEPER": 200, "AC": 500}
DEFAULT_CLASS_CAPACITY = {"SLEEPER": 100, "AC": 50}
SESSION_BOOKED_TICKETS = {}


def parse_travel_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_station_available(connection, station_name):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT 1 FROM train_stops WHERE LOWER(TRIM(station_name)) = LOWER(TRIM(?)) LIMIT 1",
        (station_name,),
    )
    return cursor.fetchone() is not None


def get_duration_text(departure_time, arrival_time):
    departure = datetime.strptime(departure_time, "%H:%M")
    arrival = datetime.strptime(arrival_time, "%H:%M")
    total_minutes = int((arrival - departure).total_seconds() // 60)
    if total_minutes < 0:
        total_minutes += 24 * 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes}m"


def display_available_trains():
    initialize_database()

    origin = input("Enter Origin Station: ").strip()
    destination = input("Enter Destination Station: ").strip()
    travel_date_input = input("Enter Travel Date (YYYY-MM-DD): ").strip()

    if not origin or not destination or not travel_date_input:
        print("Incomplete input. Please provide origin, destination and travel date.")
        return

    if origin.lower() == destination.lower():
        print("Origin and destination must be different.")
        return

    travel_date = parse_travel_date(travel_date_input)
    if travel_date is None:
        print("Invalid travel date format. Use YYYY-MM-DD.")
        return

    today = datetime.today().date()
    max_date = today + timedelta(days=90)
    if travel_date < today or travel_date > max_date:
        print("Travel date must be within the next 3 months.")
        return

    try:
        with get_connection() as connection:
            if not is_station_available(connection, origin) or not is_station_available(connection, destination):
                print("Origin or destination station does not exist in the database.")
                return

            cursor = connection.cursor()
            cursor.execute(
                """ SELECT t.train_number,t.train_name,o.departure_time,d.arrival_time FROM trains t JOIN train_stops o ON o.train_number = t.train_number AND LOWER(TRIM(o.station_name)) = LOWER(TRIM(?)) JOIN train_stops d ON d.train_number = t.train_number AND LOWER(TRIM(d.station_name)) = LOWER(TRIM(?)) WHERE o.stop_order < d.stop_order ORDER BY t.train_number """,
                (origin, destination),
            )
            trains = cursor.fetchall()

        if not trains:
            print("No available trains found for the selected route and date.")
            return

        print(f"Available trains for {origin} to {destination} on {travel_date_input}:")
        for train_number, train_name, departure_time, arrival_time in trains:
            duration = get_duration_text(departure_time, arrival_time)
            print(f"Train Number: {train_number}")
            print(f"Train Name: {train_name}")
            print(f"Departure Time: {departure_time}")
            print(f"Arrival Time: {arrival_time}")
            print(f"Travel Duration: {duration}")
            print("Available Classes: Sleeper, AC")
            print("-" * 40)
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)


def ensure_booking_tables(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (booking_id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL,train_number TEXT NOT NULL,origin_station TEXT NOT NULL,destination_station TEXT NOT NULL,travel_date TEXT NOT NULL,preferred_class TEXT NOT NULL,ticket_count INTEGER NOT NULL,total_fare REAL NOT NULL,status TEXT NOT NULL,booked_at TEXT NOT NULL,FOREIGN KEY (train_number) REFERENCES trains(train_number))
        """
    )
    cursor.execute("PRAGMA table_info(bookings)")
    columns = {row[1] for row in cursor.fetchall()}
    if "cancelled_at" not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN cancelled_at TEXT")
    if "refund_amount" not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN refund_amount REAL DEFAULT 0")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS train_class_seats (train_number TEXT NOT NULL,class_name TEXT NOT NULL,total_seats INTEGER NOT NULL,available_seats INTEGER NOT NULL,PRIMARY KEY (train_number, class_name),FOREIGN KEY (train_number) REFERENCES trains(train_number) ON DELETE CASCADE)
        """
    )


def ensure_class_seats_for_train(connection, train_number):
    cursor = connection.cursor()
    for class_name in DEFAULT_CLASS_CAPACITY:
        cursor.execute(
            """
            INSERT OR IGNORE INTO train_class_seats (train_number,class_name,total_seats,available_seats)
            VALUES (?, ?, ?, ?)
            """,
            (train_number, class_name, DEFAULT_CLASS_CAPACITY[class_name], DEFAULT_CLASS_CAPACITY[class_name]),
        )


def get_train_route_details(connection, train_number, origin, destination):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT t.train_number,t.train_name,o.departure_time,d.arrival_time FROM trains t JOIN train_stops o ON o.train_number = t.train_number AND LOWER(TRIM(o.station_name)) = LOWER(TRIM(?)) JOIN train_stops d ON d.train_number = t.train_number AND LOWER(TRIM(d.station_name)) = LOWER(TRIM(?)) WHERE t.train_number = ? AND o.stop_order < d.stop_order LIMIT 1 """, (origin, destination, train_number),
    )
    return cursor.fetchone()


def get_available_seats(connection, train_number, preferred_class):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT available_seats
        FROM train_class_seats
        WHERE train_number = ? AND class_name = ?
        LIMIT 1
        """,
        (train_number, preferred_class),
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def train_ticket_booking(logged_in_username):
    initialize_database()

    train_number = input("Enter Train Number: ").strip()
    origin = input("Enter Origin Station: ").strip()
    destination = input("Enter Destination Station: ").strip()
    travel_date_input = input("Enter Travel Date (YYYY-MM-DD): ").strip()
    preferred_class = input("Enter Preferred Class (Sleeper/AC): ").strip().upper()
    ticket_count_input = input("Enter Number of Tickets: ").strip()

    if not train_number or not origin or not destination or not travel_date_input or not preferred_class or not ticket_count_input:
        print("Incomplete input. Please provide all booking details.")
        return

    if origin.lower() == destination.lower():
        print("Origin and destination must be different.")
        return

    travel_date = parse_travel_date(travel_date_input)
    if travel_date is None:
        print("Invalid travel date format. Use YYYY-MM-DD.")
        return

    today = datetime.today().date()
    max_date = today + timedelta(days=90)
    if travel_date < today or travel_date > max_date:
        print("Travel date must be within the next 3 months.")
        return

    if preferred_class not in CLASS_FARES:
        print("Invalid class. Choose Sleeper or AC.")
        return

    if not ticket_count_input.isdigit():
        print("Invalid ticket count.")
        return

    ticket_count = int(ticket_count_input)
    if ticket_count <= 0:
        print("Ticket count must be greater than 0.")
        return

    session_used = SESSION_BOOKED_TICKETS.get(logged_in_username, 0)
    if session_used + ticket_count > 6:
        print("You cannot book more than 6 tickets in one session.")
        return

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT name,email,phone FROM customers WHERE username = ? AND is_active = 1 LIMIT 1",
                (logged_in_username,),
            )
            customer_row = cursor.fetchone()
            if customer_row is None:
                print("Customer details not found for booking.")
                return

            if not is_station_available(connection, origin) or not is_station_available(connection, destination):
                print("Origin or destination station does not exist in the database.")
                return

            ensure_booking_tables(connection)

            train_row = get_train_route_details(connection, train_number, origin, destination)
            if train_row is None:
                print("Invalid train number or route.")
                return

            ensure_class_seats_for_train(connection, train_number)

            available_seats = get_available_seats(connection, train_number, preferred_class)
            if available_seats < ticket_count:
                print("Requested seats are not available.")
                return

            fare_per_ticket = CLASS_FARES[preferred_class]
            total_fare = fare_per_ticket * ticket_count

            print(f"Total Fare: {total_fare}")
            confirmation = input("Confirm booking? (yes/amend): ").strip().lower()
            if confirmation == "amend":
                print("Booking amend selected. Restart booking.")
                return
            if confirmation != "yes":
                print("Booking cancelled.")
                return

            booked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO bookings (username,train_number,origin_station,destination_station,travel_date,preferred_class,ticket_count,total_fare,status,booked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Booked', ?)
                """,
                (logged_in_username,train_number,origin,destination,travel_date_input,preferred_class,ticket_count,total_fare,booked_at,),
            )
            booking_id = cursor.lastrowid

            cursor.execute(
                """
                UPDATE train_class_seats SET available_seats = available_seats - ? WHERE train_number = ? AND class_name = ?
                """,
                (ticket_count, train_number, preferred_class),
            )

            connection.commit()
            SESSION_BOOKED_TICKETS[logged_in_username] = session_used + ticket_count

            train_number_value, train_name, departure_time, arrival_time = train_row
            print("Ticket Booked Successfully")
            print(f"Ticket ID: {booking_id}")
            print(f"Customer: {customer_row[0] or logged_in_username}")
            print(f"Train Number: {train_number_value}")
            print(f"Train Name: {train_name}")
            print(f"Route: {origin} -> {destination}")
            print(f"Travel Date: {travel_date_input}")
            print(f"Departure Time: {departure_time}")
            print(f"Arrival Time: {arrival_time}")
            print(f"Class: {preferred_class}")
            print(f"Tickets: {ticket_count}")
            print(f"Total Fare: {total_fare}")
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)


def ticket_cancellation(logged_in_username):
    initialize_database()

    ticket_id_input = input("Enter Ticket ID: ").strip()
    password = input("Enter Password: ").strip()

    if not ticket_id_input or not password:
        print("Incomplete input. Please provide ticket id and password.")
        return

    if not ticket_id_input.isdigit():
        print("Invalid Ticket ID.")
        return

    ticket_id = int(ticket_id_input)

    try:
        with get_connection() as connection:
            ensure_booking_tables(connection)
            cursor = connection.cursor()

            cursor.execute(
                "SELECT 1 FROM customers WHERE username = ? AND password = ? AND is_active = 1 LIMIT 1",
                (logged_in_username, password),
            )
            if cursor.fetchone() is None:
                print("Please Enter Correct UserName and Password")
                return

            cursor.execute(
                """
                SELECT booking_id,username,train_number,origin_station,travel_date,preferred_class,ticket_count,total_fare,status FROM bookings WHERE booking_id = ? LIMIT 1
                """,
                (ticket_id,),
            )
            booking = cursor.fetchone()
            if booking is None:
                print("Ticket ID does not exist.")
                return

            booking_id, username, train_number, origin_station, travel_date, preferred_class, ticket_count, total_fare, status = booking

            if username != logged_in_username:
                print("Ticket does not belong to logged in customer.")
                return

            if (status or "").lower() == "cancelled":
                print("Ticket is already cancelled.")
                return

            cursor.execute(
                """
                SELECT departure_time FROM train_stops WHERE train_number = ? AND LOWER(TRIM(station_name)) = LOWER(TRIM(?)) LIMIT 1 """,
                (train_number, origin_station),
            )
            stop_row = cursor.fetchone()
            if stop_row is None:
                print("Unable to validate cancellation window.")
                return

            departure_time = stop_row[0]
            departure_datetime = datetime.strptime(f"{travel_date} {departure_time}", "%Y-%m-%d %H:%M")
            now = datetime.now()

            if now >= departure_datetime:
                print("Cancellation window has closed for this ticket.")
                return

            confirm = input("Confirm cancellation? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("Ticket cancellation aborted.")
                return

            hours_left = (departure_datetime - now).total_seconds() / 3600
            refund_amount = total_fare if hours_left > 24 else 0
            cancelled_at = now.strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """
                UPDATE bookings SET status = 'Cancelled', cancelled_at = ?, refund_amount = ? WHERE booking_id = ?
                """,
                (cancelled_at, refund_amount, booking_id),
            )

            ensure_class_seats_for_train(connection, train_number)
            cursor.execute(
                """
                UPDATE train_class_seats
                SET available_seats = MIN(total_seats, available_seats + ?)
                WHERE train_number = ? AND class_name = ?
                """,
                (ticket_count, train_number, preferred_class),
            )

            connection.commit()
            print("Ticket cancelled successfully.")
            print(f"Refund Amount: {refund_amount}")
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)


def view_booking_history(logged_in_username):
    initialize_database()

    try:
        with get_connection() as connection:
            ensure_booking_tables(connection)
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT b.travel_date,b.train_number,COALESCE(t.train_name, 'N/A'),b.status
                FROM bookings b
                LEFT JOIN trains t ON t.train_number = b.train_number
                WHERE b.username = ?
                ORDER BY b.travel_date DESC, b.booking_id DESC
                """,
                (logged_in_username,),
            )
            history_rows = cursor.fetchall()

        if not history_rows:
            print("No booking history found for this customer.")
            return

        print("Booking History")
        print(f"{'Date':<12} {'Train Number':<15} {'Train Name':<25} {'Status':<12}")
        print("-" * 70)
        for travel_date, train_number, train_name, status in history_rows:
            print(f"{travel_date:<12} {train_number:<15} {train_name:<25} {status:<12}")
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)
