from abc import abstractmethod,ABC
import os
import datetime as dt
import time
import mysql.connector as mslc
import speedtest
import hashlib as hl
import bcrypt as bt
from werkzeug.security import check_password_hash,generate_password_hash
import json

class LifeDesk(ABC):
    def __init__(self):
        try:
            self.conn = mslc.connect(host="localhost", user="root", database="life_desk")
            self.cursor = self.conn.cursor(dictionary=True)
            if self.conn.is_connected():
                print("Connection Successful")
            else:
                print("Connection Unsuccessful")
                print("System Exiting.....")
                SystemExit
            db_name="life_desk"
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        except (ConnectionError,TimeoutError,ConnectionRefusedError,ModuleNotFoundError) as E:
            print("Error : ",E)
    
    def menu(self):
        """Placeholder for menu method."""
        pass
    
    def test(self, password, email):
        try:
            # Ensure parameter is passed as a single-element tuple
            self.cursor.execute("SELECT encrypted_password FROM users WHERE email = %s", (email,))
            row = self.cursor.fetchone()
            if not row:
                return False
            stored_hash = row.get("encrypted_password")
            return check_password_hash(stored_hash, password)
        except (mslc.Error,Exception) as E:
            print("Error : ",E)
class LifeDeskManager(LifeDesk):
    def __init__(self):
        try:
            self.conn = mslc.connect(host="localhost", user="root", database="life_desk")
            self.cursor = self.conn.cursor(dictionary=True)
            if self.conn.is_connected():
                print("Connection Successful")
                self._create_users_table()
            else:
                print("Connection Unsuccessful")
                SystemExit
        except (ConnectionError, TimeoutError, ConnectionRefusedError, ModuleNotFoundError) as E:
            print("Error : ", E) 
    def _create_users_table(self):
        """Create user table if it doesn't exist."""
        try:
            # Check if user table exists
            check=self.cursor.execute("")
            self.cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'life_desk' AND TABLE_NAME = 'user'
            """)
            if self.cursor.fetchone():
                print("Users table already exists")
                return
            # Create user table if it doesn't exist
            create_table_query = """CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                encrypted_password VARCHAR(255) NOT NULL,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
            """
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("User table created successfully")
        except mslc.Error as E:
            print(f"Error with user table: {E}")
            pass
    def verify_user(self, email, password):
        if self.test(password, email) is True:
            try:
                # Update last_login timestamp
                self.cursor.execute(
                    "UPDATE users SET last_login = NOW() WHERE email = %s",
                    (email,)
                )
                self.conn.commit()
                # Fetch and return user data
                self.cursor.execute("SELECT user_id, email FROM users WHERE email = %s", (email,))
                user = self.cursor.fetchone()
                return user
            except mslc.Error as E:
                print("Error fetching user data:", E)
                return None
        return None
    def register_user(self, name, email, password):
        try:
            # Check if user already exists
            self.cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if self.cursor.fetchone():
                return {
                    "success": False,
                    "message": "User already exists",
                    "status_code": 409
                }
            hashed_password = generate_password_hash(password)
            self.cursor.execute(
                "INSERT INTO users (email, encrypted_password) VALUES (%s, %s)",
                (email, hashed_password)
            )
            self.conn.commit()
            return {
                "success": True,
                "message": "Registration successful",
                "status_code": 201
            }
        except mslc.Error as E:
            print(f"Database error during registration: {E}")
            return {
                "success": False,
                "message": f"Database error: {str(E)}",
                "status_code": 500
            }
        except Exception as E:
            print(f"Error during registration: {E}")
            return {
                "success": False,
                "message": f"Registration failed: {str(E)}",
                "status_code": 500
            }
class Speedtest(LifeDesk):
    def __init__(self):
        try:
            self.ST = speedtest.Speedtest()
            print(self.ST)
        except Exception as E:
            print(f"Warning: Speedtest initialization failed: {E}")
            self.ST=None
    def run_and_stream(self):
        import threading
        import queue

        if not self.ST:
            yield {"status": "error", "message": "Speedtest not initialized"}
            return

        try:
            yield {"status": "starting"}
            yield {"status": "selecting_best_server"}

            # ---------- DOWNLOAD ----------

            yield {"status": "running_download"}
            download_queue = queue.Queue()

            def download_worker():
                try:
                    download_speed = self.ST.download(
                        callback=lambda *args, **kwargs: download_queue.put(args)
                    )
                    download_queue.put(("done", download_speed))
                except Exception as e:
                    download_queue.put(("error", str(e)))

            threading.Thread(target=download_worker).start()

            while True:
                item = download_queue.get()

                if item[0] == "done":
                    download_speed = item[1]
                    download_mbps = round(download_speed / 1024 / 1024, 2)
                    yield {"status": "download_done", "value": download_mbps}
                    break

                elif item[0] == "error":
                    yield {"status": "error", "message": f"Download failed: {item[1]}"}
                    return

                else:
                    d = item[0]
                    mbps = round(d / 1024 / 1024, 2)
                    yield {"status": "downloading", "value": mbps}


            # ---------- UPLOAD ----------

            yield {"status": "running_upload"}
            upload_queue = queue.Queue()

            def upload_worker():
                try:
                    upload_speed = self.ST.upload(
                        callback=lambda *args, **kwargs: upload_queue.put(args))
                    upload_queue.put(("done", upload_speed))
                except Exception as e:
                    upload_queue.put(("error", str(e)))

            threading.Thread(target=upload_worker).start()

            while True:
                item = upload_queue.get()

                if item[0] == "done":
                    upload_speed = item[1]
                    upload_mbps = round(upload_speed / 1024 / 1024, 2)
                    yield {"status": "upload_done", "value": upload_mbps}
                    break

                elif item[0] == "error":
                    yield {"status": "error", "message": f"Upload failed: {item[1]}"}
                    return

                else:
                    d = item[0]
                    mbps = round(d / 1024 / 1024, 2)
                    yield {"status": "uploading", "value": mbps}


            # ---------- LATENCY ----------

            ping = getattr(self.ST.results, "ping", None)
            ping_val = round(ping, 2) if ping else None

            if ping_val is not None:
                yield {"status": "ping", "value": ping_val}


            # ---------- FINAL ----------

            yield {
                "status": "done",
                "download": download_mbps,
                "upload": upload_mbps,
                "ping": ping_val
            }
            try:
                self.conn = mslc.connect(host="localhost", user="root", database="life_desk")
                self.cursor = self.conn.cursor(dictionary=True)
                if self.conn.is_connected():
                    print("Connection Successful")
                    server_json = json.dumps({"Host" : self.ST.results.server.get('host'), "Sponsor" : self.ST.results.server.get('sponsor'),"Country" : self.ST.results.server.get('country'),"Server Id" : self.ST.results.server.get('d')})
                    query = """
                    INSERT INTO speedtesthistory
                    (server, download_speed, upload_speed, latency)
                    VALUES (%s, %s, %s, %s)
                    """
                    values = (server_json,download_speed/1024/1024,upload_speed/1024/1024,ping_val)
                    self.cursor.execute(query, values)
                    self.conn.commit()
                    print("Everything stored")
                else:
                    print("Connection Unsuccessful")
            except (Exception) as E:
                print("Error : ",E)
        except mslc.Error as E:
            print("Database Error:", E)
        except Exception as e:
            yield {"status": "error", "message": f"Critical error: {e}"}
    def get_available_servers(self):
        server_list = []
        try:
            if not self.ST:
                return {"error": "Speedtest not initialized"}
            servers = self.ST.get_servers()
            for dist_list in servers.values():
                for server in dist_list:
                    server_list.append({
                        "id": server.get("id"),
                        "location": f"{server.get('name')}",
                        "country" : f"{server.get('country')}",
                        "sponsor": server.get("sponsor"),
                        "url": server.get("url")
                    })
            return server_list
        except (ValueError, BufferError, OSError) as E:
            return {"error": f"Failed to retrieve servers: {E}"}
    def get_best_servers(self):
        server_list = []
        try:
            if not self.ST:
                return {"error": "Speedtest not initialized"}
            best = self.ST.get_best_server()
            best_list = []
            if isinstance(best, dict):
                best_list = [best]
            elif isinstance(best, (list, tuple)):
                best_list = list(best)
            else:
                try:
                    for s in best:
                        best_list.append(s)
                except Exception as E:
                    print("Error : ",E)
            best_list = []
            for server in best_list:
                server_list.append({
                    "id": server.get("id"),
                    "location": f"{server.get('name')}, {server.get('country')}",
                    "sponsor": server.get("sponsor"),
                    "url": server.get("url")
                })
            return server_list
        except (ValueError, BufferError, OSError) as E:
            return {"error": f"Failed to retrieve servers: {E}"}
    def set_mini_server(self, url):
        try:
            if not self.ST:
                print("Speedtest not initialized")
                return
            self.ST.set_mini_server(url)
            print(f"Mini server set to {url}")
        except (TypeError, ConnectionRefusedError, SystemError) as E:
            print(f"Error setting mini server: {E}")
