#!/bin/sh

# Detener el script inmediatamente si ocurre algún error
set -e

# 2. Bucle de espera activa para PostgreSQL (Sockets de red)[cite: 9]
echo "Esperando a que la base de datos PostgreSQL esté lista..."
while ! python -c "import socket; s = socket.socket(); s.connect(('db', 5432))" 2>/dev/null; do
  sleep 1
done
echo "¡Base de datos PostgreSQL disponible!"

# 3. Aplicar migraciones del sistema Django en orden estricto[cite: 9]
echo "Aplicando migraciones del sistema..."
python manage.py migrate auth
python manage.py migrate admin
python manage.py migrate contenttypes
python manage.py migrate sessions

echo "Marcando las migraciones de 'lacarta' como ya aplicadas (--fake)..."[cite: 9]
python manage.py migrate lacarta --fake

# 4. Creación y verificación de usuarios demo de prueba (Flask/WSGI)[cite: 9]
echo "Creando/verificando usuarios demo de prueba..."
flask --app wsgi seed-demo || echo "Aviso: no se pudieron crear los usuarios demo."

# 5. Recolección de archivos estáticos del admin y la aplicación[cite: 9]
echo "Recolectando estáticos en /app/staticfiles..."
python manage.py collectstatic --noinput

# 6. Verificación y creación automática del superusuario de Django[cite: 9]
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

echo "=== Entorno completamente preparado. Lanzando WSGI ==="

# 7. Lanzamiento del servidor WSGI (Gunicorn para producción o comando por defecto)
# Si prefieres usar Gunicorn directamente para la API Flask/WSGI:
exec gunicorn --bind 0.0.0.0:8000 --workers 3 wsgi:app

# (Nota: Si prefieres delegar el comando final enteramente desde tu docker-compose.yml, 
#  puedes reemplazar la línea anterior simplemente por: exec "$@")