"""Fixtures for the six mandatory tests.

The application models use PostgreSQL-specific UUID columns and the `content`
schema, so the tests run against a real PostgreSQL database:
`<DB_NAME>_test` on the same server as the development database. Django owns
the real schema; here `db.create_all()` is allowed because the exam says tests
may create the tables in an empty test database.
"""

import os
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from api_flask import create_app
from api_flask.auth.tokens import create_access_token
from api_flask.config import Config
from api_flask.extensions import db
from api_flask.models import ItemPedido, Pedido, Plato, Restaurante, Usuario

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if TEST_DATABASE_URL:
    test_url = make_url(TEST_DATABASE_URL)
else:
    base_url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    # On Windows "localhost" may resolve to a different PostgreSQL on ::1;
    # the container is published on 127.0.0.1.
    if base_url.host == "localhost":
        base_url = base_url.set(host="127.0.0.1")
    test_url = base_url.set(database=f"{base_url.database}_test")


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = test_url.render_as_string(hide_password=False)
    JWT_SECRET_KEY = "test-jwt-secret-with-at-least-32-bytes"
    JWT_EXPIRES_MINUTES = 5
    SESSION_COOKIE_SECURE = False


def _ensure_test_database():
    """CREATE DATABASE if it does not exist (Postgres needs AUTOCOMMIT)."""
    engine = create_engine(
        test_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": test_url.database},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def app():
    _ensure_test_database()
    application = create_app(TestConfig)
    with application.app_context():
        db.session.execute(text("CREATE SCHEMA IF NOT EXISTS content"))
        db.session.commit()
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()
        db.session.execute(text("DROP SCHEMA IF EXISTS content CASCADE"))
        db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed(app):
    """Clean tables and create two restaurants, three plates and three users."""
    with app.app_context():
        db.session.execute(
            text(
                "TRUNCATE TABLE content.item_pedido, content.pedido, "
                "content.plato, content.restaurante, content.usuario, "
                "public.auth_user RESTART IDENTITY CASCADE"
            )
        )
        db.session.commit()

        r1 = Restaurante(nombre="Restaurante Uno", direccion="Calle 1")
        r2 = Restaurante(nombre="Restaurante Dos", direccion="Calle 2")
        db.session.add_all([r1, r2])
        db.session.flush()

        disponible = Plato(
            restaurante_id=r1.id,
            nombre="Plato disponible",
            precio=Decimal("10.00"),
            disponible=True,
        )
        no_disponible = Plato(
            restaurante_id=r1.id,
            nombre="Plato agotado",
            precio=Decimal("5.00"),
            disponible=False,
        )
        de_otro = Plato(
            restaurante_id=r2.id,
            nombre="Plato de otro restaurante",
            precio=Decimal("7.00"),
            disponible=True,
        )
        cliente_1 = Usuario(
            nombre="Cliente Uno",
            apellido_paterno="Prueba",
            apellido_materno="",
            email="cliente1@test.invalid",
            contrasena="!",
            rol="cliente",
            sub="auth0|test-cliente-1",
        )
        cliente_2 = Usuario(
            nombre="Cliente Dos",
            apellido_paterno="Prueba",
            apellido_materno="",
            email="cliente2@test.invalid",
            contrasena="!",
            rol="cliente",
            sub="auth0|test-cliente-2",
        )
        cocina = Usuario(
            nombre="Cocina",
            apellido_paterno="Prueba",
            apellido_materno="",
            email="cocina@test.invalid",
            contrasena="!",
            rol="cocina",
            sub="auth0|test-cocina",
        )
        db.session.add_all([disponible, no_disponible, de_otro,
                            cliente_1, cliente_2, cocina])
        db.session.commit()

        return SimpleNamespace(
            restaurante_1=str(r1.id),
            restaurante_2=str(r2.id),
            plato_ok=str(disponible.id),
            plato_agotado=str(no_disponible.id),
            plato_otro=str(de_otro.id),
            cliente_1="auth0|test-cliente-1",
            cliente_2="auth0|test-cliente-2",
            cocina="auth0|test-cocina",
        )


@pytest.fixture
def login(client, app):
    """Write a real signed JWT in the Flask session, like a browser would."""

    def _login(sub, permissions, role="cliente", username="tester"):
        with app.app_context():
            token = create_access_token(sub, username, role, permissions)
        with client.session_transaction() as flask_session:
            flask_session["access_token"] = token

    return _login


@pytest.fixture
def pedido_factory(app, seed):
    """Create a persisted order (and one item) and return its UUID string."""

    def _create(usuario_sub, estado="pendiente", cantidad=1):
        with app.app_context():
            profile = Usuario.query.filter_by(sub=usuario_sub).one()
            plate = db.session.get(Plato, uuid.UUID(seed.plato_ok))
            pedido = Pedido(
                usuario_id=profile.id,
                restaurante_id=plate.restaurante_id,
                estado=estado,
                total=plate.precio * cantidad,
            )
            db.session.add(pedido)
            db.session.flush()
            db.session.add(
                ItemPedido(
                    pedido_id=pedido.id,
                    plato_id=plate.id,
                    cantidad=cantidad,
                    precio_unitario=plate.precio,
                )
            )
            db.session.commit()
            return str(pedido.id)

    return _create
