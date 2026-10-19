"""
HelpDesk AI - Secure Local Authentication & Identity Module.
Implements genuine, production-style authentication using PBKDF2-HMAC-SHA256 password hashing,
unique cryptographic salts, server-side validation, password strength scoring,
and a persistent local SQLite user store.

Security Design & Controls:
- Algorithm: PBKDF2-HMAC-SHA256 with 120,000 iterations (NIST SP 800-132 compliant).
- Salt: 16-byte cryptographically secure random salt per user (os.urandom / secrets.token_bytes).
- Pepper / Secret: Server-side environment key (HELPDESK_AUTH_SECRET) combined during hashing.
- Verification: Constant-time comparison (hmac.compare_digest) to prevent timing attacks.
- Passwords: Plaintext passwords are NEVER stored, logged, or returned in user objects.

Deployment & Architecture Limitations:
- Lightweight embedded SQLite store suited for local, single-server, or private on-premise deployments.
- For distributed multi-tenant enterprise clusters, migrate to an enterprise IdP (e.g. SAML 2.0,
  OIDC, Azure AD, Okta) as documented in the Settings view.
"""

import os
import re
import sqlite3
import secrets
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("helpdesk.auth")

# Database file location
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth.db")

PBKDF2_ITERATIONS = 120_000

# Regular expression for email format validation (RFC-compliant standard pattern)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$")

# Standard unprivileged role assigned to self-registered users
STANDARD_ROLE = "Employee / Incident Reporter"


def get_auth_secret() -> str:
    """
    Retrieves the server-side authentication pepper / secret key.
    Prioritizes the HELPDESK_AUTH_SECRET environment variable.
    If not set in the environment, loads or creates a persistent 256-bit cryptographic
    random secret in a protected local file (.auth_secret), never using a hard-coded fallback.
    """
    secret = os.environ.get("HELPDESK_AUTH_SECRET", "").strip()
    if secret:
        return secret

    secret_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auth_secret")
    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                stored = f.read().strip()
                if stored:
                    return stored
        except Exception as e:
            logger.warning("Could not read .auth_secret file: %s", e)

    # Generate a cryptographically secure random 256-bit key and persist it locally
    new_secret = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(new_secret)
    except Exception as e:
        logger.warning("Could not write .auth_secret file: %s", e)
    return new_secret


def get_db_connection() -> sqlite3.Connection:
    """Creates a connection to the local SQLite authentication database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db() -> None:
    """
    Initializes the SQLite database schema if not present.
    Insecure demo accounts are NOT seeded automatically.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_demo_account(
    email: str = "alex.turner@enterprise.internal",
    full_name: str = "Alex Turner",
    password: str = "Password123!",
    role: str = "IT Service Desk Specialist"
) -> bool:
    """
    Explicit helper to seed a demonstration account only when explicitly invoked.
    Never executed automatically during system initialization.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email.strip().lower(),))
        if cursor.fetchone() is not None:
            return False
        pwd_hash, salt_hex = hash_password(password)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (email, full_name, password_hash, salt, role, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (email.strip().lower(), full_name.strip(), pwd_hash, salt_hex, role, now_str, now_str))
        conn.commit()
        return True
    finally:
        conn.close()


def hash_password(password: str, salt_bytes: Optional[bytes] = None) -> Tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a unique random salt and server secret.
    Returns (hex_hash, hex_salt).
    """
    if salt_bytes is None:
        salt_bytes = secrets.token_bytes(16)
    
    # Combine password with server-side pepper from get_auth_secret()
    auth_secret = get_auth_secret()
    combined = f"{password}:{auth_secret}".encode("utf-8")
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        combined,
        salt_bytes,
        PBKDF2_ITERATIONS
    )
    return derived_key.hex(), salt_bytes.hex()


def verify_password(password: str, salt_hex: str, stored_hash_hex: str) -> bool:
    """
    Verifies a password against the stored salt and hash using timing-attack resistant hmac.compare_digest.
    """
    try:
        salt_bytes = bytes.fromhex(salt_hex)
        computed_hash, _ = hash_password(password, salt_bytes=salt_bytes)
        return hmac.compare_digest(computed_hash, stored_hash_hex)
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """Validates email format syntax."""
    if not email or len(email.strip()) < 5:
        return False
    clean = email.strip()
    if ".." in clean:
        return False
    return bool(EMAIL_REGEX.match(clean))


def calculate_password_strength(password: str) -> Dict[str, Any]:
    """
    Evaluates password strength and returns score (0-4), label, color, and requirement flags.
    Requirements:
    1. At least 8 characters
    2. Uppercase letter
    3. Lowercase letter
    4. Numeric digit
    5. Special character
    """
    p = password or ""
    checks = {
        "min_length": len(p) >= 8,
        "has_upper": bool(re.search(r"[A-Z]", p)),
        "has_lower": bool(re.search(r"[a-z]", p)),
        "has_digit": bool(re.search(r"[0-9]", p)),
        "has_special": bool(re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]", p))
    }
    
    passed_count = sum(checks.values())
    
    if len(p) == 0:
        return {
            "score": 0,
            "label": "None",
            "color": "#94a3b8",
            "percent": 0,
            "checks": checks,
            "feedback": "Enter a secure password."
        }
    elif passed_count <= 2:
        return {
            "score": 1,
            "label": "Weak",
            "color": "#f43f5e",
            "percent": 25,
            "checks": checks,
            "feedback": "Password is too weak. Add numbers, symbols, and mixed case."
        }
    elif passed_count == 3:
        return {
            "score": 2,
            "label": "Fair",
            "color": "#f59e0b",
            "percent": 50,
            "checks": checks,
            "feedback": "Moderate strength. Consider adding special characters."
        }
    elif passed_count == 4:
        return {
            "score": 3,
            "label": "Good",
            "color": "#0d9488",
            "percent": 75,
            "checks": checks,
            "feedback": "Strong password meeting standard IT requirements."
        }
    else:
        return {
            "score": 4,
            "label": "Very Strong",
            "color": "#10b981",
            "percent": 100,
            "checks": checks,
            "feedback": "Excellent! Meets all enterprise security criteria."
        }


