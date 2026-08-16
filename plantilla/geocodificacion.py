"""
Geolocalización (columnas `latitud`/`longitud`) de empleados activos con
`Descripción ubicación` pero sin coordenadas — típicamente personal
administrativo (no aduanero), cuyo `Aduana` no trae una dirección
geolocalizable de origen en el CSV de ZAFIRO.

Por qué vive aquí y no en tasks.py: `importar_zafiro` puede correr en una
máquina aparte del servidor que sirve a los usuarios (ver `copia_back`, PC
Windows dedicada a Celery — mismo motivo que `cache_invalidation.py` y
`notificaciones_posicion.py`). Si esta lógica viviera en tasks.py, solo
tendría efecto cuando esa PC Windows tenga el código desplegado — algo que
el flujo de deploy de este repo (ver DEPLOY.md) no cubre, así que quedaría
silenciosamente desactualizada. En cambio, se dispara desde
`InvalidarCacheZafiroView.post` (plantilla/views.py), que SIEMPRE corre en
este servidor (89.116.51.124) justo cuando Celery avisa que el import ya
terminó — garantizando que el código que se ejecuta es el que está
realmente desplegado aquí.
"""

import logging
import time

import requests
from django.db import connection

from .models import EmpleadosCompletosSig, GeocodeCache

logger = logging.getLogger(__name__)


def _append_log(bitacora, mensaje, is_error=False):
    if is_error:
        logger.error(mensaje)
    else:
        logger.info(mensaje)

    if not bitacora:
        return

    from django.utils import timezone

    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[ERROR]" if is_error else "[INFO]"
    linea = f"{timestamp} {prefix} {mensaje}\n"

    if bitacora.logs_en_vivo is None:
        bitacora.logs_en_vivo = linea
    else:
        bitacora.logs_en_vivo += linea
    bitacora.save(update_fields=["logs_en_vivo"])


def _clean_address(addr):
    if not addr:
        return ""
    addr = addr.strip()
    if "Torre Caballito" in addr or "Caballito Reforma 10" in addr:
        return "Paseo de la Reforma 10, Tabacalera, Cuauhtémoc, Ciudad de México, 06030, México"
    if "L.  Alamán" in addr or "L. Alamán" in addr or "Lucas Alaman" in addr:
        return "Calle Lucas Alamán 111, Obrera, Cuauhtémoc, Ciudad de México, 06800, México"
    if "Laboratorio Central" in addr:
        return "San Lorenzo 252, Miguel Hidalgo, Ciudad de México"
    if "Chichimequilla" in addr:
        return "Chichimequillas, El Marqués, Querétaro, México"
    if "Tlalpan" in addr:
        return "Tlalpan, Ciudad de México, México"
    return addr


# Direcciones cuyo texto crudo Nominatim no puede resolver (abreviaturas
# tipo "Ad Guaymas Recinto Portu E1 P1"), pero que corresponden a una aduana
# que YA tiene coordenadas (vienen directo del CSV de ZAFIRO para el
# personal aduanero, ver EMPLEADOS_COMPLETOS_SIG.Aduana) — se reusan esas
# coords en vez de pegarle a Nominatim con un texto que sabemos que falla.
_COORDS_CONOCIDAS = {
    "Guaymas": ("27.91396", "-110.90208"),  # Aduana de Guaymas con sede en Sonora
}


def _coords_conocidas(addr_cruda):
    for clave, coords in _COORDS_CONOCIDAS.items():
        if clave in addr_cruda:
            return coords
    return None


def _geocode_external(address):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "ANAMEjeCentralGeocoding/1.0 (edgar@anam.gob.mx)"},
            timeout=5,
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logger.warning("Error llamando a Nominatim para '%s': %s", address, e)
    return None, None


