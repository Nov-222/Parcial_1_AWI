"""Passwords stored in Django's `auth_user.password`.

The hash format is exactly Django's PBKDF2-SHA256 format
(`pbkdf2_sha256$iterations$salt$base64`), so a user created from Flask can
still be authenticated by Django and vice versa. Werkzeug's default scrypt
hash does not fit the 128 characters of `auth_user.password`.
"""

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(6)  # 12 characters, like Django's salts
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    )
    encoded = base64.b64encode(digest).decode("ascii").strip()
    return f"{ALGORITHM}${ITERATIONS}${salt}${encoded}"


def check_password(encoded: str, password: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        encoded_calculated = base64.b64encode(calculated).decode("ascii").strip()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(encoded_calculated, digest)
