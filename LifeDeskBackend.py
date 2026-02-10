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

# Module-level global user id. Use string "0" when no user is set.
CURRENT_USER_ID = "0"

def set_current_user_id(uid):
    global CURRENT_USER_ID
    try:
        # store as string for consistent "0" behavior
        CURRENT_USER_ID = str(uid) if uid is not None else "0"
    except Exception:
        CURRENT_USER_ID = "0"

def get_current_user_id():
    return CURRENT_USER_ID

class LifeDesk(ABC):
    def __init__(self, user_id=None):
        try:
            # Set instance user id from passed value or global
            self.user_id = str(user_id) if user_id is not None else get_current_user_id() or "0"
            if not self.user_id:
                self.user_id = "0"

            self.conn = mslc.connect(host="localhost", user="root", database="life_desk",connection_timeout=5)
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
    def test(self, password, email):
        try:
            # Ensure parameter is passed as a single-element tuple
            self.cursor.execute("SELECT encrypted_password FROM users WHERE email = %s ", (email,))
            row = self.cursor.fetchone()
            if not row:
                return False
            stored_hash = row.get("encrypted_password")
            return check_password_hash(stored_hash, password)
        except (mslc.Error,Exception) as E:
            print("Error : ",E)
class LifeDeskManager(LifeDesk):
    def __init__(self, user_id=None):
        super().__init__(user_id=user_id)
        try:
            self.user_id = str(user_id) if user_id is not None else get_current_user_id() or "0"
            self.conn = mslc.connect(host="localhost", user="root", database="life_desk")
            self.cursor = self.conn.cursor(dictionary=True)
            if self.conn.is_connected():
                print("Connection Successful")
                self.Create_users_table()
            else:
                print("Connection Unsuccessful")
                SystemExit
        except (ConnectionError, TimeoutError, ConnectionRefusedError, ModuleNotFoundError) as E:
            print("Error : ", E)
    def Create_users_table(self):
        try:
            self.cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'life_desk' AND TABLE_NAME = 'users'
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
                # set global current user id
                if user and user.get('user_id'):
                    set_current_user_id(user.get('user_id'))
                    self.user_id = str(user.get('user_id'))
                return user
            except mslc.Error as E:
                print("Error fetching user data:", E)
                return None
        return None
    def register_user(self, email, password):
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
            # capture and set the new user id globally
            new_id = getattr(self.cursor, 'lastrowid', None)
            if new_id:
                set_current_user_id(new_id)
                self.user_id = str(new_id)
            return {
                "success": True,
                "message": "Registration successful",
                "status_code": 201,
                "user_id": new_id or None
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
    def __init__(self, user_id=None):
        try:
            # set instance user id
            self.user_id = str(user_id) if user_id is not None else get_current_user_id() or "0"
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
                    server_json = json.dumps({"Host" : self.ST.results.server.get('host'), "Sponsor" : self.ST.results.server.get('sponsor'),"Country" : self.ST.results.server.get('country'),"Server_Id" : self.ST.results.server.get('d')})
                    # try to store user-specific history; if user_id is "0" still store but mark as 0
                    uid = self.user_id if hasattr(self, 'user_id') else get_current_user_id() or "0"
                    query = """
                    INSERT INTO speedtesthistory
                    (user_id, server, download_speed_in_mbps, upload_speed_in_mbps, latency_in_ms)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    values = (uid, server_json,download_mbps,upload_mbps,ping_val)
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
            if not getattr(self, 'user_id', None) or self.user_id == "0":
                return "0"
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
            if not getattr(self, 'user_id', None) or self.user_id == "0":
                return "0"
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
                    "location": f"{server.get('name')}",
                    "country" : f"{server.get('country')}",
                    "sponsor": server.get("sponsor"),
                    "url": server.get("url")
                })
            return server_list
        except (ValueError, BufferError, OSError) as E:
            return {"error": f"Failed to retrieve servers: {E}"}
    def speedHistory(self):
        try:
            self.conn = mslc.connect(host="localhost", user="root", database="life_desk")
            self.cursor = self.conn.cursor(dictionary=True)
            if self.conn.is_connected():
                # require a user id to fetch user-specific history
                uid = getattr(self, 'user_id', None) or get_current_user_id() or "0"
                if uid == "0":
                    return "0"
                query = "SELECT * FROM speedtesthistory WHERE user_id = %s"
                self.cursor.execute(query, (uid,))
                history = self.cursor.fetchall()
                return history
            self.cursor.execute(query)
            self.conn.commit()
            print("Everything Displayed")
        except mslc.Error as E:
            print("Database Error:", E)
            return None
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class PasswordManager(LifeDesk):
    def __init__(self, host="localhost", user="root", password="", database="life_desk", user_id=None):
        # set instance user id from passed value or global
        try:
            self.user_id = str(user_id) if user_id is not None else get_current_user_id() or "0"
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.conn.cursor(dictionary=True)
            self._create_passwords_table()
        except (ConnectionError,ConnectionResetError) as E:
            print("Error ",E)
    
    def _create_passwords_table(self):
        """Create passwords table if it doesn't exist"""
        try:
            self.cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'life_desk' AND TABLE_NAME = 'passwords'
            """)
            if self.cursor.fetchone():
                return
            
            create_table_query = """CREATE TABLE IF NOT EXISTS passwords (
                password_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                site_name VARCHAR(255) NOT NULL,
                site_url VARCHAR(500),
                login_username VARCHAR(255) NOT NULL,
                encrypted_password VARCHAR(500) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("Passwords table created successfully")
        except Exception as E:
            print(f"Error creating passwords table: {E}")

    def add_password(self, user_id: int = None, site_name: str = "", site_url: str = "",
                     login_username: str = "", plain_password: str = "", notes: str = ""):
        # determine which user id to use
        uid = str(user_id) if user_id is not None else getattr(self, 'user_id', None) or get_current_user_id() or "0"
        if uid == "0":
            return "0"
        encrypted = generate_password_hash(plain_password)
        now = datetime.now()
        query = """
            INSERT INTO passwords (user_id, site_name, site_url, login_username,
                                   encrypted_password, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (uid, site_name, site_url, login_username,
                                     encrypted, notes, now, now))
        self.conn.commit()
        print(f" Password for '{site_name}' added.")

    def update_password(self, password_id: int, new_password: str):
        encrypted = generate_password_hash(new_password)
        now = datetime.now()
        query = """
            UPDATE passwords
            SET encrypted_password = %s, updated_at = %s
            WHERE password_id = %s
        """
        self.cursor.execute(query, (encrypted, now, password_id))
        self.conn.commit()
        if self.cursor.rowcount:
            print(f"Password ID {password_id} updated.")
        else:
            print(f"Password ID {password_id} not found.")

    def showAllInfo(self):
        uid = getattr(self, 'user_id', None) or get_current_user_id() or "0"
        if uid == "0":
            return "0"
        query = """
            SELECT password_id, user_id, site_name, site_url, login_username,
                   encrypted_password, notes, created_at, updated_at
            FROM passwords
            WHERE user_id = %s
            ORDER BY created_at DESC
        """
        self.cursor.execute(query, (uid,))
        results = self.cursor.fetchall()
        if not results:
            print("No passwords stored.")
            return
        for r in results:
            print(f"─────────────────────────────────")
            print(f"  ID:         {r['password_id']}")
            print(f"  User ID:    {r['user_id']}")
            print(f"  Site Name:  {r['site_name']}")
            print(f"  Site URL:   {r['site_url']}")
            print(f"  Username:   {r['login_username']}")
            print(f"  Encrypted:  {r['encrypted_password'][:50]}...")
            print(f"  Notes:      {r['notes']}")
            print(f"  Created:    {r['created_at']}")
            print(f"  Updated:    {r['updated_at']}")
        print(f"─────────────────────────────────")
        print(f"Total: {len(results)} entries")
