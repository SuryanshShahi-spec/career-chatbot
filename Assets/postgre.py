"""
postgre.py — PostgreSQL user auth with comprehensive error handling.

Error handling:
  - get_db_c() retries up to 2 times on OperationalError (transient connection resets)
  - All functions use try/except/finally to guarantee cursor/connection closure
  - register_user: distinguishes UniqueViolation from other DB errors
  - login_user: full try/except/finally; connection closed in all paths
  - get_user_profile / update_user_profile: consistent error handling
  - All DB errors logged to logs/api_errors.log
"""

import os
import time
import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor
import bcrypt
import jwt
import datetime
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Assets"))

from errors import get_logger, DatabaseError

load_dotenv()

logger = get_logger("postgre")

JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")

# ── DB connection with retry ───────────────────────────────────────────────────

def get_db_c(retries: int = 2, base_delay: float = 1.0):
    """
    Create and return a psycopg2 database connection.
    Retries up to `retries` times on OperationalError (e.g. transient connection resets).

    Raises:
        DatabaseError if the connection cannot be established after all attempts.
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME", "your_database_name"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "your_pgadmin_password"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                connect_timeout=5,
            )
            logger.debug("DB connection established (attempt %d).", attempt + 1)
            return conn
        except psycopg2.OperationalError as exc:
            last_exc = exc
            wait = base_delay * (2 ** attempt)
            logger.warning(
                "DB connection failed (attempt %d/%d): %s. Retrying in %.1fs...",
                attempt + 1, retries + 1, exc, wait,
            )
            if attempt < retries:
                time.sleep(wait)

    logger.error("All DB connection attempts failed: %s", last_exc)
    raise DatabaseError(f"Could not connect after {retries + 1} attempts: {last_exc}")


# ── 0. DATABASE INITIALISATION ────────────────────────────────────────────────

def init_db() -> None:
    """
    Create the users table if it does not already exist.
    Safe to call on every startup (uses CREATE TABLE IF NOT EXISTS).
    """
    conn = cursor = None
    try:
        conn = get_db_c()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id               SERIAL PRIMARY KEY,
                full_name        VARCHAR(255) NOT NULL,
                email            VARCHAR(255) UNIQUE NOT NULL,
                password_hash    TEXT NOT NULL,
                phone            VARCHAR(20),
                profile_picture  TEXT,
                last_login       TIMESTAMPTZ,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
        logger.debug("users table verified / created.")
        print("[OK] Database initialised successfully.")
    except DatabaseError as exc:
        logger.error("init_db: DB unavailable: %s", exc)
        print(f"[ERROR] Database unavailable: {exc}")
        raise
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        logger.error("init_db: DB error: %s", exc)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ── 1. USER REGISTRATION ───────────────────────────────────────────────────────

def register_user(full_name: str, email: str, password: str, phone: str = None) -> dict:
    """
    Register a new user. Hashes the password with bcrypt before storing.

    Returns a dict with keys: success (bool), message (str), and on success: user_id, email.
    """
    if not all([full_name, email, password]):
        return {"success": False, "message": "full_name, email, and password are all required."}

    # Hash password safely
    try:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except Exception as exc:
        logger.error("Password hashing failed: %s", exc)
        return {"success": False, "message": "Internal error during password processing."}

    conn = cursor = None
    try:
        conn = get_db_c()
        cursor = conn.cursor()
        query = """
        INSERT INTO users (full_name, email, password_hash, phone)
        VALUES (%s, %s, %s, %s) RETURNING id, email;
        """
        cursor.execute(query, (full_name, email, hashed_password, phone))
        user = cursor.fetchone()
        conn.commit()
        logger.debug("Registered new user: %s (id=%s)", email, user[0])
        return {"success": True, "message": "User registered successfully.", "user_id": user[0], "email": user[1]}

    except psycopg2.errors.UniqueViolation:
        if conn:
            conn.rollback()
        logger.info("Registration attempt with duplicate email: %s", email)
        return {"success": False, "message": "An account with this email already exists."}

    except psycopg2.OperationalError as exc:
        if conn:
            conn.rollback()
        logger.error("DB operational error during register_user: %s", exc)
        return {"success": False, "message": "Database connection error. Please try again."}

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        logger.error("DB error during register_user: %s", exc)
        return {"success": False, "message": "A database error occurred. Please try again."}

    except DatabaseError as exc:
        logger.error("Could not connect to DB for register_user: %s", exc)
        return {"success": False, "message": "Database unavailable. Please try again later."}

    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error in register_user: %s", exc)
        return {"success": False, "message": f"Unexpected error: {exc}"}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ── 2. USER LOGIN ──────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user by email + password.
    On success, updates last_login and returns a JWT token.

    Returns a dict with keys: success (bool), message (str), and on success: token.
    """
    if not email or not password:
        return {"success": False, "message": "Email and password are required."}

    conn = cursor = None
    try:
        conn = get_db_c()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s;", (email,))
        user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "Invalid email or password."}

        # Verify password
        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return {"success": False, "message": "Invalid email or password."}

        # Update last_login
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s;", (user["id"],))
        conn.commit()

        # Generate JWT Token valid for 24 hours
        token_payload = {
            "user_id": str(user["id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
        logger.debug("User logged in: %s (id=%s)", email, user["id"])
        return {"success": True, "token": token}

    except psycopg2.OperationalError as exc:
        if conn:
            conn.rollback()
        logger.error("DB operational error during login_user: %s", exc)
        return {"success": False, "message": "Database connection error. Please try again."}

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        logger.error("DB error during login_user: %s", exc)
        return {"success": False, "message": "A database error occurred. Please try again."}

    except DatabaseError as exc:
        logger.error("Could not connect to DB for login_user: %s", exc)
        return {"success": False, "message": "Database unavailable. Please try again later."}

    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error in login_user: %s", exc)
        return {"success": False, "message": f"Unexpected error: {exc}"}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ── 3. GET PROFILE DATA ────────────────────────────────────────────────────────

def get_user_profile(token: str) -> dict:
    """
    Decode a JWT token and return the corresponding user profile.

    Returns a dict with keys: success (bool), message (str), and on success: profile (dict).
    """
    if not token:
        return {"success": False, "message": "Token is required."}

    # Decode token first (no DB call needed for this)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
    except jwt.ExpiredSignatureError:
        return {"success": False, "message": "Token expired. Please login again."}
    except jwt.InvalidTokenError as exc:
        return {"success": False, "message": f"Invalid authentication token: {exc}"}

    conn = cursor = None
    try:
        conn = get_db_c()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
        SELECT id, full_name, email, phone, profile_picture, created_at
        FROM users WHERE id = %s;
        """
        cursor.execute(query, (user_id,))
        profile = cursor.fetchone()

        if not profile:
            return {"success": False, "message": "User not found."}

        return {"success": True, "profile": dict(profile)}

    except psycopg2.OperationalError as exc:
        logger.error("DB operational error during get_user_profile: %s", exc)
        return {"success": False, "message": "Database connection error. Please try again."}

    except psycopg2.Error as exc:
        logger.error("DB error during get_user_profile: %s", exc)
        return {"success": False, "message": "A database error occurred. Please try again."}

    except DatabaseError as exc:
        logger.error("Could not connect to DB for get_user_profile: %s", exc)
        return {"success": False, "message": "Database unavailable. Please try again later."}

    except Exception as exc:
        logger.exception("Unexpected error in get_user_profile: %s", exc)
        return {"success": False, "message": f"Unexpected error: {exc}"}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ── 4. UPDATE PROFILE DATA ─────────────────────────────────────────────────────

def update_user_profile(
    token: str,
    full_name: str,
    phone: str,
    profile_picture: str = None,
) -> dict:
    """
    Decode a JWT token and update the user's profile fields.

    Returns a dict with keys: success (bool), message (str).
    """
    if not token:
        return {"success": False, "message": "Token is required."}

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
    except jwt.ExpiredSignatureError:
        return {"success": False, "message": "Token expired. Please login again."}
    except jwt.InvalidTokenError as exc:
        return {"success": False, "message": f"Invalid authentication token: {exc}"}

    conn = cursor = None
    try:
        conn = get_db_c()
        cursor = conn.cursor()

        query = """
        UPDATE users
        SET full_name = %s, phone = %s, profile_picture = %s
        WHERE id = %s;
        """
        cursor.execute(query, (full_name, phone, profile_picture, user_id))
        conn.commit()
        logger.debug("Profile updated for user_id=%s", user_id)
        return {"success": True, "message": "Profile updated successfully!"}

    except psycopg2.errors.UniqueViolation:
        if conn:
            conn.rollback()
        return {"success": False, "message": "Update conflict: that value is already in use."}

    except psycopg2.OperationalError as exc:
        if conn:
            conn.rollback()
        logger.error("DB operational error during update_user_profile: %s", exc)
        return {"success": False, "message": "Database connection error. Please try again."}

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        logger.error("DB error during update_user_profile: %s", exc)
        return {"success": False, "message": "A database error occurred. Please try again."}

    except DatabaseError as exc:
        logger.error("Could not connect to DB for update_user_profile: %s", exc)
        return {"success": False, "message": "Database unavailable. Please try again later."}

    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error in update_user_profile: %s", exc)
        return {"success": False, "message": f"Unexpected error: {exc}"}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
