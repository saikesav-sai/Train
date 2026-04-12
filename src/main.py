
from admin.auth_admin import run_admin_portal
from config import GOODBYE_MESSAGE, INVALID_OPTION_MESSAGE
from customer.auth_customer import run_customer_portal

if __name__ == "__main__":
    while True:
        print("\nPortal Menu")
        print("1) Admin Portal")
        print("2) Customer Portal")
        print("3) Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            run_admin_portal()
        elif choice == "2":
            run_customer_portal()
        elif choice == "3":
            print(GOODBYE_MESSAGE)
            break
        else:
            print(INVALID_OPTION_MESSAGE)
