import re
import sqlite3

from config import (DB_ERROR_MESSAGE, INCOMPLETE_INPUT_MESSAGE,INVALID_OPTION_MESSAGE, INVALID_ROUTE_MESSAGE,INVALID_STATION_NAME_MESSAGE, INVALID_TIME_FORMAT_MESSAGE,INVALID_TRAIN_NAME_MESSAGE, INVALID_TRAIN_NUMBER_MESSAGE,TRAIN_ALREADY_EXISTS_MESSAGE, TRAIN_CONFLICT_MESSAGE,TRAIN_NOT_FOUND_MESSAGE, TRAIN_REGISTERED_MESSAGE,TRAIN_UPDATE_CANCELLED_MESSAGE,TRAIN_UPDATE_SUCCESS_MESSAGE)
from data.db import get_connection, initialize_database


def is_blank(value):
    return not value or value.strip() == ""

def is_valid_train_number(train_number):
    return re.fullmatch(r"[A-Za-z0-9-]{2,20}", train_number or "") is not None


def is_valid_train_name(train_name):
    return re.fullmatch(r"[A-Za-z0-9 .'-]{2,60}", train_name or "") is not None


def is_valid_station_name(station_name):
    return re.fullmatch(r"[A-Za-z .'-]{2,60}", station_name or "") is not None


def is_valid_time(time_value):
    return re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", time_value or "") is not None


def get_stops_list(stops_text):
    return [item.strip() for item in (stops_text or "").split(",") if item.strip()]


def is_valid_route(origin, destination, intermediate_stops):
    if is_blank(origin) or is_blank(destination):
        print(INCOMPLETE_INPUT_MESSAGE)
        return False

    if origin.lower() == destination.lower():
        print(INVALID_ROUTE_MESSAGE)
        return False

    all_stations = [origin, destination] + intermediate_stops
    if any(not is_valid_station_name(station) for station in all_stations):
        print(INVALID_STATION_NAME_MESSAGE)
        return False

    return True


def collect_schedule(stations):
    schedule = []

    for index, station_name in enumerate(stations, 1):
        arrival_time = input(f"Arrival time at {station_name} (HH:MM): ").strip()
        departure_time = input(f"Departure time at {station_name} (HH:MM): ").strip()

        if is_blank(arrival_time) or is_blank(departure_time):
            print(INCOMPLETE_INPUT_MESSAGE)
            return None
        if not is_valid_time(arrival_time) or not is_valid_time(departure_time):
            print(INVALID_TIME_FORMAT_MESSAGE)
            return None

        schedule.append((index, station_name, arrival_time, departure_time))

    return schedule

def train_number_exists(connection, train_number):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT 1 FROM trains WHERE train_number = ? LIMIT 1",
        (train_number,),
    )
    return cursor.fetchone() is not None

def save_train(connection, train_number, train_name, origin, destination, intermediate_stops, schedule):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO trains (train_number,train_name,origin_station,destination_station,intermediate_stops) VALUES (?, ?, ?, ?, ?)
        """,
        (train_number,train_name,origin,destination,", ".join(intermediate_stops),),)

    for stop_order, station_name, arrival_time, departure_time in schedule:
        cursor.execute(
            """
            INSERT INTO train_stops (train_number,stop_order,station_name,arrival_time,departure_time) VALUES (?, ?, ?, ?, ?)
            """,
            (train_number,stop_order,station_name,arrival_time,departure_time,),
        )

def get_train_details(connection, train_number):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT train_number,train_name,origin_station,destination_station,intermediate_stops FROM trains WHERE train_number = ?
        """,
        (train_number,),
    )
    train_row = cursor.fetchone()

    if train_row is None:
        return None

    cursor.execute(
        """
        SELECT stop_order,station_name,arrival_time,departure_time FROM train_stops WHERE train_number = ? ORDER BY stop_order ASC """,(train_number,),
    )

    return {
        "train_number": train_row[0],
        "train_name": train_row[1],
        "origin_station": train_row[2],
        "destination_station": train_row[3],
        "intermediate_stops": train_row[4],
        "schedule": cursor.fetchall(),
    }


def show_train_details(train_details):
    print(f"Train Number: {train_details['train_number']}")
    print(f"Train Name: {train_details['train_name']}")
    print(f"Origin Station: {train_details['origin_station']}")
    print(f"Destination Station: {train_details['destination_station']}")

    intermediate_stops = train_details["intermediate_stops"].strip()
    print(f"Intermediate Stops: {intermediate_stops if intermediate_stops else 'None'}")
    print("Schedule:")

    for stop_order, station_name, arrival_time, departure_time in train_details["schedule"]:
        print(
            f"{stop_order}. {station_name} - Arrival: {arrival_time}, Departure: {departure_time}"
        )


