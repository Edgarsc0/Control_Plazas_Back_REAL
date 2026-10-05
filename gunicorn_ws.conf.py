# Configuración de gunicorn para el proceso de websockets (servicio
# plazas-ws, Docker). SEPARADO a propósito de gunicorn.conf.py (WSGI,
# puerto 8000, el que sirve TODO el tráfico HTTP/SSE de producción) para
# no tocar ese proceso ya probado: este solo atiende /ws/*.
bind = "0.0.0.0:8001"
# uvicorn worker: único worker_class que entiende el protocolo websocket
# bajo gunicorn+Channels. Sin usuarios reales todavía (ver routing.py),
# así que 2 workers de sobra; subir si en el futuro algún feature lo usa.
worker_class = "uvicorn.workers.UvicornWorker"
workers = 2
# Las conexiones WS son de larga duración por diseño: el timeout corto de
# gunicorn.conf.py (pensado para requests HTTP/SSE normales) mataría
# workers con conexiones abiertas sin tráfico. Generoso a propósito.
timeout = 3600
graceful_timeout = 30
keepalive = 5
accesslog = "-"

# Mismo truco que gunicorn.conf.py: importar vistas/URLs una sola vez en
# el maestro (asgi.py ya corre get_asgi_application() al importarse).
preload_app = True


def post_fork(server, worker):
    # Ninguna conexión abierta en el maestro debe compartirse entre workers.
    from django.db import connections

    connections.close_all()
