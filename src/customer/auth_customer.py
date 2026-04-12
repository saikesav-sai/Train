from config import (GOODBYE_USER_MESSAGE, INVALID_OPTION_MESSAGE,
                    LOGIN_FAILURE_MESSAGE)
from customer.booking import (display_available_trains, ticket_cancellation,
                              train_ticket_booking, view_booking_history)
from customer.profile import (customer_details_update, customer_registration,
                              customer_soft_delete)
from data.db import get_connection, initialize_database


def is_customer_login_valid(username, password):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT 1 FROM customers WHERE username = ? AND password = ? AND is_active = 1 LIMIT 1",
            (username, password),
        )
        return cursor.fetchone() is not None


def customer_login():
    initialize_database()
    while True:
        username = input("UserName: ").strip()
        password = input("Password: ").strip()

        if is_customer_login_valid(username, password):
            return username

        print(LOGIN_FAILURE_MESSAGE)


def show_customer_menu(logged_in_username):
    while True:
        print("\nCustomer Menu")
        print("1) Customer Registration")
        print("2) Customer Details Update")
        print("3) Customer Soft Delete")
        print("4) Display Available Trains")
        print("5) Train Ticket Booking")
        print("6) Ticket Cancellation")
        print("7) View Booking History")
        print("8) Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            customer_registration()
        elif choice == "2":
            customer_details_update(logged_in_username)
        elif choice == "3":
            if customer_soft_delete(logged_in_username):
                print(GOODBYE_USER_MESSAGE)
                break
        elif choice == "4":
            display_available_trains()
        elif choice == "5":
            train_ticket_booking(logged_in_username)
        elif choice == "6":
            ticket_cancellation(logged_in_username)
        elif choice == "7":
            view_booking_history(logged_in_username)
        elif choice == "8":
            print(GOODBYE_USER_MESSAGE)
            break
        else:
            print(INVALID_OPTION_MESSAGE)


def run_customer_portal():
    while True:
        print("\nCustomer Access")
        print("1) Login")
        print("2) Register")
        print("3) Back")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            logged_in_username = customer_login()
            show_customer_menu(logged_in_username)
        elif choice == "2":
            customer_registration()
        elif choice == "3":
            break
        else:
            print(INVALID_OPTION_MESSAGE)
