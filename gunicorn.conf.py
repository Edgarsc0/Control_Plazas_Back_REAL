# Configuración de gunicorn para producción (Docker).
bind = "0.0.0.0:8000"
# gthread: los endpoints SSE son generadores síncronos que ocupan un hilo
# mientras la conexión está abierta; muchos hilos por worker evitan que
# unas pocas pestañas abiertas agoten la capacidad para peticiones normales.
worker_class = "gthread"
workers = 4
threads = 32
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 2000
max_requests_jitter = 200
accesslog = "-"

# Importar vistas/URLs (pandas, genai, ...) toma ~4s: se hace una sola vez en
# el maestro y los workers lo heredan al hacer fork, en lugar de pagarlo en
# la primera petición de cada worker (y tras cada reciclaje por max_requests).
preload_app = True


def on_starting(server):
    import django

    django.setup()
    from django.urls import get_resolver

    get_resolver().url_patterns


def post_fork(server, worker):
    # Ninguna conexión abierta en el maestro debe compartirse entre workers.
    from django.db import connections

    connections.close_all()
