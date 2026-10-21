from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .service import (
    RegistrationError,
    authenticate,
    create_user,
    token_claims,
)
from .tokens import create_access_token

bp = Blueprint("auth", __name__, url_prefix="/auth")


# --------------------------------------------------------------------- JSON
# Same contract as GUIA-LOGIN-JWT: JSON in, signed JWT out, no cookies.


def json_error(status, code, message):
    return (
        jsonify(
            {"success": False, "error": status, "code": code, "message": message}
        ),
        status,
    )


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        auth_user, profile = create_user(
            data.get("username"),
            data.get("password"),
            nombre=data.get("nombre"),
        )
    except RegistrationError as err:
        return json_error(err.status, err.code, err.message)

    return (
        jsonify(
            {
                "success": True,
                "user": {
                    "id": str(profile.id),
                    "username": auth_user.username,
                    "sub": profile.sub,
                    "role": profile.rol,
                },
            }
        ),
        201,
    )


@bp.post("/login")
def login():
    """JSON credentials in, signed JWT out. The client keeps the token."""
    data = request.get_json(silent=True) or {}
    result = authenticate(data.get("username"), data.get("password"))
    if result is None:
        # Same message for unknown user and wrong password: no enumeration.
        return json_error(401, "invalid_credentials", "Usuario o contraseña inválidos.")

    _, profile = result
    claims = token_claims(profile, result[0].username)
    return jsonify(
        {
            "access_token": create_access_token(
                claims["sub"], claims["username"], claims["role"], claims["permissions"]
            ),
            "token_type": "Bearer",
            "expires_in": current_app.config["JWT_EXPIRES_MINUTES"] * 60,
        }
    )


# ---------------------------------------------------------------------- HTML
# The browser cannot send an Authorization header from a plain <form>, so the
# Jinja pages keep the same JWT in the signed Flask session after login.


def _safe_next(value):
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("views.index")


@bp.get("/ingresar")
def login_form():
    if session.get("access_token"):
        return redirect(url_for("views.index"))
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.post("/ingresar")
def login_submit():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    result = authenticate(username, password)
    if result is None:
        flash("Usuario o contraseña inválidos.", "error")
        return (
            render_template(
                "auth/login.html",
                next=request.form.get("next", ""),
                username=username,
            ),
            401,
        )

    _, profile = result
    claims = token_claims(profile, result[0].username)
    session["access_token"] = create_access_token(
        claims["sub"], claims["username"], claims["role"], claims["permissions"]
    )
    return redirect(_safe_next(request.form.get("next")))


@bp.get("/registro")
def register_form():
    return render_template("auth/register.html")


@bp.post("/registro")
def register_submit():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    nombre = request.form.get("nombre", "")
    try:
        create_user(username, password, nombre=nombre)
    except RegistrationError as err:
        flash(err.message, "error")
        return (
            render_template(
                "auth/register.html", username=username, nombre=nombre
            ),
            err.status,
        )

    result = authenticate(username, password)
    if result is not None:
        _, profile = result
        claims = token_claims(profile, result[0].username)
        session["access_token"] = create_access_token(
            claims["sub"],
            claims["username"],
            claims["role"],
            claims["permissions"],
        )
    flash("Cuenta creada. Ya puedes hacer pedidos.", "success")
    return redirect(url_for("views.index"))


@bp.route("/salir", methods=["GET", "POST"])
def logout():
    session.pop("access_token", None)
    flash("Sesión cerrada.", "success")
    return redirect(url_for("views.index"))
