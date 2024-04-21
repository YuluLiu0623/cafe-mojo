"""
This script is designed to test the user registration endpoint's ability to handle multiple concurrent requests.
It can be configured to target any API URL, making it suitable for testing in different regional deployments.

To run this script:
1. Ensure that the API server is running and accessible at the target URL.
2. Navigate to the directory containing this script. This script should be located under the 'test' folder in the 'cafe-moji' project directory.
3. Run the script using Python 3 by providing the target API URL as an argument. For example:
   python script_user_service_test.py http://api-region1.example.com

Arguments:
- API_URL: The base URL of the API where the user/signup endpoint is available.

Location:
- This script is located in the 'cafe-moji/test' folder.

Requirements:
- Python 3.x
- 'requests' library installed in your Python environment (install via pip if necessary)

Purpose:
- To test and ensure that the user registration process can scale under load and perform efficiently across different regions.
"""


import sys

import psycopg2
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database configuration
DB_CONFIG = {
    'dbname': 'cafe_mojo',
    'user': 'user',
    'password': 'password',
    'host': 'localhost',
    'port': '5432',
}


def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)


def clean_up_database(usernames):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = "DELETE FROM users WHERE username = ANY(%s);"
            cursor.execute(query, (usernames,))
            conn.commit()
    print("Cleaned up test users from database.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python script_user_service_test.py <API_URL>")
        sys.exit(1)

    API_URL = sys.argv[1]
    USERS_TO_REGISTER = 50
    SIGNUP_ENDPOINT = f"{API_URL}/user/signup"

    def register_user():
        username = f"user_{uuid4()}"
        password = "password"
        response = requests.post(SIGNUP_ENDPOINT, json={"username": username, "password": password})
        return response.ok, username

    with ThreadPoolExecutor(max_workers=USERS_TO_REGISTER) as executor:
        futures = [executor.submit(register_user) for _ in range(USERS_TO_REGISTER)]
        results = [future.result() for future in as_completed(futures)]

    success_count = sum(1 for success, _ in results if success)
    failed_count = USERS_TO_REGISTER - success_count
    registered_usernames = [username for success, username in results if success]

    print(f"Attempted to register users: {USERS_TO_REGISTER}")
    print(f"Successfully registered users: {success_count}")
    print(f"Failed registration attempts: {failed_count}")

    clean_up_database(registered_usernames)

if __name__ == "__main__":
    main()

