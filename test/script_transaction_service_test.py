"""
This script is designed to perform a load test on the transaction API by simulating a high number of concurrent transactions over a set period. It is intended to assess the system's handling of intense, concurrent transaction processing in a controlled test environment.

How to run this script:
1. Ensure the API server that you are testing is running and accessible. The BASE_URL in the script should be set to the API's base URL.
2. Place this script in the appropriate directory. It is recommended to store it under 'cafe-moji/test' to maintain project organization.
3. Execute the script from your command line by navigating to the directory where the script is stored and running:
   python script_transaction_service_test.py <API_URL>


Requirements:
- This script requires Python 3.x.
- The 'requests' library must be installed in your Python environment. Install it via pip if it is not already installed by running:
  pip install requests

Features:
- Registers a test user and logs in to obtain a JWT token.
- Creates a new group for transactions or retrieves an existing one if it already exists.
- Simultaneously sends transaction requests to the server using multiple threads to simulate high load conditions.
- Measures and prints out the success rate and the total number of transactions processed during the test period.

Location and Structure:
- The script is located within the 'cafe-moji/test' folder as part of the project structure designed to organize test scripts and related utilities.

Purpose:
- The primary purpose of this script is to evaluate how well the transaction processing system performs under significant load and to identify any potential bottlenecks or failures in the system's ability to process transactions concurrently.
"""
import sys
import psycopg2
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
# Test parameters
CONCURRENT_REQUESTS = 100  # Number of concurrent requests
TEST_DURATION = 60  # Duration of the test in seconds, modify as needed

# Default test user credentials
USERNAME = "test_transaction"  # Username for test user
PASSWORD = "testpassword"  # Password for test user

DB_CONFIG = {
    'dbname': 'cafe_mojo',
    'user': 'user',
    'password': 'password',
    'host': 'localhost',  # 当运行在Docker容器外部时，使用Docker容器的IP或localhost如果端口已映射
    'port': '5432',
}


def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn
def clean_up_database():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM transaction WHERE user_id = (SELECT user_id FROM user WHERE user_name = %s);", (USERNAME,))
            cursor.execute("DELETE FROM user WHERE user_name = %s;", (USERNAME,))
            conn.commit()
        print("Test data cleaned up.")


def setup_test_user(api_base_url):
    """
    Registers and logs in a user. Returns a JWT token for authenticated API calls.
    If the user already exists, it continues to login.
    """
    # Register a user
    response = requests.post(f"{api_base_url}/user/signup", json={"username": USERNAME, "password": PASSWORD})
    if response.status_code == 201:
        print("User successfully registered.")
    elif response.status_code == 400:
        print("User already exists. Proceeding with login.")

    # Log in user
    response = requests.post(f"{api_base_url}/user/login", json={"username": USERNAME, "password": PASSWORD})
    if response.status_code != 200:
        raise Exception("Login failed, cannot perform tests.")

    access_token = response.json()["access_token"]
    print("Login successful, access token received.")
    return access_token


def create_group(access_token, api_base_url):
    """
    Creates a group for the test transactions. Returns the group ID.
    If a group already exists, tries to retrieve an existing group ID.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(f"{api_base_url}/group/add", headers=headers, json={"name": "Test Transaction"})
    if response.status_code == 201:
        print("Group created successfully.")
        return response.json()["group_id"]
    elif response.status_code == 400:
        print("Group already exists. Retrieving existing group...")
        return get_group_id(access_token, api_base_url)


def get_group_id(access_token, api_base_url):
    """
    Retrieves the first group ID associated with the user. This assumes the user is part of at least one group.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{api_base_url}/user/memberships", headers=headers)
    if response.status_code == 200 and response.json():
        return response.json()[0]["group_id"]
    raise Exception("No groups found for user.")


def simulate_transaction(access_token, api_base_url, group_id):
    """
    Simulates a transaction by sending a POST request to the transaction endpoint.
    Returns True if the request was successful, False otherwise.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "group_id": group_id,
        "store": "Dublin 6",
        "points_redeemed": 0,
        "items": [{"item_id": 1, "quantity": 1}]  # Sample item, assumes item ID 1 exists
    }
    response = requests.post(f"{api_base_url}/transaction/add", headers=headers, json=data)
    return response.ok


def main(api_base_url):
    """
    Main function to execute the load test. Registers a user, creates a group, and then simulates
    high-concurrency transactions to test API responsiveness and stability under load.
    """
    access_token = setup_test_user(api_base_url)
    group_id = create_group(access_token, api_base_url)
    if not group_id:
        print("Failed to retrieve or create a group. Exiting...")
        return

    print(f"Using Group ID: {group_id}")

    # Execute concurrent transactions for a specified duration
    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        end_time = time.time() + TEST_DURATION
        futures = []
        while time.time() < end_time:
            futures.append(executor.submit(simulate_transaction, access_token, api_base_url, group_id))

        success_count = sum(future.result() for future in as_completed(futures))
        print(f"Total requests: {len(futures)}")
        print(f"Successful requests: {success_count}")
        print(f"Success rate: {success_count / len(futures) * 100:.2f}%")

        clean_up_database()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_transaction_service_test.py <API_URL>")
        sys.exit(1)
    main(sys.argv[1])
