import mysql.connector as mslc
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify
app = Flask(__name__)
db = mslc.connect(
    host="localhost",
    user="root",
    password="password",
    database="lifedesk"
)
cursor = db.cursor(dictionary=True)
@app.route("/register", methods=["POST"])
def register(self):
    self.data = request.get_json()
    self.username = self.data.get("username")
    self.password = self.data.get("password")
    if not self.username or not self.password:
        return jsonify({"message": "Missing data"}), 400
    cursor.execute("SELECT id FROM users WHERE username = %s", (self.username))
    if cursor.fetchone():
        return jsonify({"message": "User already exists"}), 409
    hashed_password = generate_password_hash(self.password)
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (self.username, hashed_password)
    )
    db.commit()
    return jsonify({"message": "Registration successful"}), 201
# ------------------ LOGIN ------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    cursor.execute("SELECT * FROM users WHERE username = %s", (username))
    user = cursor.fetchone()
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid username or password"}), 401
    return jsonify({
        "message": "Login successful",
        "username": user["username"],
        "role": user["role"]
    }), 200
if __name__ == "__main__":
    app.run(debug=True)
