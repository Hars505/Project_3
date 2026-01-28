from abc import abstractmethod,ABC
import os
import datetime as dt
import time
import mysql.connector as mslc
import speedtest_cli as st
import hashlib as hl
import bcrypt as bt
from werkzeug.security import check_password_hash,generate_password_hash
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
        """Verify credentials against the database.

        Returns True if the email exists and the password matches the stored hash,
        otherwise returns False.

        Raises:
            mysql.connector.Error: if a database error occurs while querying.
        """
        try:
            # Ensure parameter is passed as a single-element tuple
            self.cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
            row = self.cursor.fetchone()
            if not row:
                return False
            stored_hash = row.get("password")
            return check_password_hash(stored_hash, password)
        except mslc.Error:
            # Database error: propagate to caller
            raise
        except Exception:
            # Unknown error: propagate to caller
            raise


class LifeDeskManager(LifeDesk):
    """Concrete implementation of LifeDesk for handling user verification."""
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
            raise
    
    def _create_users_table(self):
        """Create users table if it doesn't exist."""
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("Users table verified/created successfully")
        except mslc.Error as E:
            print(f"Error creating users table: {E}")
            raise
    
    def menu(self):
        """Placeholder for menu method."""
        pass
    
    def verify_user(self, email, password):
        """Verify user credentials and return user data if valid.
        
        Returns:
            dict: User data if credentials are valid, None otherwise.
        """
        if self.test(password, email) is True:
            try:
                self.cursor.execute("SELECT name, email FROM users WHERE email = %s", (email,))
                user = self.cursor.fetchone()
                return user
            except mslc.Error as E:
                print("Error fetching user data:", E)
                return None
        return None
    
    def register_user(self, name, email, password):
        """Register a new user in the database.
        
        Args:
            name: User's name
            email: User's email
            password: User's password (will be hashed)
        
        Returns:
            dict: Success status, message, and status code
        """
        try:
            # Check if user already exists
            self.cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if self.cursor.fetchone():
                return {
                    "success": False,
                    "message": "User already exists",
                    "status_code": 409
                }
            
            # Hash password and insert new user
            hashed_password = generate_password_hash(password)
            self.cursor.execute(
                "INSERT INTO users (User_name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
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
