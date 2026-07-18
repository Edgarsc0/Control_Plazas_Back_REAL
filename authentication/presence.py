"""
Presencia de usuarios en tiempo real: quién está activo y en qué página.

Vive solo en Redis (mismo broker que Celery, ver settings.CELERY_BROKER_URL),
no en BD: es un dato efímero que debe autoexpirar solo si el heartbeat del
front deja de llegar (pestaña cerrada, red caída, crash del navegador) sin
necesitar ningún evento explícito de "logout" o desconexión.
"""

import json
from datetime import datetime, timezone

from django.conf import settings

PRESENCE_TTL_SECONDS = 45
PRESENCE_KEY_PREFIX = "presence"


def _redis_client():
    import redis as redis_lib

    return redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)


def _presence_key(email, tab_id):
    return f"{PRESENCE_KEY_PREFIX}:{email}:{tab_id}"


def set_presence(*, email, tab_id, rol, ua, path, title, subtab):
    """Registra/renueva la presencia de una pestaña puntual de un usuario."""
    r = _redis_client()
    payload = {
        "email": email,
        "rol": rol,
        "ua": ua,
        "path": path,
        "title": title,
        "subtab": subtab,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    r.set(_presence_key(email, tab_id), json.dumps(payload), ex=PRESENCE_TTL_SECONDS)


def get_active_sessions():
    """Sesiones activas agrupadas por email (una entrada por pestaña/dispositivo)."""
    r = _redis_client()
    sessions_by_email = {}

    for key in r.scan_iter(match=f"{PRESENCE_KEY_PREFIX}:*"):
        raw = r.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            continue

        email = data.get("email")
        if not email:
            continue

        entry = sessions_by_email.setdefault(
            email,
            {"email": email, "rol": data.get("rol"), "ua": data.get("ua"), "sessions": []},
        )
        entry["sessions"].append(
            {
                "path": data.get("path"),
                "title": data.get("title"),
                "subtab": data.get("subtab"),
                "ts": data.get("ts"),
            }
        )

    for entry in sessions_by_email.values():
        entry["sessions"].sort(key=lambda s: s["ts"] or "", reverse=True)

    return sorted(sessions_by_email.values(), key=lambda entry: entry["email"])