def schedule_conflict_exists(connection, train_number, origin, destination, departure_time, arrival_time):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM trains t
        JOIN train_stops first_stop
            ON first_stop.train_number = t.train_number
            AND first_stop.stop_order = (
                SELECT MIN(s1.stop_order)
                FROM train_stops s1
                WHERE s1.train_number = t.train_number
            )
        JOIN train_stops last_stop
            ON last_stop.train_number = t.train_number
            AND last_stop.stop_order = (
                SELECT MAX(s2.stop_order)
                FROM train_stops s2
                WHERE s2.train_number = t.train_number
            )
        WHERE t.train_number != ?
            AND LOWER(TRIM(t.origin_station)) = LOWER(TRIM(?))
            AND LOWER(TRIM(t.destination_station)) = LOWER(TRIM(?))
            AND first_stop.departure_time = ?
            AND last_stop.arrival_time = ?
        LIMIT 1
        """,
        (train_number, origin, destination, departure_time, arrival_time),
    )
    return cursor.fetchone() is not None


def replace_schedule(connection, train_number, schedule):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM train_stops WHERE train_number = ?", (train_number,))

    for stop_order, station_name, arrival_time, departure_time in schedule:
        cursor.execute(
            """
            INSERT INTO train_stops (train_number,stop_order,station_name,arrival_time,departure_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (train_number, stop_order, station_name, arrival_time, departure_time),
        )
def update_train_name(connection, train_number):
    new_train_name = input("Enter new Train Name: ").strip()

    if is_blank(new_train_name):
        print(INCOMPLETE_INPUT_MESSAGE)
        return False

    if not is_valid_train_name(new_train_name):
        print(INVALID_TRAIN_NAME_MESSAGE)
        return False

    cursor = connection.cursor()
    cursor.execute(
        "UPDATE trains SET train_name = ? WHERE train_number = ?",
        (new_train_name, train_number),
    )
    return True


def update_route_or_schedule(connection, train_number, train_details, with_route):
    if with_route:
        origin = input("Enter new Origin Station: ").strip()
        destination = input("Enter new Destination Station: ").strip()
        intermediate_stops = get_stops_list(
            input("Enter new Intermediate Stops separated by comma (or press Enter to skip): ").strip()
        )
        if not is_valid_route(origin, destination, intermediate_stops):
            return False
    else:
        origin = train_details["origin_station"]
        destination = train_details["destination_station"]
        intermediate_stops = get_stops_list(train_details["intermediate_stops"])

    schedule = collect_schedule([origin] + intermediate_stops + [destination])
    if schedule is None:
        return False

    if schedule_conflict_exists(
        connection,
        train_number,
        origin,
        destination,
        schedule[0][3],
        schedule[-1][2],
    ):
        print(TRAIN_CONFLICT_MESSAGE)
        return False

    if with_route:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE trains
            SET origin_station = ?, destination_station = ?, intermediate_stops = ?
            WHERE train_number = ?
            """,
            (origin, destination, ", ".join(intermediate_stops), train_number),
        )

    replace_schedule(connection, train_number, schedule)
    return True


def admin_train_registration():
    initialize_database()

    train_number = input("Enter Train Number: ").strip()
    train_name = input("Enter Train Name: ").strip()
    origin = input("Enter Origin Station: ").strip()
    destination = input("Enter Destination Station: ").strip()
    intermediate_stops_text = input(
        "Enter Intermediate Stops separated by comma (or press Enter to skip): "
    ).strip()

    if is_blank(train_number) or is_blank(train_name) or is_blank(origin) or is_blank(destination):
        print(INCOMPLETE_INPUT_MESSAGE)
        return

    if not is_valid_train_number(train_number):
        print(INVALID_TRAIN_NUMBER_MESSAGE)
        return

    if not is_valid_train_name(train_name):
        print(INVALID_TRAIN_NAME_MESSAGE)
        return

    intermediate_stops = get_stops_list(intermediate_stops_text)
    if not is_valid_route(origin, destination, intermediate_stops):
        return

    try:
        with get_connection() as connection:
            if train_number_exists(connection, train_number):
                print(TRAIN_ALREADY_EXISTS_MESSAGE)
                return

            schedule = collect_schedule([origin] + intermediate_stops + [destination])

            if schedule is None:
                return

            save_train(connection,train_number,train_name,origin,destination,intermediate_stops,schedule,)
            connection.commit()

        print(TRAIN_REGISTERED_MESSAGE)
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)


def train_details_update_by_admin():
    initialize_database()

    train_number = input("Enter Train Number to search: ").strip()

    if is_blank(train_number):
        print(INCOMPLETE_INPUT_MESSAGE)
        return

    if not is_valid_train_number(train_number):
        print(INVALID_TRAIN_NUMBER_MESSAGE)
        return

    try:
        with get_connection() as connection:
            train_details = get_train_details(connection, train_number)

            if train_details is None:
                print(TRAIN_NOT_FOUND_MESSAGE)
                return

            print("Train found:")
            show_train_details(train_details)

            print("\nSelect what you want to update:")
            print("1) Train Name")
            print("2) Route and Schedule")
            print("3) Schedule Timings")
            print("4) Cancel")

            update_choice = input("Enter your choice: ").strip()

            if update_choice == "4":
                print(TRAIN_UPDATE_CANCELLED_MESSAGE)
                return

            action_map = {
                "1": lambda: update_train_name(connection, train_number),
                "2": lambda: update_route_or_schedule(connection, train_number, train_details, True),
                "3": lambda: update_route_or_schedule(connection, train_number, train_details, False),
            }
            action = action_map.get(update_choice)
            if action is None:
                print(INVALID_OPTION_MESSAGE)
                return

            is_updated = action()

            if not is_updated:
                return

            connection.commit()
            print(TRAIN_UPDATE_SUCCESS_MESSAGE)
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)

def delete_train_by_admin():
    print("Delete Train by Admin operation selected.")
