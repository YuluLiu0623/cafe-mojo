"""
This script is designed to simulate concurrent updates to a group's score across different regions in a Dockerized distributed database environment. It targets two primary instances of a PostgreSQL database, one in Europe (euw_primary) and one in the USA (usw_primary), which simulate the regional primary databases in a multi-master database setup.

This test will:
- Register and log in two users, each in a different region.
- Create a group in one region and add the user from the other region to this group.
- Perform concurrent updates to the group's score from both regions.
- Retrieve the final score of the group from one region.

To clean up the test data, the script connects to both regional databases and deletes the test users and the group.

Usage:
python script_conflict_handling_test.py <API_URL_REGION_1> <API_URL_REGION_2>
Where API_URL_REGION_1 and API_URL_REGION_2 are the endpoints for the different regional instances.
"""


import sys
import requests
import threading
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import psycopg2

# Define a global variable for the group name to be used in the test
GROUP_NAME = "GlobalGroup"

# Database configuration for the EU region
DB_CONFIG_EU = {
    'dbname': 'cafe_mojo',
    'user': 'postgres',
    'password': 'password',
    'host': 'euw_primary',  # Should match the Docker service name
    'port': '5432',
}

# Database configuration for the US region
DB_CONFIG_US = {
    'dbname': 'cafe_mojo',
    'user': 'postgres',
    'password': 'password',
    'host': 'usw_primary',  # Should match the Docker service name
    'port': '5432',
}


def get_db_connection(db_config):
    """Establishes a database connection using the provided configuration."""
    try:
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except psycopg2.DatabaseError as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)


def clean_up_database(db_config, group_name):
    """Cleans up test data from the database for the specified region."""
    conn = get_db_connection(db_config)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM "group" WHERE name = %s', (group_name,))
            cursor.execute('DELETE FROM "user" WHERE user_name LIKE %s', ('test_conflict_user%',))
            conn.commit()
    print("Test data has been cleaned up.")


def main():
    if len(sys.argv) < 3:
        print("Usage: python script_conflict_handling_test.py <API_URL_REGION_1> <API_URL_REGION_2>")
        sys.exit(1)

    # Obtain the API URLs from the command-line arguments
    API_BASE_URL_REGION1 = sys.argv[1]
    API_BASE_URL_REGION2 = sys.argv[2]

    def register_and_login_user(api_url, username, password):
        reg_response = requests.post(f"{api_url}/user/signup", json={"username": username, "password": password})
        if reg_response.status_code == 201:
            print(f"User {username} registered successfully.")
        elif reg_response.status_code == 400:
            print(f"User {username} registration failed: {reg_response.json()}")

        login_response = requests.post(f"{api_url}/user/login", json={"username": username, "password": password})
        if login_response.status_code == 200:
            print(f"User {username} logged in successfully.")
            return login_response.json()['access_token']
        else:
            print(f"User {username} login failed: {login_response.json()}")
            return None

    def create_group(jwt, api_url, group_name):
        headers = {'Authorization': f'Bearer {jwt}'}
        response = requests.post(f"{api_url}/group/add", headers=headers, json={"name": group_name})
        if response.status_code == 201:
            print(f"Group {group_name} created successfully.")
            return response.json()['group_id']
        else:
            print(f"Group {group_name} creation failed: {response.json()}")
            return None

    def add_member_to_group(jwt, api_url, group_id, user_name):
        headers = {'Authorization': f'Bearer {jwt}'}
        response = requests.post(f"{api_url}/group/add-member", headers=headers,
                                 json={"group_id": group_id, "user_name": user_name})
        if response.status_code == 201:
            print(f"User {user_name} added to group {group_id} successfully.")
        else:
            print(f"Failed to add user {user_name} to group {group_id}: {response.json()}")

    def update_group_points(jwt, group_id, points_to_add, api_url):
        headers = {'Authorization': f'Bearer {jwt}'}
        response = requests.post(f"{api_url}/group/add_points", headers=headers,
                                 json={"group_id": group_id, "points_to_add": points_to_add})
        print(f"Attempt to update points for group {group_id} by user with token {jwt[-10:]}: {response.json()}")

    def get_group_points(jwt, group_id, api_url):
        headers = {'Authorization': f'Bearer {jwt}'}
        response = requests.get(f"{api_url}/group/{group_id}", headers=headers)
        if response.status_code == 200:
            print(f"Final points for group {group_id}: {response.json()['points']}")
        else:
            print(f"Failed to retrieve points for group {group_id}: {response.json()}")

    def simulate_concurrent_updates(group_id, jwt1, jwt2, api_url1, api_url2):
        points_to_add = 10
        thread1 = threading.Thread(target=update_group_points, args=(jwt1, group_id, points_to_add, api_url1))
        thread2 = threading.Thread(target=update_group_points, args=(jwt2, group_id, points_to_add, api_url2))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        get_group_points(jwt1, group_id, api_url1)

    user1_token = register_and_login_user(API_BASE_URL_REGION1, "test_conflict_user1", "password1")
    user2_token = register_and_login_user(API_BASE_URL_REGION2, "test_conflict_user2", "password2")

    if user1_token and user2_token:
        group_id = create_group(user1_token, API_BASE_URL_REGION1, "TestConflict")
        if group_id:
            add_member_to_group(user1_token, API_BASE_URL_REGION1, group_id, "test_conflict_user2")
            simulate_concurrent_updates(group_id, user1_token, user2_token, API_BASE_URL_REGION1, API_BASE_URL_REGION2)

    clean_up_database(DB_CONFIG_EU, GROUP_NAME)
    clean_up_database(DB_CONFIG_US, GROUP_NAME)

if __name__ == "__main__":
    main()
