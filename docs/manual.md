# Train Console Based Application - Developer Manual

## 1) Purpose
This project is a menu-driven Python console application for train operations and ticket booking.
It covers admin and customer workflows from login to booking history.

Primary goals:
- Admin train management (add, update, delete)
- Customer account management (register, update, soft delete)
- Train search, ticket booking, cancellation, and booking history


## 2) High-level Flow
The entry point is src/main.py.

Main portal menu:
- Admin Portal
- Customer Portal
- Exit

### Admin portal flow
Implemented in src/admin/auth_admin.py:
- Login with hard-coded credentials from src/config.py
- Menu options route to train operations in src/admin/train_management.py

### Customer portal flow
Implemented in src/customer/auth_customer.py:
- Login/registration access
- Menu options route to:
  - registration/update/delete in src/customer/profile.py
  - availability/booking/cancellation/history in src/customer/booking.py


## 3) Project Structure
- src/main.py: top-level app menu
- src/config.py: constants, fixed credentials, message strings
- src/data/db.py: SQLite connection and base table initialization
- src/admin/auth_admin.py: admin login and admin menu
- src/admin/train_management.py: train CRUD and schedule validations
- src/customer/auth_customer.py: customer login and customer menu
- src/customer/profile.py: customer register/update/soft delete
- src/customer/booking.py: train search, booking, cancellation, history
- tests/test_requirement_flows.py: automated requirement-focused test suite
- run_requirement_tests.py: one-command test runner
- setup_manual_test_data.py: deterministic DB seed for manual QA scenarios


## 4) Database Notes
Database file location:
- db/train_console.db

Core tables:
- trains
- train_stops
- customers

Booking-related tables are created on demand in customer booking flows:
- bookings
- train_class_seats

Seat classes:
- SLEEPER
- AC

Default capacities:
- SLEEPER: 100
- AC: 50


## 5) Key Business Rules in Code
- Admin login uses fixed credentials: admin / admin123
- Customer login checks customers table and only allows is_active = 1
- Train number must be unique
- Schedule conflict is blocked when origin + destination + departure + arrival overlap with another train
- Travel date for search/booking must be within next 3 months
- Booking session limit: max 6 tickets per user session
- Cancellation:
  - requires valid ticket ID and customer password
  - ownership is enforced (ticket must belong to logged-in user)
  - full refund only when cancellation is more than 24 hours before departure


## 6) How to Run the Application
From project root:
- python src/main.py


## 7) Automated Testing (for regression)
Run all tests:
- python run_requirement_tests.py

Direct unittest command:
- python -m unittest -v tests/test_requirement_flows.py

The automated tests are designed to verify requirement behavior and detect regressions.


## 8) Manual Test Data Seeder
File:
- setup_manual_test_data.py

Purpose:
- resets and seeds DB with deterministic data for quick manual checks
- inserts users, trains, seats, and bookings for common scenarios

Run with confirmation:
- python setup_manual_test_data.py

Run without prompt:
- python setup_manual_test_data.py --yes

Important:
- this script deletes existing train/customer/booking data in the app database before reseeding


## 9) Seeded Accounts and Scenarios
After running setup_manual_test_data.py, these are available:

Admin:
- admin / admin123

Customers:
- user / user123 (active)
- booking_owner / book123 (active)
- other_user / other123 (active)
- inactive_user / inactive123 (inactive; login should fail)

Sample cancellation scenarios seeded:
- Ticket ID 1: full-refund path (more than 24 hours before departure)
- Ticket ID 2: zero-refund path (near departure)
- Ticket ID 4: ownership validation path (belongs to other_user)


## 10) Recommended Team Workflow
1. Pull latest code.
2. Run seed script for consistent manual testing baseline.
3. Run automated tests before/after changes.
4. Implement feature updates in module-specific files (admin, customer, data).
5. Re-run tests and manual smoke checks.


## 11) Quick Troubleshooting
If login fails unexpectedly:
- verify DB has users (run setup_manual_test_data.py)
- verify inactive status is not blocking customer login

If booking fails with station errors:
- ensure the origin/destination exist in train_stops

If cancellation refund is unexpected:
- verify travel date/time and origin station stop time for the ticket

If tests fail intermittently:
- re-run tests after ensuring no stale DB lock/process is using db/train_console.db


## 12) For New Contributors
Start reading in this order:
1. src/main.py
2. src/config.py
3. src/data/db.py
4. src/admin/train_management.py
5. src/customer/profile.py
6. src/customer/booking.py
7. tests/test_requirement_flows.py

This order helps understand entry flow, constants, persistence, and feature logic.
