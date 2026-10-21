from flask import Flask
from api_flask.config import Config
from api_flask.extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar la base de datos
    db.init_app(app)

    # Importar los modelos para registrarlos en el contexto
    from api_flask import models  # noqa: F401

    # Registrar el Blueprint de rutas
    from api_flask.routes import bp as api_bp
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return {"status": "ok", "message": "API de Flask operando (Database-First)"}

    return app