from functools import wraps

from flask import request, session

from .errors import AuthError
from .tokens import verify_decode_jwt


def get_token_auth_header():
    """Return the raw JWT from `Authorization: Bearer <token>`.

    Same validations and error codes as GUIA-LOGIN-JWT (section 9), so the
    JSON API behaves exactly like the guide and can be tested with curl.
    """
    auth = request.headers.get("Authorization", "").strip()
    if not auth:  # absent, empty or only spaces: split() would give []
        raise AuthError(
            {
                "code": "authorization_header_missing",
                "description": "Authorization header is expected.",
            },
            401,
        )
    parts = auth.split()
    if parts[0].lower() != "bearer":
        raise AuthError(
            {
                "code": "invalid_header",
                "description": 'Authorization header must start with "Bearer".',
            },
            401,
        )
    if len(parts) == 1:
        raise AuthError(
            {"code": "invalid_header", "description": "Token not found."}, 401
        )
    if len(parts) > 2:
        raise AuthError(
            {
                "code": "invalid_header",
                "description": 'Authorization header must be "Bearer <token>".',
            },
            401,
        )
    return parts[1]


def get_request_token():
    """Header first (API/curl), then the Flask session (Jinja pages).

    The guide sends the token only in the header. For server-rendered pages we
    also accept the signed session cookie, because a browser <form> cannot add
    an Authorization header. The token is still the same JWT: the session only
    stores it, authentication is always verified against the signature.
    """
    if request.headers.get("Authorization", "").strip():
        return get_token_auth_header()
    token = session.get("access_token")
    if token:
        return token
    raise AuthError(
        {
            "code": "authorization_header_missing",
            "description": "Authorization header is expected.",
        },
        401,
    )


def _protect(view, permission):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = get_request_token()
        payload = verify_decode_jwt(token)
        if permission and permission not in payload.get("permissions", []):
            raise AuthError(
                {
                    "code": "permission_denied",
                    "description": f"Permission required: {permission}.",
                },
                403,
            )
        return view(payload, *args, **kwargs)

    return wrapper


def requires_auth(arg=None, *, permission=None):
    """Decorator with or without a permission argument.

        @requires_auth                      # any valid token
        @requires_auth("create:pedidos")    # token + permission, else 403
        @requires_auth(permission="read:pedidos")

    The route receives the decoded payload as its first argument.
    """
    if callable(arg):
        return _protect(arg, None)

    required = permission if permission is not None else arg

    def decorator(view):
        return _protect(view, required)

    return decorator