def geocodificar_empleados_sin_coordenadas(bitacora=None):
    """
    Geolocaliza a los empleados con posición activa que tienen `Descripción
    ubicación` pero llegaron sin coordenadas.

    Usa Nominatim (OpenStreetMap) como geocodificador, pero solo para
    direcciones genuinamente nuevas: el caché real vive en la tabla-hash
    `GeocodeCache` (dirección normalizada -> lat/lng), no en un escaneo de
    EMPLEADOS_COMPLETOS_SIG completa en cada corrida — esa tabla tiene
    decenas de miles de filas, mientras que direcciones únicas hay unas
    pocas decenas, así que precargar el hash es prácticamente instantáneo.
    Los empleados pendientes se actualizan con un solo `bulk_update`. Nunca
    lanza excepción: un fallo aquí (ej. Nominatim caído) no debe tumbar el
    resto de `InvalidarCacheZafiroView.post`.
    """
    t0 = time.time()
    _append_log(
        bitacora,
        "Geolocalizando empleados activos sin coordenadas (Nominatim, por Descripción ubicación)...",
    )

    try:
        known_coords = {
            c.direccion: (c.latitud, c.longitud) for c in GeocodeCache.objects.all()
        }

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.`Descripción ubicación`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN MOV_POS_LATEST activas
                    ON e.`Posición` = activas.`Nº Pos Actual` AND activas.`Estado Psn` = 'A'
                WHERE (TRIM(IFNULL(e.latitud, '')) = '' OR TRIM(IFNULL(e.longitud, '')) = '')
                  AND TRIM(IFNULL(e.`Descripción ubicación`, '')) <> ''
            """)
            pendientes = cursor.fetchall()  # [(id, descripcion_ubicacion), ...]

        if not pendientes:
            _append_log(
                bitacora,
                f"Geolocalización: sin pendientes, todos los activos ya tienen coordenadas "
                f"({len(known_coords)} dirección(es) en el hash). ({time.time() - t0:.1f}s)",
            )
            return

        actualizados = 0
        llamadas_api = 0
        fallidos = 0
        nuevas_direcciones = {}  # direccion -> (lat, lng), para bulk_create al final
        updates = []  # instancias EmpleadosCompletosSig(id=..., latitud=..., longitud=...)

        for emp_id, desc in pendientes:
            clean = _clean_address(desc)

            override = _coords_conocidas(desc)
            if override:
                # Prioridad sobre el caché: si `clean` quedó guardado en
                # GeocodeCache como caché negativo (""/"") de una corrida
                # anterior en la que esta dirección aún no tenía override,
                # ese registro nunca se actualiza solo (bulk_create de abajo
                # usa ignore_conflicts=True) — así que el override manual
                # siempre gana, sin importar qué haya en el hash.
                lat_str, lng_str = override
                known_coords[clean] = (lat_str, lng_str)
                nuevas_direcciones[clean] = (lat_str, lng_str)
                lat, lng = lat_str, lng_str
                GeocodeCache.objects.update_or_create(
                    direccion=clean, defaults={"latitud": lat_str, "longitud": lng_str}
                )
            elif clean in known_coords:
                # Caché negativo: ("", "") = Nominatim ya no pudo resolver
                # esta dirección antes, no reintentar cada corrida.
                lat, lng = known_coords[clean]
                lat, lng = (lat or None), (lng or None)
            else:
                lat, lng = _geocode_external(clean)
                llamadas_api += 1
                if lat is not None and lng is not None:
                    lat_str = str(round(float(lat), 6))[:12]
                    lng_str = str(round(float(lng), 6))[:13]
                else:
                    lat_str = lng_str = ""
                known_coords[clean] = (lat_str, lng_str)
                nuevas_direcciones[clean] = (lat_str, lng_str)
                lat, lng = (lat_str or None), (lng_str or None)
                time.sleep(1.2)  # respeta el límite de 1 req/s de Nominatim

            if lat is not None and lng is not None:
                updates.append(
                    EmpleadosCompletosSig(id=emp_id, latitud=str(lat)[:12], longitud=str(lng)[:13])
                )
                actualizados += 1
            else:
                fallidos += 1

        if updates:
            EmpleadosCompletosSig.objects.bulk_update(
                updates, ["latitud", "longitud"], batch_size=500
            )

        if nuevas_direcciones:
            GeocodeCache.objects.bulk_create(
                [
                    GeocodeCache(direccion=d, latitud=lat, longitud=lng)
                    for d, (lat, lng) in nuevas_direcciones.items()
                ],
                ignore_conflicts=True,
            )

        _append_log(
            bitacora,
            f"Geolocalización completada: {actualizados} actualizado(s), "
            f"{fallidos} sin resolver, {llamadas_api} llamada(s) a Nominatim nuevas "
            f"({len(nuevas_direcciones)} dirección(es) agregada(s) al hash). "
            f"({time.time() - t0:.1f}s)",
        )
    except Exception as e:
        _append_log(bitacora, f"Error geolocalizando empleados: {str(e)}", is_error=True)
        logger.error("Error en geocodificar_empleados_sin_coordenadas: %s", e, exc_info=True)
