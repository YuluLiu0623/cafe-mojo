import requests

class APIClient:
    BASE_URL = "http://127.0.0.1:5000"
    access_token = None

    @classmethod
    def set_access_token(cls, token):
        cls.access_token = token

    @classmethod
    def signup(cls, username, password):
        response = requests.post(f"{APIClient.BASE_URL}/user/signup", json={"username": username, "password": password})
        return response

    @classmethod
    def login(cls, username, password):
        response = requests.post(f"{APIClient.BASE_URL}/user/login", json={"username": username, "password": password})
        if response.status_code == 200:
            cls.access_token = response.json().get('access_token')
        return response

    @classmethod
    def get_authenticated_header(cls):
        return {"Authorization": f"Bearer {cls.access_token}"} if cls.access_token else {}

    @classmethod
    def get_user_memberships(cls):
        """Get the community information of the currently logged-in user"""
        headers = cls.get_authenticated_header()
        response = requests.get(f"{cls.BASE_URL}/user/memberships", headers=headers)
        return response

    @classmethod
    def create_group(cls, group_name):
        """Create a new group"""
        headers = cls.get_authenticated_header()
        data = {"name": group_name}
        response = requests.post(f"{cls.BASE_URL}/group/add", headers=headers, json=data)
        return response

    @classmethod
    def add_member_to_group(cls, group_id, user_name):
        """Add user to group"""
        headers = cls.get_authenticated_header()
        data = {"group_id": group_id, "user_name": user_name}
        response = requests.post(f"{cls.BASE_URL}/group/add-member", headers=headers, json=data)
        return response

    @classmethod
    def get_group_details(cls, group_id):
        """Get the details of the specified group."""
        headers = cls.get_authenticated_header()
        response = requests.get(f"{cls.BASE_URL}/group/{group_id}", headers=headers)
        return response

    @classmethod
    def get_items(cls):
        """Get a list of all items"""
        headers = cls.get_authenticated_header()
        response = requests.get(f"{cls.BASE_URL}/item/all", headers=headers)
        return response

    @classmethod
    def add_item(cls, name, price):
        """Adds a new item to the inventory"""
        headers = cls.get_authenticated_header()
        data = {
            "name": name,
            "price": price
        }
        response = requests.post(f"{cls.BASE_URL}/item/add", headers=headers, json=data)
        return response

    @classmethod
    def create_transaction(cls, group_id, store, points_redeemed, items):
        headers = cls.get_authenticated_header()
        data = {
            "group_id": group_id,
            "store": store,
            "points_redeemed": points_redeemed,
            "items": items
        }
        response = requests.post(f"{cls.BASE_URL}/transaction/add", headers=headers, json=data)
        return response