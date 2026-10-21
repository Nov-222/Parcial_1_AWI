"""JWT authentication.

    AuthError             -> error with its HTTP status code
    get_token_auth_header -> reads "Authorization: Bearer <token>"
    verify_decode_jwt     -> checks signature, expiry and issuer
    requires_auth         -> decorator: token (401) and permission (403)
"""

from .decorators import get_token_auth_header, requires_auth
from .errors import AuthError
from .tokens import create_access_token, verify_decode_jwt

__all__ = [
    "AuthError",
    "create_access_token",
    "get_token_auth_header",
    "requires_auth",
    "verify_decode_jwt",
]
