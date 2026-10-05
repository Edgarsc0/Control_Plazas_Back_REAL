"""
Rutas de websocket. Vacío de propósito salvo /ws/health/ (ver
consumers.py): la infraestructura (ASGI, Channels, canal Redis, nginx)
ya soporta websockets, pero ningún feature de producto la usa todavía.
"""

from django.urls import path

from eje_central_back.consumers import HealthConsumer

websocket_urlpatterns = [
    path("ws/health/", HealthConsumer.as_asgi()),
]
