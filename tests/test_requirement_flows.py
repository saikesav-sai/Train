import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import data.db as db
from admin.auth_admin import admin_login, show_admin_menu
from admin.train_management import (admin_train_registration,
                                    delete_train_by_admin,
                                    train_details_update_by_admin)
from config import (DB_ERROR_MESSAGE, GOODBYE_USER_MESSAGE,
                    INCOMPLETE_INPUT_MESSAGE, INVALID_OPTION_MESSAGE,
                    LOGIN_FAILURE_MESSAGE, TRAIN_ALREADY_EXISTS_MESSAGE,
                    TRAIN_CONFLICT_MESSAGE, TRAIN_DELETE_SUCCESS_MESSAGE,
                    TRAIN_REGISTERED_MESSAGE, TRAIN_UPDATE_SUCCESS_MESSAGE)
from customer.auth_customer import (customer_login, is_customer_login_valid,
                                    show_customer_menu)
from customer.booking import (CLASS_FARES, DEFAULT_CLASS_CAPACITY,
                              SESSION_BOOKED_TICKETS, display_available_trains,
                              ensure_booking_tables, ticket_cancellation,
                              train_ticket_booking, view_booking_history)
from customer.profile import (customer_details_update, customer_registration,
                              customer_soft_delete)


class RequirementFlowTests(unittest.TestCase):
    def setUp(self):
        self.original_db_file_name = db.DB_FILE_NAME
        self.test_db_file_name = f"test_{uuid4().hex}.db"
        db.DB_FILE_NAME = self.test_db_file_name
        SESSION_BOOKED_TICKETS.clear()

    def tearDown(self):
        test_db_path = db.get_db_path()
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        db.DB_FILE_NAME = self.original_db_file_name
        SESSION_BOOKED_TICKETS.clear()

    def run_with_inputs(self, func, inputs, *args):
        output_buffer = io.StringIO()
        with patch("builtins.input", side_effect=inputs):
            with redirect_stdout(output_buffer):
                result = func(*args)
        return result, output_buffer.getvalue()

    def add_customer(self, username, password, name="Test User", email="test@example.com", phone="9876543210", address="Test Street"):
        db.initialize_database()
        with db.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO customers (name,email,phone,address,username,password,is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (name, email, phone, address, username, password),
            )
            connection.commit()

    def add_train(self, train_number, origin, destination, departure_time, arrival_time, train_name="Demo Express"):
        db.initialize_database()
        with db.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO trains (train_number,train_name,origin_station,destination_station,intermediate_stops)
                VALUES (?, ?, ?, ?, ?)
                """,
                (train_number, train_name, origin, destination, ""),
            )
            connection.execute(
                """
                INSERT INTO train_stops (train_number,stop_order,station_name,arrival_time,departure_time)
                VALUES (?, 1, ?, ?, ?)
                """,
                (train_number, origin, departure_time, departure_time),
            )
            connection.execute(
                """
                INSERT INTO train_stops (train_number,stop_order,station_name,arrival_time,departure_time)
                VALUES (?, 2, ?, ?, ?)
                """,
                (train_number, destination, arrival_time, arrival_time),
            )
            connection.commit()

    def add_booking(self, username, train_number, origin, destination, travel_date, preferred_class, ticket_count, total_fare, status="Booked"):
        db.initialize_database()
        with db.get_connection() as connection:
            ensure_booking_tables(connection)
            connection.execute(
                """
                INSERT INTO bookings (username,train_number,origin_station,destination_station,travel_date,preferred_class,ticket_count,total_fare,status,booked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    train_number,
                    origin,
                    destination,
                    travel_date,
                    preferred_class,
                    ticket_count,
                    total_fare,
                    status,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            connection.commit()

    def get_booking_status(self, booking_id):
        with db.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT status FROM bookings WHERE booking_id = ?", (booking_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_train_exists(self, train_number):
        with db.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM trains WHERE train_number = ?", (train_number,))
            return cursor.fetchone() is not None

    def get_available_seats_for_class(self, train_number, class_name):
        with db.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT available_seats FROM train_class_seats WHERE train_number = ? AND class_name = ?",
                (train_number, class_name),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_booking_count(self, username):
        with db.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM bookings WHERE username = ?", (username,))
            return cursor.fetchone()[0]

    def test_admin_login_retry_then_success(self):
        _, output = self.run_with_inputs(
            admin_login,
            ["wrong", "nope", "admin", "admin123"],
        )
        self.assertIn(LOGIN_FAILURE_MESSAGE, output)

    def test_us001_admin_menu_invalid_option_message(self):
        _, output = self.run_with_inputs(show_admin_menu, ["99", "4"])
        self.assertIn(INVALID_OPTION_MESSAGE, output)

    def test_us001_admin_menu_routes_to_options(self):
        with patch("admin.auth_admin.admin_train_registration") as reg_mock, patch(
            "admin.auth_admin.train_details_update_by_admin"
        ) as upd_mock, patch("admin.auth_admin.delete_train_by_admin") as del_mock:
            self.run_with_inputs(show_admin_menu, ["1", "2", "3", "4"])

        reg_mock.assert_called_once()
        upd_mock.assert_called_once()
        del_mock.assert_called_once()

    def test_us001_admin_menu_exit_message_matches_requirement(self):
        _, output = self.run_with_inputs(show_admin_menu, ["4"])
        self.assertIn(GOODBYE_USER_MESSAGE, output)

    def test_admin_train_registration_and_duplicate_rejection(self):
        registration_inputs = [
            "T100",
            "Morning Star",
            "Chennai",
            "Madurai",
            "",
            "08:00",
            "08:10",
            "12:00",
            "12:10",
        ]
        _, first_output = self.run_with_inputs(admin_train_registration, registration_inputs)
        self.assertIn(TRAIN_REGISTERED_MESSAGE, first_output)

        _, duplicate_output = self.run_with_inputs(admin_train_registration, registration_inputs)
        self.assertIn(TRAIN_ALREADY_EXISTS_MESSAGE, duplicate_output)

    def test_us002_train_registration_incomplete_input(self):
        _, output = self.run_with_inputs(
            admin_train_registration,
            ["", "Demo", "Chennai", "Madurai", ""],
        )
        self.assertIn(INCOMPLETE_INPUT_MESSAGE, output)

    def test_us003_train_update_name_success(self):
        self.add_train("T101", "Chennai", "Trichy", "08:00", "12:00", "Old Name")
        _, output = self.run_with_inputs(
            train_details_update_by_admin,
            ["T101", "1", "New Name"],
        )
        self.assertIn(TRAIN_UPDATE_SUCCESS_MESSAGE, output)
        with db.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT train_name FROM trains WHERE train_number = ?", ("T101",))
            self.assertEqual(cursor.fetchone()[0], "New Name")

    def test_us003_schedule_conflict_prevented(self):
        self.add_train("T201", "Delhi", "Agra", "09:00", "11:00", "Alpha")
        self.add_train("T202", "Pune", "Mumbai", "10:00", "13:00", "Beta")

        _, output = self.run_with_inputs(
            train_details_update_by_admin,
            [
                "T202",
                "2",
                "Delhi",
                "Agra",
                "",
                "08:50",
                "09:00",
                "11:00",
                "11:10",
            ],
        )
        self.assertIn(TRAIN_CONFLICT_MESSAGE, output)

    def test_us004_delete_train_success_without_bookings(self):
        self.add_train("T301", "Hyd", "Vij", "06:00", "10:00")
        _, output = self.run_with_inputs(delete_train_by_admin, ["T301", "yes"])
        self.assertIn(TRAIN_DELETE_SUCCESS_MESSAGE, output)
        self.assertFalse(self.get_train_exists("T301"))

    def test_us004_delete_train_handles_associated_booking(self):
        self.add_customer(
            username="delete_user",
            password="pass123",
            name="Delete User",
            email="delete.user@example.com",
            phone="9000000101",
        )
        self.add_train("T302", "Hyd", "Vij", "07:00", "11:00")
        travel_date = (datetime.today().date() + timedelta(days=5)).strftime("%Y-%m-%d")
        self.add_booking("delete_user", "T302", "Hyd", "Vij", travel_date, "SLEEPER", 1, 200)

        _, output = self.run_with_inputs(delete_train_by_admin, ["T302", "yes"])
        self.assertNotIn(DB_ERROR_MESSAGE, output)
        with db.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT status FROM bookings WHERE train_number = ?", ("T302",))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "Cancelled")

    def test_us005_customer_login_failure_then_success(self):
        self.add_customer(
            username="login_ok",
            password="secret",
            name="Login Okay",
            email="login.ok@example.com",
            phone="9000000102",
        )
        _, output = self.run_with_inputs(customer_login, ["x", "y", "login_ok", "secret"])
        self.assertIn(LOGIN_FAILURE_MESSAGE, output)

    def test_us005_customer_menu_invalid_option_and_exit(self):
        _, output = self.run_with_inputs(show_customer_menu, ["99", "8"], "user")
        self.assertIn(INVALID_OPTION_MESSAGE, output)
        self.assertIn(GOODBYE_USER_MESSAGE, output)

    def test_us005_customer_menu_routes_to_options(self):
        with patch("customer.auth_customer.customer_registration") as reg_mock, patch(
            "customer.auth_customer.customer_details_update"
        ) as update_mock, patch("customer.auth_customer.customer_soft_delete", return_value=False) as soft_delete_mock, patch(
            "customer.auth_customer.display_available_trains"
        ) as available_mock, patch("customer.auth_customer.train_ticket_booking") as booking_mock, patch(
            "customer.auth_customer.ticket_cancellation"
        ) as cancel_mock, patch("customer.auth_customer.view_booking_history") as history_mock:
            self.run_with_inputs(show_customer_menu, ["1", "2", "3", "4", "5", "6", "7", "8"], "menu_user")

        reg_mock.assert_called_once()
        update_mock.assert_called_once_with("menu_user")
        soft_delete_mock.assert_called_once_with("menu_user")
        available_mock.assert_called_once()
        booking_mock.assert_called_once_with("menu_user")
        cancel_mock.assert_called_once_with("menu_user")
        history_mock.assert_called_once_with("menu_user")

    def test_customer_registration_invalid_email(self):
        _, output = self.run_with_inputs(
            customer_registration,
            ["Alice", "alice_user", "invalid-email", "9876543210", "pass123", "Some Address"],
        )
        self.assertIn("Invalid email format.", output)

    def test_us006_customer_registration_invalid_name_and_phone(self):
        _, name_output = self.run_with_inputs(
            customer_registration,
            ["Alice1", "alice_1", "alice1@example.com", "9876543210", "pass123", "Some Address"],
        )
        self.assertIn("Invalid name. Name should contain only letters and spaces.", name_output)

        _, phone_output = self.run_with_inputs(
            customer_registration,
            ["Alice", "alice_2", "alice2@example.com", "98765", "pass123", "Some Address"],
        )
        self.assertIn("Invalid phone number. Enter exactly 10 digits.", phone_output)

    def test_us006_customer_registration_duplicate_rejected(self):
        self.add_customer(
            username="dup_user",
            password="pass123",
            name="Dup User",
            email="dup.user@example.com",
            phone="9000000103",
        )
        _, output = self.run_with_inputs(
            customer_registration,
            ["Another User", "dup_user", "dup.user@example.com", "9000000103", "pass999", "Other Address"],
        )
        self.assertIn("Customer with same username, email or phone already exists.", output)

    def test_us007_customer_details_update_success(self):
        self.add_customer(
            username="update_user",
            password="pass123",
            name="Update User",
            email="update.user@example.com",
            phone="9000000104",
            address="Old Address",
        )

        _, output = self.run_with_inputs(
            customer_details_update,
            ["Updated User", "updated.user@example.com", "9000000999", "New Address"],
            "update_user",
        )
        self.assertIn("Customer details updated successfully.", output)

    def test_us008_customer_soft_delete_blocks_login(self):
        self.add_customer(
            username="login_user",
            password="pass123",
            name="Login User",
            email="login.user@example.com",
            phone="9000000001",
        )
        self.assertTrue(is_customer_login_valid("login_user", "pass123"))

        result, output = self.run_with_inputs(customer_soft_delete, ["yes"], "login_user")
        self.assertTrue(result)
        self.assertIn("Customer account deactivated successfully.", output)
        self.assertFalse(is_customer_login_valid("login_user", "pass123"))

    def test_us009_display_available_trains_success(self):
        self.add_train("T401", "Delhi", "Agra", "09:00", "11:00", "Fastline")
        travel_date = (datetime.today().date() + timedelta(days=4)).strftime("%Y-%m-%d")

        _, output = self.run_with_inputs(display_available_trains, ["Delhi", "Agra", travel_date])
        self.assertIn("Train Number: T401", output)
        self.assertIn("Train Name: Fastline", output)
        self.assertIn("Travel Duration:", output)
        self.assertIn("Available Classes: Sleeper, AC", output)

    def test_us009_display_available_trains_date_validation(self):
        self.add_train("T402", "Delhi", "Agra", "09:00", "11:00", "Window")
        past_date = (datetime.today().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        _, output = self.run_with_inputs(display_available_trains, ["Delhi", "Agra", past_date])
        self.assertIn("Travel date must be within the next 3 months.", output)

    def test_us009_display_available_trains_station_validation(self):
        future_date = (datetime.today().date() + timedelta(days=3)).strftime("%Y-%m-%d")
        _, output = self.run_with_inputs(display_available_trains, ["Nowhere", "Elsewhere", future_date])
        self.assertIn("Origin or destination station does not exist in the database.", output)

    def test_us010_booking_success_updates_seats(self):
        self.add_customer(
            username="book_user",
            password="pass123",
            name="Book User",
            email="book.user@example.com",
            phone="9000000105",
        )
        self.add_train("T501", "Pune", "Mumbai", "07:00", "10:00")
        travel_date = (datetime.today().date() + timedelta(days=2)).strftime("%Y-%m-%d")

        _, output = self.run_with_inputs(
            train_ticket_booking,
            ["T501", "Pune", "Mumbai", travel_date, "Sleeper", "2", "yes"],
            "book_user",
        )

        self.assertIn("Total Fare: 400", output)
        self.assertIn("Ticket Booked Successfully", output)
        expected_available = DEFAULT_CLASS_CAPACITY["SLEEPER"] - 2
        self.assertEqual(self.get_available_seats_for_class("T501", "SLEEPER"), expected_available)

    def test_us010_booking_amend_does_not_create_record(self):
        self.add_customer(
            username="amend_user",
            password="pass123",
            name="Amend User",
            email="amend.user@example.com",
            phone="9000000106",
        )
        self.add_train("T502", "Pune", "Mumbai", "07:00", "10:00")
        travel_date = (datetime.today().date() + timedelta(days=2)).strftime("%Y-%m-%d")

        _, output = self.run_with_inputs(
            train_ticket_booking,
            ["T502", "Pune", "Mumbai", travel_date, "AC", "1", "amend"],
            "amend_user",
        )
        self.assertIn("Booking amend selected. Restart booking.", output)
        self.assertEqual(self.get_booking_count("amend_user"), 0)

    def test_us010_booking_rejects_more_than_six_tickets_per_session(self):
        self.add_customer(
            username="limit_user",
            password="pass123",
            name="Limit User",
            email="limit.user@example.com",
            phone="9000000002",
        )
        self.add_train("T200", "Delhi", "Agra", "09:00", "11:00")
        SESSION_BOOKED_TICKETS["limit_user"] = 5

        travel_date = (datetime.today().date() + timedelta(days=2)).strftime("%Y-%m-%d")
        _, output = self.run_with_inputs(
            train_ticket_booking,
            ["T200", "Delhi", "Agra", travel_date, "Sleeper", "2"],
            "limit_user",
        )
        self.assertIn("You cannot book more than 6 tickets in one session.", output)

    def test_us011_ticket_cancellation_refund_full_when_more_than_24_hours(self):
        self.add_customer(
            username="refund_user",
            password="pass123",
            name="Refund User",
            email="refund.user@example.com",
            phone="9000000003",
        )
        self.add_train("T300", "Pune", "Mumbai", "10:00", "13:00")

        travel_date = (datetime.today().date() + timedelta(days=3)).strftime("%Y-%m-%d")
        _, booking_output = self.run_with_inputs(
            train_ticket_booking,
            ["T300", "Pune", "Mumbai", travel_date, "Sleeper", "2", "yes"],
            "refund_user",
        )
        self.assertIn("Ticket Booked Successfully", booking_output)

        _, cancellation_output = self.run_with_inputs(
            ticket_cancellation,
            ["1", "pass123", "yes"],
            "refund_user",
        )
        self.assertIn("Ticket cancelled successfully.", cancellation_output)
        self.assertIn("Refund Amount: 400", cancellation_output)

    def test_us011_ticket_cancellation_refund_zero_within_24_hours(self):
        self.add_customer(
            username="norefund_user",
            password="pass123",
            name="No Refund User",
            email="norefund.user@example.com",
            phone="9000000004",
        )

        travel_dt = datetime.now() + timedelta(hours=2)
        arrival_dt = travel_dt + timedelta(hours=1)
        self.add_train(
            "T301",
            "Bhopal",
            "Indore",
            travel_dt.strftime("%H:%M"),
            arrival_dt.strftime("%H:%M"),
        )

        travel_date = travel_dt.strftime("%Y-%m-%d")
        _, booking_output = self.run_with_inputs(
            train_ticket_booking,
            ["T301", "Bhopal", "Indore", travel_date, "AC", "1", "yes"],
            "norefund_user",
        )
        self.assertIn("Ticket Booked Successfully", booking_output)

        _, cancellation_output = self.run_with_inputs(
            ticket_cancellation,
            ["1", "pass123", "yes"],
            "norefund_user",
        )
        self.assertIn("Ticket cancelled successfully.", cancellation_output)
        self.assertIn("Refund Amount: 0", cancellation_output)

    def test_us011_ticket_cancellation_invalid_password(self):
        self.add_customer(
            username="pwd_user",
            password="pass123",
            name="Pwd User",
            email="pwd.user@example.com",
            phone="9000000107",
        )
        self.add_train("T503", "Kochi", "Goa", "07:00", "13:00")
        travel_date = (datetime.today().date() + timedelta(days=3)).strftime("%Y-%m-%d")
        self.add_booking("pwd_user", "T503", "Kochi", "Goa", travel_date, "SLEEPER", 1, CLASS_FARES["SLEEPER"])

        _, output = self.run_with_inputs(ticket_cancellation, ["1", "wrong"], "pwd_user")
        self.assertIn(LOGIN_FAILURE_MESSAGE, output)
        self.assertEqual(self.get_booking_status(1), "Booked")

    def test_us011_ticket_cancellation_releases_seats(self):
        self.add_customer(
            username="seat_user",
            password="pass123",
            name="Seat User",
            email="seat.user@example.com",
            phone="9000000108",
        )
        self.add_train("T504", "Nagpur", "Bhopal", "09:00", "12:00")
        travel_date = (datetime.today().date() + timedelta(days=3)).strftime("%Y-%m-%d")

        self.run_with_inputs(
            train_ticket_booking,
            ["T504", "Nagpur", "Bhopal", travel_date, "AC", "2", "yes"],
            "seat_user",
        )
        seats_after_booking = self.get_available_seats_for_class("T504", "AC")

        self.run_with_inputs(ticket_cancellation, ["1", "pass123", "yes"], "seat_user")
        seats_after_cancel = self.get_available_seats_for_class("T504", "AC")

        self.assertEqual(seats_after_booking, DEFAULT_CLASS_CAPACITY["AC"] - 2)
        self.assertEqual(seats_after_cancel, DEFAULT_CLASS_CAPACITY["AC"])

    def test_us012_booking_history_is_customer_specific(self):
        self.add_customer(
            username="history_user_1",
            password="pass123",
            name="History User One",
            email="history.one@example.com",
            phone="9000000005",
        )
        self.add_customer(
            username="history_user_2",
            password="pass123",
            name="History User Two",
            email="history.two@example.com",
            phone="9000000006",
        )
        self.add_train("T400", "Hyd", "Vij", "07:00", "11:00", "River Express")
        self.add_train("T401", "Hyd", "War", "06:00", "09:00", "Lake Express")

        db.initialize_database()
        with db.get_connection() as connection:
            ensure_booking_tables(connection)
            connection.execute(
                """
                INSERT INTO bookings (username,train_number,origin_station,destination_station,travel_date,preferred_class,ticket_count,total_fare,status,booked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("history_user_1", "T400", "Hyd", "Vij", "2030-01-10", "SLEEPER", 1, 200, "Booked", "2026-01-01 10:00:00"),
            )
            connection.execute(
                """
                INSERT INTO bookings (username,train_number,origin_station,destination_station,travel_date,preferred_class,ticket_count,total_fare,status,booked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("history_user_2", "T401", "Hyd", "War", "2030-01-10", "AC", 1, 500, "Booked", "2026-01-01 10:00:00"),
            )
            connection.commit()

        _, output = self.run_with_inputs(view_booking_history, [], "history_user_1")
        self.assertIn("T400", output)
        self.assertNotIn("T401", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