def register_user(
    email: str,
    full_name: str,
    password: str,
    confirm_password: str,
    role: str = STANDARD_ROLE,
    allow_privileged: bool = False
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registers a new user with full server-side validation.
    Prevents self-assignment of privileged roles (IT Support, Admin/SecOps)
    unless allow_privileged is explicitly authorized.
    Returns (success_bool, message, user_dict_or_None).
    """
    clean_email = email.strip().lower()
    clean_name = full_name.strip()
    clean_role = (role or STANDARD_ROLE).strip()

    # Prevent self-assignment of privileged roles
    from rbac import normalize_role, ROLE_EMPLOYEE
    canonical_role = normalize_role(clean_role)
    if canonical_role != ROLE_EMPLOYEE and not allow_privileged:
        return False, "Self-assignment of privileged roles is not permitted. Standard accounts receive the Employee role. Contact an administrator for elevated access.", None
    
    if not clean_email or not validate_email(clean_email):
        return False, "Please enter a valid corporate email address (e.g., user@company.com).", None
    
    if not clean_name:
        return False, "Please provide your full legal or employee name.", None
        
    if not password:
        return False, "Password cannot be blank.", None
        
    if len(password) < 8:
        return False, "Password must be at least 8 characters long.", None
        
    if password != confirm_password:
        return False, "Passwords do not match. Please verify and re-enter.", None
        
    strength = calculate_password_strength(password)
    if strength["score"] < 2:
        return False, f"Password is too weak: {strength['feedback']}", None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
        if cursor.fetchone() is not None:
            return False, "An account with this corporate email address already exists.", None

        pwd_hash, salt_hex = hash_password(password)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (email, full_name, password_hash, salt, role, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (clean_email, clean_name, pwd_hash, salt_hex, clean_role, now_str, now_str))
        conn.commit()

        user_id = cursor.lastrowid
        user_info = {
            "id": user_id,
            "email": clean_email,
            "full_name": clean_name,
            "role": clean_role,
            "created_at": now_str,
            "last_login": now_str
        }
        return True, "Account created successfully.", user_info
    except sqlite3.IntegrityError:
        return False, "An account with this email address already exists.", None
    except Exception as e:
        logger.error("Registration error: %s", e, exc_info=True)
        return False, "Registration failed due to a system error. Please try again.", None
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticates a user with email and password against the SQLite store.
    Updates last_login timestamp upon success.
    Returns (success_bool, message, user_dict_or_None).
    """
    clean_email = email.strip().lower()
    
    if not clean_email or not password:
        return False, "Please enter both email and password.", None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, full_name, password_hash, salt, role, created_at, last_login
            FROM users WHERE email = ?
        """, (clean_email,))
        row = cursor.fetchone()

        if row is None:
            # Generic error to prevent email enumeration
            return False, "Invalid email address or password.", None

        stored_hash = row["password_hash"]
        salt_hex = row["salt"]

        if not verify_password(password, salt_hex, stored_hash):
            return False, "Invalid email address or password.", None

        # Update last login timestamp
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_str, row["id"]))
        conn.commit()

        user_info = {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "created_at": row["created_at"],
            "last_login": now_str
        }
        return True, "Authentication successful.", user_info
    except Exception as e:
        logger.error("Authentication error: %s", e, exc_info=True)
        return False, "Authentication failed due to a system error. Please try again.", None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves safe user profile metadata (never exposing hash or salt)."""
    clean_email = email.strip().lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, role, created_at, last_login FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def change_password(
    email: str,
    current_password: str,
    new_password: str,
    confirm_new_password: str
) -> Tuple[bool, str]:
    """
    Safely changes an existing user's password.
    Validates current password using timing-safe comparison, checks new password
    complexity, and updates the database with a freshly derived salt and hash.
    Returns (success_bool, message).
    """
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return False, "User email is required."

    if not current_password:
        return False, "Please provide your current password."

    if not new_password:
        return False, "Please enter a new password."

    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long."

    if new_password != confirm_new_password:
        return False, "New passwords do not match. Please verify and re-enter."

    strength = calculate_password_strength(new_password)
    if strength["score"] < 2:
        return False, f"Password is too weak: {strength['feedback']}"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash, salt FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            return False, "User account not found."

        stored_hash = row["password_hash"]
        salt_hex = row["salt"]

        if not verify_password(current_password, salt_hex, stored_hash):
            return False, "Current password is incorrect."

        new_hash, new_salt = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (new_hash, new_salt, row["id"])
        )
        conn.commit()
        return True, "Password changed successfully."
    except Exception as e:
        logger.error("Password update error for %s: %s", clean_email, e, exc_info=True)
        return False, "Failed to update password due to a system error. Please try again."
    finally:
        conn.close()


# Initialize database automatically upon module import
init_auth_db()
