from api_flask import create_app as create_flask_app
from config.wsgi import application as django_application
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# 1. Instanciar la aplicación de Flask (dueña de la aplicación web y la API)
flask_app = create_flask_app()

# 2. Configurar el Dispatcher Middleware
# - La aplicación principal en '/' es Flask.
# - La ruta '/admin' se delega a Django exclusivamente para el panel de administración.
application = DispatcherMiddleware(
    flask_app,
    {
        "/admin": django_application,
    },
)