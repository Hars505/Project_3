from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from LifeDeskBackend import LifeDeskManager, Speedtest
from flask import Response, stream_with_context
import json

Lifedesk = Flask(__name__, template_folder='templates', static_folder='templates', static_url_path='/static')

# Enable CORS for frontend communication
CORS(Lifedesk)

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
    email = data.get("email")  # Changed from "Email" to "email"
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400
    
    # Use backend manager to verify user
    user = backend_manager.verify_user(email, password)
    if user:
        return jsonify({
            "message": "Login successful",
            "email": user["email"],
            "user_id": user["user_id"]
        }), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401


def speedtest(lifedesk_app):
    """Register speedtest-related routes on the provided Flask app."""
    @lifedesk_app.route("/speedtest")
    def serve_speedtest():
        return render_template("Speedtest/speedtest/speedtest.html")


    @lifedesk_app.route('/api/speedtest/stream')
    def stream_speedtest():
        """Server-Sent Events endpoint that streams speedtest progress/results."""
        def event_stream():
            st = Speedtest()
            for item in st.run_and_stream():
                try:
                    yield f"data: {json.dumps(item)}\n\n"
                except Exception:
                    # If serialization fails, send a simple error event
                    yield f"data: {json.dumps({'status':'error','message':'serialization error'})}\n\n"

        return Response(stream_with_context(event_stream()), mimetype='text/event-stream')


    @lifedesk_app.route('/speedtest/servers')
    def serve_servers():
        """Render the servers listing page."""
        return render_template("Speedtest/AllServers/servers.html")

    @lifedesk_app.route('/api/speedtest/servers')
    def api_speedtest_servers():
        """Return available speedtest servers as JSON (all servers)."""
        st = Speedtest()
        servers = st.get_available_servers()
        if isinstance(servers, dict) and servers.get('error'):
            return jsonify(servers), 500
        return jsonify(servers)

    @lifedesk_app.route('/speedtest/best_servers')
    def serve_best_servers():
        """Render the best-server page (shows the recommended server)."""
        return render_template("Speedtest/bestServer/best_server.html")

    @lifedesk_app.route('/api/speedtest/best_servers')
    def api_speedtest_best_servers():
        """Return best server(s) as JSON. Uses get_available_servers to allow frontend to choose best."""
        st = Speedtest()
        servers = st.get_available_servers()
        if isinstance(servers, dict) and servers.get('error'):
            return jsonify(servers), 500
        return jsonify(servers)


# Register the speedtest route with the Lifedesk app
speedtest(Lifedesk)
if __name__ == "__main__":
    Lifedesk.run(debug=True, host='localhost', port=5000)
    
