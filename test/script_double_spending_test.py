"""
This script is designed to simulate a set of operations involving user registration, group management, and transaction processing to test the functionality and robustness of an API handling concurrent requests.

Instructions for running this script:
1. Make sure the API server (e.g., Flask application) that you intend to test is up and running at the specified BASE_URL.
2. The script should be located under a specific directory structured for testing within your project. It's recommended to place this script in a directory such as 'project_directory/scripts' for organization.
3. To execute the script, navigate to the directory where the script is located and run it from the command line:
   python script_double_spending_test.py <API_URL>


Script Workflow:
- Registers two test users.
- Logs in both users to retrieve JWT tokens.
- Creates a group and adds both users to it.
- Simulates adding initial points to the group.
- Conducts concurrent transactions using threading to simulate real-world usage and test the system's handling of concurrency.
- Checks and prints the final state of the group's points to verify the outcomes of the transactions.

Location and Structure:
- Ensure this script is located in a dedicated test directory within your project structure, such as 'project_directory/tests'.
- This structure helps maintain clarity and organization, especially in larger projects where multiple types of tests might be needed.

Purpose:
- This script is used primarily for testing and verifying the correct functionality of user registration, group creation, transaction handling, and concurrency management within the API. It aims to ensure that the system performs as expected under simulated real-world conditions.
"""
import sys
import threading
import psycopg2
import requests
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_db_connection(db_config):
    conn = psycopg2.connect(**db_config)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def clean_up_database(test_usernames, db_config):
    with get_db_connection(db_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'DELETE FROM "transaction_item" WHERE transaction_id IN (SELECT transaction_id FROM "transaction" WHERE user_id IN (SELECT user_id FROM "user" WHERE user_name = ANY(%s)));',
                (test_usernames,))
            cursor.execute('DELETE FROM "transaction" WHERE user_id IN (SELECT user_id FROM "user" WHERE user_name = ANY(%s));',
                           (test_usernames,))
            cursor.execute('DELETE FROM "group_member" WHERE user_id IN (SELECT user_id FROM "user" WHERE user_name = ANY(%s));',
                           (test_usernames,))
            cursor.execute('DELETE FROM "group" WHERE name = %s;', ('TestGroup',))
            cursor.execute('DELETE FROM "user" WHERE user_name = ANY(%s);', (test_usernames,))
        print("Cleaned up the database.")


def register_user(username, password, api_base_url):
    url = f"{api_base_url}/user/signup"
    data = {"username": username, "password": password}
    response = requests.post(url, json=data)
    return response.json(), response.status_code


def login_user(username, password, api_base_url):
    url = f"{api_base_url}/user/login"
    data = {"username": username, "password": password}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        return None


def create_group(jwt, group_name, api_base_url):
    url = f"{api_base_url}/group/add"
    headers = {'Authorization': f'Bearer {jwt}'}
    data = {"name": group_name}
    response = requests.post(url, headers=headers, json=data)
    return response.json(), response.status_code


def add_group_member(jwt, group_id, user_name, api_base_url):
    url = f"{api_base_url}/group/add-member"
    headers = {'Authorization': f'Bearer {jwt}'}
    data = {"group_id": group_id, "user_name": user_name}
    response = requests.post(url, headers=headers, json=data)
    return response.json(), response.status_code


def make_transaction(jwt, group_id, store, item, api_base_url):
    url = f"{api_base_url}/transaction/add"
    headers = {'Authorization': f'Bearer {jwt}'}
    data = {
        "group_id": group_id,
        "store": store,
        "points_redeemed": 2,
        "items": item
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json(), response.status_code


def add_initial_points(jwt, group_id, initial_points, api_base_url):
    url = f"{api_base_url}/group/add_points"
    headers = {'Authorization': f'Bearer {jwt}'}
    data = {"group_id": group_id, "points_to_add": initial_points}
    response = requests.post(url, headers=headers, json=data)
    return response.json(), response.status_code


def simulate_transaction(jwt1, jwt2, group_id, api_base_url):
    items_user1 = [{"item_id": 1, "quantity": 2}, {"item_id": 2, "quantity": 1}]
    items_user2 = [{"item_id": 3, "quantity": 1}, {"item_id": 4, "quantity": 3}]

    thread1 = threading.Thread(target=make_transaction, args=(jwt1, group_id, "Dublin 6", items_user1, api_base_url))
    thread2 = threading.Thread(target=make_transaction, args=(jwt2, group_id, "Dublin 6", items_user2, api_base_url))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()


def check_group_points(jwt, group_id, api_base_url):
    url = f"{api_base_url}/group/{group_id}"
    headers = {'Authorization': f'Bearer {jwt}'}
    response = requests.get(url, headers=headers)
    return response.json(), response.status_code


def main(api_base_url):
    DB_CONFIG = {
        'dbname': 'cafe_mojo',
        'user': 'postgres',
        'password': 'password',
        'host': 'localhost',
        'port': '5432',
    }
    user1 = {"username": "testuser1", "password": "password1"}
    user2 = {"username": "testuser2", "password": "password2"}
    group_name = "TestGroup"

    print("Registering users...")
    register_user(user1['username'], user1['password'], api_base_url)
    register_user(user2['username'], user2['password'], api_base_url)

    print("Logging in users...")
    jwt1 = login_user(user1['username'], user1['password'], api_base_url)
    jwt2 = login_user(user2['username'], user2['password'], api_base_url)

    print("Creating group...")
    group_info, status = create_group(jwt1, group_name, api_base_url)
    if status != 201:
        print("Failed to create group.")
        return
    group_id = group_info['group_id']

    print("Adding second user to group...")
    add_group_member(jwt1, group_id, user2['username'], api_base_url)

    print("Adding initial points to group...")
    add_initial_points(jwt1, group_id, 10, api_base_url)

    print("Simulating transactions...")
    simulate_transaction(jwt1, jwt2, group_id, api_base_url)

    print("Checking final group points...")
    result, status = check_group_points(jwt1, group_id, api_base_url)
    print(f"Group Points Status: {status}, Data: {result}")

    test_usernames = [user1['username'], user2['username']]
    clean_up_database(test_usernames, DB_CONFIG)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python script_double_spending_test.py <API_URL>")
        sys.exit(1)

    main(sys.argv[1])
