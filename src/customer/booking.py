import sqlite3
from datetime import datetime, timedelta

from config import DB_ERROR_MESSAGE
from data.db import get_connection, initialize_database


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

def train_ticket_booking():
    print("Train Ticket Booking operation selected.")
def ticket_cancellation():
    print("Ticket Cancellation operation selected.")

def view_booking_history():
    print("View Booking History operation selected.")
