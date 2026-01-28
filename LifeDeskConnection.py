from flask import Flask, request, jsonify,render_template
from LifeDeskBackend import LifeDeskManager

Lifedesk = Flask(__name__, static_folder='html', static_url_path='/static')

# Initialize backend manager for all database operations
backend_manager = LifeDeskManager()

@Lifedesk.route("/")
def serve_login():
    return render_template("LoginRegister/login.html")

@Lifedesk.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not name or not email or not password:
        return jsonify({"message": "Missing data"}), 400
    
    # Use backend to register user
    result = backend_manager.register_user(name, email, password)
    
    if result["success"]:
        return jsonify({"message": result["message"]}), 201
    else:
        return jsonify({"message": result["message"]}), result["status_code"]

# ------------------ LOGIN ------------------
@Lifedesk.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("Email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400
    
    # Use backend manager to verify user
    user = backend_manager.verify_user(email, password)
    
    if user:
        return jsonify({
            "message": "Login successful",
            "name": user["name"],
            "email": user["email"]
        }), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401

if __name__ == "__main__":
    Lifedesk.run(debug=True, host='localhost', port=5000)
    
