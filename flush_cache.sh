#!/usr/bin/env bash
# Red de seguridad para datos frescos: borra la caché de Django en Redis cada
# 30 min aunque no llegue el aviso de la PC que corre importar_zafiro
# (InvalidarCacheZafiroView). No toca las keys de Celery ni notifica a los
# suscriptores externos (eso solo lo hace el flujo normal post-ZAFIRO).
docker exec plazas_api python manage.py shell -c '
import redis
from django.conf import settings
from django.core.cache import cache
r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
n = 0
for k in r.scan_iter(match=f"{cache.key_prefix}:{cache.version}:*", count=500):
    r.delete(k); n += 1
print(n)' 2>&1 | sed "s/^/$(date "+%F %T") cache keys borradas: /" >> /srv/controlPlazas/Control_Plazas_Back_REAL/logs/cache_flush.log
docker exec -e PYTHONPATH=/app plazas_api python /app/warm_cache.py 2>/dev/null | sed "s/^/$(date "+%F %T") warm: /" >> /srv/controlPlazas/Control_Plazas_Back_REAL/logs/cache_flush.log
