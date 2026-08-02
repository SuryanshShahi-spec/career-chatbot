"""
auth.py — Authentication facade for Job Search Assistant.

Wraps the PostgreSQL user functions from Data/postgre.py and exposes a
clean, stateless auth API used by chatbot.py and any future web layer.

Features:
  - register()        : create account with validation
  - login()           : authenticate and return a signed JWT
  - require_auth()    : decorator / context check — validates JWT on entry
  - get_profile()     : fetch profile for a validated token
  - update_profile()  : update fields for a validated token
  - logout()          : client-side token invalidation helper
  - AuthSession       : lightweight dataclass carrying decoded token claims

All functions return typed dicts with { success, message, ... } so callers
never need to catch exceptions — errors are surfaced as structured responses.

Usage (standalone):
    from auth import auth_service
    result = auth_service.register("Alice", "alice@example.com", "Pass1234!")
    session = auth_service.login("alice@example.com", "Pass1234!")
    if session["success"]:
        profile = auth_service.get_profile(session["token"])

Usage (as decorator):
    @auth_service.require_auth
    def protected_action(session: AuthSession):
        print(f"Hello, {session.user_id}")
"""

import os
import re
import sys
import functools
from dataclasses import dataclass
from typing import Callable, Optional

import jwt
from dotenv import load_dotenv

# ── Resolve paths so auth.py works whether run from Assets/ or project root ────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, "..")
sys.path.insert(0, os.path.join(_ROOT, "Assets"))
sys.path.insert(0, os.path.join(_ROOT, "Data"))

from errors import get_logger, AuthError as _AuthError

# Import DB layer — relative path handled above
from postgre import register_user, login_user, get_user_profile, update_user_profile

load_dotenv(dotenv_path=os.path.join(_ROOT, ".env"))

logger = get_logger("auth")

JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")

# ── Password policy ────────────────────────────────────────────────────────────

_MIN_PASSWORD_LENGTH = 8
_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"
)  # at least one lower, upper, digit; min 8 chars

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── AuthSession dataclass ──────────────────────────────────────────────────────

@dataclass
class AuthSession:
    """
    Decoded, validated JWT claims carried throughout a request.

    Attributes:
        user_id:   String UUID of the authenticated user.
        token:     The raw JWT string (for passing to downstream functions).
    """
    user_id: str
    token: str


# ── AuthService class ──────────────────────────────────────────────────────────

