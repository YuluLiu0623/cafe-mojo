from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


# Initialize Flask app
app = Flask(__name__)

# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = "your_jwt_secret_key"  # Change this to your secret key
jwt = JWTManager(app)


# Assume the add_*, get_*, and authenticate_user functions are defined here or imported

@app.route('/user/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = app.config["db_query"].authenticate_user(username, password)
    if user:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Bad username or password"}), 401


@app.route('/user/signup', methods=['POST'])
def signup():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    if username is None or password is None:
        return jsonify({"msg": "Invalid data"}), 400
    user = app.config["db_query"].add_user(username, password)
    if user:
        return jsonify({"msg": "User created", "user_id": user.user_id}), 201
    else:
        return jsonify({"msg": "Username already exists"}), 400


@app.route('/user/memberships', methods=['GET'])
@jwt_required()
def get_user_groups():
    current_user_username = get_jwt_identity()
    user = app.config["db_query"].get_user_details_by_username(current_user_username)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Assuming a backref 'groups' in User model for groups the user is a member of
    groups = user.groups
    groups_data = [{"group_id": group.group_id, "name": group.name, "owner_id": group.owner_id} for group in groups]
    return jsonify(groups_data), 200


@app.route('/transaction/add', methods=['POST'])
@jwt_required()
def add_transaction_with_items():
    # Extract the current user's identity from the JWT token
    current_user_username = get_jwt_identity()

    # Find the user by username
    user = app.config["db_query"].get_user_details_by_username(current_user_username)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json()
    user_id = user.user_id
    group_id = data.get('group_id')
    store = data.get('store')
    points_redeemed = data.get('points_redeemed')
    items = data.get('items')  # Expected to be a list of dicts, each with 'item_id', 'quantity'

    transaction, transaction_items = app.config["db_query"].add_transaction(
        user_id, group_id, store, points_redeemed, items
    )

    if not transaction or not transaction_items:
        return jsonify({"msg": "Transaction failed!"}), 500
    else:
        return jsonify({
            "msg": "Transaction and items added successfully",
            "transaction": transaction,
            "transaction_items": transaction_items
        }), 201


@app.route('/item/add', methods=['POST'])
@jwt_required()
def add_item():
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    if not name or price is None:
        return jsonify({"msg": "Missing item name or price"}), 400

    item = app.config["db_query"].add_item(name, price)
    if item:
        return jsonify({"msg": "Item added successfully", "item_id": item.item_id}), 201
    else:
        return jsonify({"msg": "Failed to add item"}), 500


@app.route('/item/all', methods=['GET'])
@jwt_required()
def get_items():
    items = app.config["db_query"].get_items()
    items_data = [{"item_id": item.item_id, "name": item.name, "price": item.price} for item in items]
    return jsonify(items_data), 200


@app.route('/group/add', methods=['POST'])
@jwt_required()
def create_group():
    current_user = get_jwt_identity()
    group_name = request.json.get('name', None)
    # Find the user ID based on the JWT identity
    user = app.config["db_query"].get_user_details_by_username(current_user)
    print("JWT identity: ", current_user)
    print("User details:", user)

    if group_name is None or user is None:
        return jsonify({"msg": "Invalid data"}), 400
    group = app.config["db_query"].add_group(user.user_id, group_name)
    if group:
        return jsonify({"msg": "Group created", "group_id": group.group_id}), 201
    else:
        return jsonify({"msg": "Failed to create group"}), 400


@app.route('/group/add-member', methods=['POST'])
@jwt_required()
def add_group_member():
    data = request.get_json()
    group_id = data.get('group_id')
    user_name = data.get('user_name')

    user = app.config["db_query"].get_user_details_by_username(user_name)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    success = app.config["db_query"].add_member_to_group(user.user_id, group_id)
    if success:
        return jsonify({"msg": "Member added to group successfully"}), 201
    else:
        return jsonify({"msg": "Failed to add member to group"}), 500


@app.route('/group/<int:group_id>', methods=['GET'])
@jwt_required()
def get_group(group_id):
    group_details = app.config["db_query"].get_group_details(group_id)
    if not group_details:
        return jsonify({"msg": "Group not found"}), 404

    # Enhance group details with member information
    members_data = [{"user_id": member_id} for member_id in group_details['members']]
    group_details['members'] = members_data
    return jsonify(group_details), 200


@app.route('/group/add_points', methods=['POST'])
@jwt_required()
def add_group_points():
    current_user = get_jwt_identity()
    data = request.get_json()
    group_id = data.get('group_id')
    points_to_add = data.get('points_to_add')

    success = app.config["db_query"].add_group_points(group_id, points_to_add)
    if success:
        return jsonify({"msg": "Group points added successfully"}), 200
    else:
        return jsonify({"msg": "Failed to add points to group"}), 500


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return jsonify({"status": "ok"}), 200

