"""
Invalidación total de la caché del servidor, para cuando `importar_zafiro`
corre en una máquina aparte (ver `InvalidarCacheZafiroView` en views.py).

El worker de Celery que corre `importar_zafiro` en la PC Windows (repo
`copia_back`) invalida su propia caché local al terminar, pero esa caché
vive en el Redis de esa PC, no en el de este servidor — el que realmente
sirve a los usuarios. Ese Redis del servidor nunca se entera de que hay
datos nuevos hasta que expira el TTL de cada cache key (hasta 20 min).

Este módulo borra TODA la caché de Django del servidor bajo pedido, para
que el siguiente request de cualquier usuario recalcule con datos frescos.
"""

import logging

import redis as redis_lib
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def invalidar_todo_el_cache_servidor():
    """
    Borra todas las keys de caché de Django en Redis, sin tocar las keys de
    broker/result-backend de Celery que viven en la misma DB de Redis
    (`CACHES.LOCATION` reutiliza `CELERY_BROKER_URL`).

    Es seguro porque Django prefija cada key de caché con
    "{KEY_PREFIX}:{VERSION}:" (ver `django.core.cache.backends.base
    .BaseCache.__init__` y `default_key_func`) — un patrón que Celery/kombu
    nunca usa para sus propias keys (colas, `_kombu.binding.*`, unacked,
    `celery-task-meta-*`), así que un `cache.clear()` normal (que internamente
    hace `FLUSHDB` sobre TODA la DB) sería demasiado agresivo aquí.
    """
    r = redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)
    pattern = f"{cache.key_prefix}:{cache.version}:*"
    borradas = 0
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match=pattern, count=500)
        if keys:
            r.delete(*keys)
            borradas += len(keys)
        if cursor == 0:
            break
    logger.info("invalidar_todo_el_cache_servidor: %d keys borradas (patrón %s)", borradas, pattern)
    return borradas
