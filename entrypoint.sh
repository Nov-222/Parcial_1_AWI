#!/bin/sh

echo "Esperando a que la base de datos PostgreSQL esté lista..."

# Bucle de reintentos seguros mediante sockets de red
while ! python -c "import socket; s = socket.socket(); s.connect(('db', 5432))" 2>/dev/null; do
  sleep 1
done

echo "¡Base de datos disponible! Aplicando migraciones del sistema..."
python manage.py migrate auth
python manage.py migrate admin
python manage.py migrate contenttypes
python manage.py migrate sessions

echo "Marcando las migraciones de 'lacarta' como ya aplicadas (--fake)..."
python manage.py migrate lacarta --fake

echo "Creando/verificando usuarios demo de prueba..."
flask --app wsgi seed-demo || echo "Aviso: no se pudieron crear los usuarios demo."

echo "Recolectando estáticos del admin en /app/staticfiles..."
python manage.py collectstatic --noinput

echo "Verificando/Creando superusuario de Django automáticamente..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin123")
    print("¡Superusuario 'admin' creado exitosamente!")
else:
    print("El superusuario 'admin' ya existe.")
END

echo "Iniciando servidor Django..."
exec python manage.py runserver 0.0.0.0:8000