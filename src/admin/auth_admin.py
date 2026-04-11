from admin.train_management import (admin_train_registration,delete_train_by_admin,train_details_update_by_admin)
from config import (ADMIN_PASSWORD, ADMIN_USERNAME, GOODBYE_MESSAGE,INVALID_OPTION_MESSAGE, LOGIN_FAILURE_MESSAGE)


def admin_login():
    while True:
        username = input("UserName: ").strip()
        password = input("Password: ").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return True

        print(LOGIN_FAILURE_MESSAGE)


def show_admin_menu():
    while True:
        print("\nAdmin Menu")
        print("1) Admin Train Registration")
        print("2) Train Details Update by Admin")
        print("3) Delete Train by Admin")
        print("4) Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            admin_train_registration()
        elif choice == "2":
            train_details_update_by_admin()
        elif choice == "3":
            delete_train_by_admin()
        elif choice == "4":
            print(GOODBYE_MESSAGE)
            break
        else:
            print(INVALID_OPTION_MESSAGE)


def run_admin_portal():
    if admin_login():
        show_admin_menu()
