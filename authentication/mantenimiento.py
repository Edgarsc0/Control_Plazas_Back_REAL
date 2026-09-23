"""Estado del modo mantenimiento, cacheado para no pegarle a la BD en cada request."""

import logging

from django.core.cache import cache
from django.db import DatabaseError

logger = logging.getLogger(__name__)

CACHE_KEY = "mantenimiento:estado"
CACHE_TTL = 60 * 60
MENSAJE_DEFAULT = "Estamos arreglando cositas. Volvemos muy pronto."


def obtener_estado():
    """{"activo": bool, "mensaje": str, "exentos_user_ids": [int]}"""
    estado = cache.get(CACHE_KEY)
    if estado is not None:
        return estado

    from .models import ModoMantenimiento

    try:
        config = ModoMantenimiento.objects.filter(pk=1).first()
        exentos = (
            list(config.exentos.exclude(user__isnull=True).values_list("user_id", flat=True))
            if config
            else []
        )
    except DatabaseError:
        # Migración sin aplicar o BD caída: fallar abierto (sin mantenimiento)
        # en vez de tumbar toda la API, y sin cachear para reintentar.
        logger.exception("No se pudo leer ModoMantenimiento; se asume apagado.")
        return {"activo": False, "mensaje": MENSAJE_DEFAULT, "exentos_user_ids": []}
    if config is None:
        estado = {"activo": False, "mensaje": MENSAJE_DEFAULT, "exentos_user_ids": []}
    else:
        estado = {
            "activo": config.activo,
            "mensaje": config.mensaje or MENSAJE_DEFAULT,
            "exentos_user_ids": exentos,
        }
    cache.set(CACHE_KEY, estado, CACHE_TTL)
    return estado


def invalidar_cache():
    cache.delete(CACHE_KEY)


def usuario_bloqueado(user, estado=None):
    """True si el modo mantenimiento está activo y `user` (persona de la whitelist) no está exento."""
    estado = estado or obtener_estado()
    if not estado["activo"]:
        return False
    if not user or not user.is_authenticated:
        return False
    if user.id in estado["exentos_user_ids"]:
        return False
    # Cuentas de servicio (p. ej. zafiro-worker-windows, rendicion-cuentas-worker)
    # no tienen fila en Whitelist: no son personas, así que nunca se bloquean
    # (y no habría forma de marcarlas como exentas desde la UI).
    return getattr(user, "perfil", None) is not None
