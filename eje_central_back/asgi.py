"""
ASGI config for eje_central_back project.

Solo lo usa el proceso dedicado a websockets (servicio plazas-ws, ver
gunicorn_ws.conf.py). El tráfico HTTP de producción (incluye SSE) sigue
100% en WSGI (eje_central_back/wsgi.py vía gunicorn.conf.py) — esta app
corre en un proceso/puerto separado, sin tocar ese camino.

A propósito la rama "http" de abajo NO es la app Django completa: algunas
vistas (ej. authentication/views.py: PermissionListView) hacen una query
síncrona a BD al definirse la clase (queryset=...), al importar el
urlconf — bajo ASGI eso truena con SynchronousOnlyOperation la primera
vez que algo intenta resolver una URL en este proceso (verificado: 500 en
cualquier GET). Como nginx nunca manda tráfico HTTP normal a este puerto
(solo /ws/*), evitamos el problema de raíz sin tocar esas vistas: el
branch "http" aquí es un stub que solo devuelve 404.
"""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eje_central_back.settings')
django.setup()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from eje_central_back.routing import websocket_urlpatterns  # noqa: E402


async def _http_not_available(scope, receive, send):
    await receive()
    await send({
        "type": "http.response.start",
        "status": 404,
        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
    })
    await send({
        "type": "http.response.body",
        "body": b"Este proceso solo sirve websockets (/ws/*). HTTP normal va por WSGI.",
    })


application = ProtocolTypeRouter({
    "http": _http_not_available,
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
