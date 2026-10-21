"""User creation, authentication and identity lookup.

Credentials live in Django's `auth_user` table (Django owns the schema). The
application profile lives in `content.usuario`, linked through the same
`sub` string that Auth0 puts in the token, e.g. `auth0|42`.
"""

import re

from ..extensions import db
from ..models import AuthUser, Usuario
from ..permissions import ROLES, permissions_for_role
from .passwords import check_password, hash_password

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,80}$")
MIN_PASSWORD = 8

# Checked when the user does not exist, so "unknown user" and "wrong
# password" take about the same time and cannot be told apart.
_DUMMY_HASH = hash_password("not-a-real-password")


class RegistrationError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def normalize_username(value):
    return str(value or "").strip().lower()


def sub_for(auth_user):
    return f"auth0|{auth_user.id}"


def create_user(username, password, nombre=None, role="cliente"):
    username = normalize_username(username)
    role = (role or "cliente").strip().lower()

    if not USERNAME_RE.match(username):
        raise RegistrationError(
            "invalid_username",
            "Usuario: 3-80 caracteres, minúsculas, números, punto, guion o guion bajo.",
        )
    if len(str(password or "")) < MIN_PASSWORD:
        raise RegistrationError(
            "weak_password", f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres."
        )
    if role not in ROLES:
        raise RegistrationError("invalid_role", "Rol desconocido.")
    if AuthUser.query.filter_by(username=username).first():
        raise RegistrationError("username_taken", "Ese usuario ya existe.", 409)

    try:
        auth_user = AuthUser(
            username=username,
            password=hash_password(password),
            first_name=(nombre or username)[:150],
            last_name="",
            email=f"{username}@local.invalid",
            is_active=True,
        )
        db.session.add(auth_user)
        db.session.flush()  # assigns auth_user.id

        profile = Usuario(
            nombre=(nombre or username)[:100],
            apellido_paterno="",
            apellido_materno="",
            email=f"{username}@local.invalid",
            contrasena="!",  # legacy NOT NULL column: real hash lives in auth_user
            rol=role,
            sub=sub_for(auth_user),
        )
        db.session.add(profile)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return auth_user, profile


def authenticate(username, password):
    """Return (auth_user, profile) if the credentials are valid, else None."""
    username = normalize_username(username)
    auth_user = AuthUser.query.filter_by(username=username).first()
    if auth_user is None:
        check_password(_DUMMY_HASH, password)
        return None
    if not check_password(auth_user.password, password):
        return None

    profile = Usuario.query.filter_by(sub=sub_for(auth_user)).first()
    if profile is None or profile.eliminado:
        return None
    return auth_user, profile


def usuario_from_payload(payload):
    """Identity comes from the token's `sub`, never from the form."""
    sub = str(payload.get("sub", ""))
    if not sub:
        return None
    return Usuario.query.filter_by(sub=sub, eliminado=0).first()


def token_claims(profile, username=None):
    role = (profile.rol or "cliente").strip().lower()
    return {
        "sub": profile.sub,
        "username": username or profile.nombre,
        "role": role,
        "permissions": permissions_for_role(role),
    }
