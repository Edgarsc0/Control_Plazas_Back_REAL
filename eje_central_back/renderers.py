"""Renderer JSON basado en orjson (mucho más rápido que el JSON de la stdlib).

Se usa como renderer por defecto de DRF para acelerar la serialización de TODAS
las respuestas, en especial las listas grandes (p. ej. la plantilla de ~12k filas).
"""

from decimal import Decimal

import orjson
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer

_ORJSON_OPTS = orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY


def _default(obj):
    # orjson serializa nativamente datetime/date/time/UUID. Decimal no: lo
    # convertimos a str para mantener el formato actual de DRF
    # (COERCE_DECIMAL_TO_STRING=True por defecto).
    if isinstance(obj, Decimal):
        return str(obj)
    # Fallback seguro (el renderer es global): convertir a str cualquier tipo
    # no soportado en vez de lanzar 500.
    return str(obj)


class ORJSONRenderer(JSONRenderer):
    """Renderer de DRF que serializa con orjson."""

    media_type = "application/json"
    format = "json"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        return orjson.dumps(data, default=_default, option=_ORJSON_OPTS)


def orjson_dumps(data):
    """Serializa a bytes JSON con orjson (Decimal -> str)."""
    return orjson.dumps(data, default=_default, option=_ORJSON_OPTS)


def orjson_response(data, status=200):
    """Construye un HttpResponse JSON usando orjson, evitando el overhead de DRF.

    Útil para endpoints de listas grandes y para servir payloads ya cacheados
    (bytes) sin re-serializar.
    """
    payload = data if isinstance(data, (bytes, bytearray)) else orjson_dumps(data)
    return HttpResponse(payload, status=status, content_type="application/json")
