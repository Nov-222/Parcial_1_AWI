import os

import click
from flask import Flask, jsonify, render_template, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

from api_flask.auth import AuthError
from api_flask.auth.handlers import handle_auth_error
from api_flask.config import Config
from api_flask.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__, static_url_path="/assets")
    app.config.from_object(config_class)

    if len(app.config["JWT_SECRET_KEY"].encode()) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 bytes long.")

    # Behind Nginx: use X-Forwarded-* so url_for() builds https:// URLs.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)

    # Importar los modelos para registrarlos en el contexto
    from api_flask import models  # noqa: F401

    from api_flask.auth.routes import bp as auth_bp
    from api_flask.routes import bp as api_bp
    from api_flask.views import bp as views_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    app.register_error_handler(AuthError, handle_auth_error)

    @app.get("/health")
    def health():
        """Kept for deployment health checks."""
        return {"status": "ok", "message": "API de Flask operando (Database-First)"}

    @app.context_processor
    def inject_auth():
        from api_flask.auth.tokens import verify_decode_jwt

        claims = None
        token = session.get("access_token")
        if token:
            try:
                claims = verify_decode_jwt(token)
            except AuthError:
                session.pop("access_token", None)

        def can(permission):
            return bool(claims and permission in claims.get("permissions", []))

        return {"claims": claims, "can": can}

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(
                {
                    "success": False,
                    "error": 404,
                    "code": "not_found",
                    "message": "Resource not found.",
                }
            ), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith("/api/"):
            return jsonify(
                {
                    "success": False,
                    "error": 403,
                    "code": "forbidden",
                    "message": "Forbidden.",
                }
            ), 403
        return render_template("errors/403.html", message="No tienes permiso."), 403

    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option(
        "--password", prompt=True, hide_input=True, confirmation_prompt=True
    )
    @click.option("--nombre", default="")
    @click.option(
        "--role",
        type=click.Choice(["cliente", "cocina", "admin"]),
        default="cliente",
        show_default=True,
    )
    def create_user_command(username, password, nombre, role):
        """Create a user (credentials in auth_user, profile in content.usuario)."""
        from api_flask.auth.service import RegistrationError, create_user

        try:
            auth_user, profile = create_user(
                username, password, nombre=nombre, role=role
            )
        except RegistrationError as err:
            raise click.ClickException(err.message)

        click.echo(
            f"Usuario {auth_user.username!r} creado con rol {profile.rol!r} "
            f"y sub {profile.sub!r}."
        )

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Create/repair the demo accounts using DEMO_PASSWORD."""
        from api_flask.auth.service import seed_demo_users

        password = os.environ.get("DEMO_PASSWORD", "")
        if not password:
            click.echo("DEMO_PASSWORD no está definida; se omiten los usuarios demo.")
            return

        for auth_user, profile in seed_demo_users(password):
            click.echo(
                f"Demo listo: {auth_user.username!r}, rol {profile.rol!r}, "
                f"sub {profile.sub!r}."
            )

    return app
