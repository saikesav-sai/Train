import re
import sqlite3

from config import DB_ERROR_MESSAGE
from data.db import get_connection, initialize_database


def is_valid_name(name):
    return re.fullmatch(r"[A-Za-z ]+", name or "") is not None


def is_valid_email(email):
    return re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email or "") is not None


def is_valid_phone(phone):
    return re.fullmatch(r"\d{10}", phone or "") is not None


def customer_registration():
    initialize_database()

    name = input("Enter Name: ").strip()
    username = input("Enter UserName: ").strip()
    email = input("Enter Email: ").strip()
    phone = input("Enter Phone Number: ").strip()
    password = input("Enter Password: ").strip()
    address = input("Enter Address: ").strip()

    if not name or not username or not email or not phone or not password or not address:
        print("Incomplete input. Please provide all required customer details.")
        return

    if not is_valid_name(name):
        print("Invalid name. Name should contain only letters and spaces.")
        return

    if not is_valid_email(email):
        print("Invalid email format.")
        return

    if not is_valid_phone(phone):
        print("Invalid phone number. Enter exactly 10 digits.")
        return

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT 1 FROM customers WHERE username = ? OR LOWER(email) = LOWER(?) OR phone = ? LIMIT 1",
                (username, email, phone),
            )
            if cursor.fetchone() is not None:
                print("Customer with same username, email or phone already exists.")
                return

            cursor.execute(
                """
                INSERT INTO customers (name,email,phone,address,username,password,is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (name, email, phone, address, username, password),
            )
            connection.commit()

        print("Customer registered successfully.")
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)

def customer_details_update(logged_in_username):
    initialize_database()

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT name,email,phone,address FROM customers WHERE username = ? AND is_active = 1 LIMIT 1",
                (logged_in_username,),
            )
            row = cursor.fetchone()
            if row is None:
                print("Customer details not found.")
                return

            current_name, current_email, current_phone, current_address = row
            name = input(f"Enter Name [{current_name or ''}]: ").strip() or (current_name or "")
            email = input(f"Enter Email [{current_email or ''}]: ").strip() or (current_email or "")
            phone = input(f"Enter Phone Number [{current_phone or ''}]: ").strip() or (current_phone or "")
            address = input(f"Enter Address [{current_address or ''}]: ").strip() or (current_address or "")

            if not name or not email or not phone or not address:
                print("Incomplete input. Please provide all required customer details.")
                return

            if not is_valid_name(name):
                print("Invalid name. Name should contain only letters and spaces.")
                return

            if not is_valid_email(email):
                print("Invalid email format.")
                return

            if not is_valid_phone(phone):
                print("Invalid phone number. Enter exactly 10 digits.")
                return

            cursor.execute(
                "SELECT 1 FROM customers WHERE (LOWER(email) = LOWER(?) OR phone = ?) AND username != ? LIMIT 1",
                (email, phone, logged_in_username),
            )
            if cursor.fetchone() is not None:
                print("Customer with same email or phone already exists.")
                return

            cursor.execute(
                """
                UPDATE customers
                SET name = ?, email = ?, phone = ?, address = ?
                WHERE username = ? AND is_active = 1
                """,
                (name, email, phone, address, logged_in_username),
            )
            connection.commit()
            print("Customer details updated successfully.")
    except sqlite3.Error:
        print(DB_ERROR_MESSAGE)

def customer_soft_delete():
    print("Customer Soft Delete operation selected.")
