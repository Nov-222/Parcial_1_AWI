from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

from .errors import AuthError

ALGORITHM = "HS256"


def create_access_token(sub, username, role, permissions):
    """Sign a short-lived JWT that says who the user is and what it may do."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),  # the Auth0-style id, always a string
        "username": username,
        "role": role,
        "permissions": list(permissions),
        "iat": now,
        "exp": now + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"]),
        "iss": current_app.config["JWT_ISSUER"],
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm=ALGORITHM)


def verify_decode_jwt(token):
    """Return the payload of a valid token or raise AuthError(401).

    `algorithms` is an explicit allow-list: never trust the `alg` the token
    claims for itself, or an attacker could send `"alg": "none"`.
    """
    try:
        return jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[ALGORITHM],
            issuer=current_app.config["JWT_ISSUER"],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise AuthError({"code": "token_expired", "description": "Token expired."}, 401)
    except jwt.InvalidTokenError:
        raise AuthError({"code": "invalid_token", "description": "Invalid token."}, 401)
