import multiprocessing
import os

# Dirección y puerto de escucha interno
bind = os.environ.get("GUNICORN_BIND")

# Número de workers basado en los núcleos de CPU disponibles (2 * CPUs + 1)
workers = int(os.environ.get("GUNICORN_WORKERS"))
worker_class = "sync"
threads = int(os.environ.get("GUNICORN_THREADS"))

# Tiempos de espera y estabilidad
timeout = int(os.environ.get("GUNICORN_TIMEOUT"))
graceful_timeout = 30
keepalive = 5

# Mitigación de fugas de memoria reciclando workers cada 1000 peticiones + aleatoriedad (jitter)
max_requests = 1000
max_requests_jitter = 100

# Registro de accesos y errores directamente a la salida estándar del contenedor (stdout/stderr)
accesslog = "-"
errorlog = "-"

# Confiar en las cabeceras de proxy de Nginx (X-Forwarded-*)
forwarded_allow_ips = "*"

wsgi_app = "wsgi:application"