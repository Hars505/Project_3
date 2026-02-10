from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from LifeDeskBackend import LifeDeskManager, Speedtest, PasswordManager, set_current_user_id, get_current_user_id
from flask import Response, stream_with_context
import json

Lifedesk = Flask(__name__, template_folder='templates', static_folder='templates', static_url_path='/static')

CORS(Lifedesk)
backend_manager = LifeDeskManager()
password_manager = PasswordManager()

@Lifedesk.route("/")
def serve_login():
    return render_template("/Home/LoginRegister/index.html")

@Lifedesk.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400   
    # Use backend to register user
    result = backend_manager.register_user(email, password)
    
    if result["success"]:
        user_id = result.get("user_id")
        set_current_user_id(user_id)
        return jsonify({"message": result["message"], "user_id": user_id}), 201
    else:
        return jsonify({"message": result["message"]}), result["status_code"]

# LOGIN 
@Lifedesk.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400
    # Use backend manager to verify user
    user = backend_manager.verify_user(email, password)
    if user:
        user_id = user.get("user_id")
        set_current_user_id(user_id)
        return jsonify({
            "message": "Login successful",
            "email": user["email"],
            "user_id": user_id
        }), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401
    
def speedtest(lifedesk_app):
    @lifedesk_app.route("/speedtest")
    def serve_speedtest():
        return render_template("Speedtest/speedtest/speedtest.html")

    @lifedesk_app.route('/api/speedtest/stream')
    def stream_speedtest():
        def event_stream():
            st = Speedtest()
            for item in st.run_and_stream():
                try:
                    yield f"data: {json.dumps(item)}\n\n"
                except Exception:
                    yield f"data: {json.dumps({'status':'error','message':'serialization error'})}\n\n"

        return Response(stream_with_context(event_stream()), mimetype='text/event-stream')
    
    @lifedesk_app.route('/speedtest/servers')
    def serve_servers():
        return render_template("Speedtest/AllServers/servers.html")

    @lifedesk_app.route('/api/speedtest/servers')
    def api_speedtest_servers():
        st = Speedtest()
        servers = st.get_available_servers()
        if isinstance(servers, dict) and servers.get('error'):
            return jsonify(servers), 500
        return jsonify(servers)

    @lifedesk_app.route('/speedtest/best_servers')
    def serve_best_servers():
        return render_template("Speedtest/bestServer/best_server.html")

    @lifedesk_app.route('/api/speedtest/best_servers')
    def api_speedtest_best_servers():
        st = Speedtest()
        servers = st.get_available_servers()
        if isinstance(servers, dict) and servers.get('error'):
            return jsonify(servers), 500
        return jsonify(servers)
    @lifedesk_app.route("/Speedtest/History")
    def Speedtest_history():
            return render_template("Speedtest/History/speedhistory1.html")

    @lifedesk_app.route('/api/Speedtest/History')
    def api_speedtest_history():
            st = Speedtest()
            data = st.speedHistory()
            return jsonify(data)

def password_manager_routes(lifedesk_app):
    """Password Manager Routes"""
    
    @lifedesk_app.route("/passwordManager")
    def serve_password_manager():
        return render_template("passwordManager/passwordManager.html")
    
    @lifedesk_app.route("/api/passwords/add", methods=["POST"])
    def add_password():
        current_user = get_current_user_id()
        if current_user == "0":
            return jsonify({"error": "User not authenticated"}), 401
        
        data = request.get_json()
        site_name = data.get("site_name", "")
        site_url = data.get("site_url", "")
        login_username = data.get("login_username", "")
        plain_password = data.get("plain_password", "")
        notes = data.get("notes", "")
        
        if not all([site_name, login_username, plain_password]):
            return jsonify({"error": "Missing required fields"}), 400
        
        try:
            password_manager.add_password(
                user_id=int(current_user),
                site_name=site_name,
                site_url=site_url,
                login_username=login_username,
                plain_password=plain_password,
                notes=notes
            )
            return jsonify({"success": True, "message": "Password added successfully"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @lifedesk_app.route("/api/passwords/all", methods=["GET"])
    def get_all_passwords():
        current_user = get_current_user_id()
        if current_user == "0":
            return jsonify({"error": "User not authenticated"}), 401
        
        try:
            pm = PasswordManager(user_id=int(current_user))
            query = """
                SELECT password_id, user_id, site_name, site_url, login_username,
                       notes, created_at, updated_at
                FROM passwords
                WHERE user_id = %s
                ORDER BY created_at DESC
            """
            pm.cursor.execute(query, (current_user,))
            results = pm.cursor.fetchall()
            return jsonify(results), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @lifedesk_app.route("/api/passwords/update/<int:password_id>", methods=["PUT"])
    def update_password(password_id):
        current_user = get_current_user_id()
        if current_user == "0":
            return jsonify({"error": "User not authenticated"}), 401
        
        data = request.get_json()
        new_password = data.get("new_password", "")
        
        if not new_password:
            return jsonify({"error": "New password required"}), 400
        
        try:
            password_manager.update_password(password_id, new_password)
            return jsonify({"success": True, "message": "Password updated successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @lifedesk_app.route("/api/passwords/delete/<int:password_id>", methods=["DELETE"])
    def delete_password(password_id):
        current_user = get_current_user_id()
        if current_user == "0":
            return jsonify({"error": "User not authenticated"}), 401
        
        try:
            pm = PasswordManager(user_id=int(current_user))
            query = "DELETE FROM passwords WHERE password_id = %s AND user_id = %s"
            pm.cursor.execute(query, (password_id, current_user))
            pm.conn.commit()
            return jsonify({"success": True, "message": "Password deleted successfully"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
# Register the routes with the Lifedesk app
speedtest(Lifedesk)
password_manager_routes(Lifedesk)

if __name__ == "__main__":  
    Lifedesk.run(debug=True, host='localhost', port=5000)
  