class AuthService:
    """
    Stateless authentication service.

    All methods are side-effect-free except for DB writes (register, login
    timestamp, profile update). Every method returns a dict with at minimum:
        { "success": bool, "message": str }
    """

    # ── Validation helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_email(email: str) -> Optional[str]:
        """Return error string if invalid, else None."""
        if not email or not isinstance(email, str):
            return "Email is required."
        if not _EMAIL_RE.match(email.strip()):
            return f"'{email}' is not a valid email address."
        return None

    @staticmethod
    def _validate_password(password: str) -> Optional[str]:
        """Return error string if policy not met, else None."""
        if not password:
            return "Password is required."
        if len(password) < _MIN_PASSWORD_LENGTH:
            return f"Password must be at least {_MIN_PASSWORD_LENGTH} characters."
        if not _PASSWORD_RE.match(password):
            return (
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            )
        return None

    @staticmethod
    def _decode_token(token: str) -> dict:
        """
        Decode and validate a JWT. Returns the payload dict on success.

        Raises:
            jwt.ExpiredSignatureError  if token is expired.
            jwt.InvalidTokenError      if token is malformed.
        """
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

    # ── Public API ─────────────────────────────────────────────────────────────

    def register(
        self,
        full_name: str,
        email: str,
        password: str,
        phone: str = None,
    ) -> dict:
        """
        Register a new user account.

        Validates email format and password policy before hitting the DB.

        Returns:
            { success, message }  on failure
            { success, message, user_id, email }  on success
        """
        # Input validation
        if not full_name or not full_name.strip():
            return {"success": False, "message": "Full name is required."}

        email_err = self._validate_email(email)
        if email_err:
            return {"success": False, "message": email_err}

        pwd_err = self._validate_password(password)
        if pwd_err:
            return {"success": False, "message": pwd_err}

        logger.debug("Registering user: %s", email)
        result = register_user(full_name.strip(), email.strip().lower(), password, phone)

        if result.get("success"):
            logger.info("New user registered: %s (id=%s)", email, result.get("user_id"))
        else:
            logger.info("Registration rejected for %s: %s", email, result.get("message"))

        return result

    def login(self, email: str, password: str) -> dict:
        """
        Authenticate a user and return a JWT.

        Returns:
            { success, message }          on failure
            { success, token, message }   on success
        """
        email_err = self._validate_email(email)
        if email_err:
            return {"success": False, "message": email_err}

        if not password:
            return {"success": False, "message": "Password is required."}

        logger.debug("Login attempt: %s", email)
        result = login_user(email.strip().lower(), password)

        if result.get("success"):
            logger.info("User logged in: %s", email)
        else:
            logger.info("Login failed for %s: %s", email, result.get("message"))

        return result

    def verify_token(self, token: str) -> dict:
        """
        Validate a JWT without touching the DB.

        Returns:
            { success: True,  session: AuthSession }  if valid
            { success: False, message: str }           if invalid / expired
        """
        if not token:
            return {"success": False, "message": "No token provided."}
        try:
            payload = self._decode_token(token)
            session = AuthSession(user_id=payload["user_id"], token=token)
            return {"success": True, "session": session}
        except jwt.ExpiredSignatureError:
            return {"success": False, "message": "Session expired. Please log in again."}
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid token: %s", exc)
            return {"success": False, "message": "Invalid authentication token."}

    def get_profile(self, token: str) -> dict:
        """
        Fetch the full profile for the user identified by token.

        Returns:
            { success, message }           on failure
            { success, profile: dict }     on success
        """
        check = self.verify_token(token)
        if not check["success"]:
            return check
        return get_user_profile(token)

    def update_profile(
        self,
        token: str,
        full_name: str,
        phone: str,
        profile_picture: str = None,
    ) -> dict:
        """
        Update mutable profile fields for the authenticated user.

        Returns:
            { success, message }
        """
        check = self.verify_token(token)
        if not check["success"]:
            return check

        if not full_name or not full_name.strip():
            return {"success": False, "message": "Full name cannot be empty."}

        return update_user_profile(token, full_name.strip(), phone, profile_picture)

    def logout(self, token: str) -> dict:
        """
        Client-side logout helper.

        JWTs are stateless — true server-side invalidation requires a token
        blocklist (Redis or DB). This method validates the token and returns
        a confirmation so clients can safely discard it.

        Returns:
            { success, message }
        """
        check = self.verify_token(token)
        if not check["success"]:
            return check
        session: AuthSession = check["session"]
        logger.info("User logged out: user_id=%s", session.user_id)
        return {"success": True, "message": "Logged out successfully. Please discard your token."}

    def require_auth(self, func: Callable) -> Callable:
        """
        Decorator that injects a validated AuthSession as the first argument.

        The wrapped function must accept token: str as its first argument.
        If the token is invalid the decorated function is NOT called and a
        failure dict is returned instead.

        Usage:
            @auth_service.require_auth
            def do_something(session: AuthSession, other_arg):
                ...

            result = do_something(token="<jwt>", other_arg="value")
        """
        @functools.wraps(func)
        def wrapper(token: str, *args, **kwargs):
            check = self.verify_token(token)
            if not check["success"]:
                return check  # { success: False, message: ... }
            return func(check["session"], *args, **kwargs)
        return wrapper


# ── Singleton ──────────────────────────────────────────────────────────────────

auth_service = AuthService()


# ── CLI smoke test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== Auth Service Smoke Test ===\n")

    # 1. Register
    reg = auth_service.register(
        full_name="Test User",
        email="smoketest@example.com",
        password="SmokeTest1",
        phone="9999999999",
    )
    print(f"Register : {reg}")

    # 2. Login
    login_res = auth_service.login("smoketest@example.com", "SmokeTest1")
    print(f"Login    : {{'success': {login_res['success']}, 'token': '...'}}")

    if login_res["success"]:
        token = login_res["token"]

        # 3. Verify token
        verify = auth_service.verify_token(token)
        print(f"Verify   : success={verify['success']}, user_id={verify['session'].user_id}")

        # 4. Get profile
        profile_res = auth_service.get_profile(token)
        if profile_res["success"]:
            print(f"Profile  : {profile_res['profile']['full_name']}, {profile_res['profile']['email']}")
        else:
            print(f"Profile  : {profile_res}")

        # 5. Update profile
        upd = auth_service.update_profile(token, "Test User Updated", "8888888888")
        print(f"Update   : {upd}")

        # 6. Logout
        out = auth_service.logout(token)
        print(f"Logout   : {out}")

    # 7. Bad password policy
    bad = auth_service.register("X", "x@example.com", "weak")
    print(f"Bad pwd  : {bad}")

    # 8. Bad email
    bad2 = auth_service.register("X", "not-an-email", "ValidPass1")
    print(f"Bad email: {bad2}")

    # 9. require_auth decorator
    @auth_service.require_auth
    def greet(session: AuthSession):
        return f"Hello, user_id={session.user_id}"

    if login_res["success"]:
        print(f"Decorator: {greet(login_res['token'])}")
    print(f"Bad token: {greet('invalid.token.here')}")

    print("\n=== Done ===\n")
