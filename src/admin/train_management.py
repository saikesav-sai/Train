import sqlite3

from config import (DB_ERROR_MESSAGE, INCOMPLETE_INPUT_MESSAGE,INVALID_ROUTE_MESSAGE, TRAIN_ALREADY_EXISTS_MESSAGE,TRAIN_REGISTERED_MESSAGE)
from data.db import get_connection, initialize_database


def is_blank(value):
    return not value or value.strip() == ""

def get_stops_list(stops_text):
    if is_blank(stops_text):
        return []
    raw_items = stops_text.split(",")
    stops = []
    for item in raw_items:
        stop = item.strip()
        if stop:
            stops.append(stop)
    return stops

def ask_schedule(origin, destination, intermediate_stops):
    stations = [origin] + intermediate_stops + [destination]
    schedule = []

    for index, station_name in enumerate(stations, 1):
        arrival_time = input(f"Arrival time at {station_name} (HH:MM): ").strip()
        departure_time = input(f"Departure time at {station_name} (HH:MM): ").strip()

        if is_blank(arrival_time) or is_blank(departure_time):
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


def admin_train_registration():
    initialize_database()

    train_number = input("Enter Train Number: ").strip()
    train_name = input("Enter Train Name: ").strip()
    origin = input("Enter Origin Station: ").strip()
    destination = input("Enter Destination Station: ").strip()
    intermediate_stops_text = input(
        "Enter Intermediate Stops separated by comma (or press Enter to skip): "
    ).strip()

    if (
        is_blank(train_number)
        or is_blank(train_name)
        or is_blank(origin)
        or is_blank(destination)
    ):
        print(INCOMPLETE_INPUT_MESSAGE)
        return

    if origin.lower() == destination.lower():
        print(INVALID_ROUTE_MESSAGE)
        return

    try:
        with get_connection() as connection:
            if train_number_exists(connection, train_number):
                print(TRAIN_ALREADY_EXISTS_MESSAGE)
                return

            intermediate_stops = get_stops_list(intermediate_stops_text)
            schedule = ask_schedule(origin, destination, intermediate_stops)

            if schedule is None:
                print(INCOMPLETE_INPUT_MESSAGE)
                return

            save_train(connection,train_number,train_name,origin,destination,intermediate_stops,schedule,)
            connection.commit()

        print(TRAIN_REGISTERED_MESSAGE)
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)


def train_details_update_by_admin():
    print("Train Details Update by Admin operation selected.")

def delete_train_by_admin():
    print("Delete Train by Admin operation selected.")
