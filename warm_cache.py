"""
Precalienta la caché de Redis justo después de flush_cache.sh, para que el
primer usuario tras la limpieza no espere el recálculo (hasta ~18s en
conteo_plazas_historico_serie). Solo hace GET en proceso, sin red ni sesión.
"""
import time

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

# Todo lo que piden los tabs de Plantilla de Empleados y el tablero al abrirse.
# Primero los datasets base (otros endpoints se derivan de ellos).
ENDPOINTS = [
    "/api/plantilla/empleados_completos_activos_detalle/",
    "/api/plantilla/empleados_completos_estatus_resumen/",
    "/api/plantilla/empleados_estatus_por_nivel_ua/",
    "/api/plantilla/empleados_distribucion_geografica/",
    "/api/plantilla/mov_pos_detalle/?is_latest=true",
    "/api/plantilla/mov_pos_alineacion/",
    "/api/plantilla/cuadro_vacancia/",
    "/api/plantilla/desglose_jerarquico/",
    "/api/plantilla/desglose_jerarquico_ocupados/",
    "/api/plantilla/conteo_plazas_historico_serie/",
    "/api/plantilla/aduanas_ocupacion_vacancia/",
    "/api/plantilla/movimientos-personal/",
    "/api/plantilla/movimientos-personal/stats/",
    "/api/plantilla/bajas_sig/",
    "/api/plantilla/bajas_sig/historico/",
    "/api/plantilla/bajas_sig/motivos/",
    "/api/plantilla/torre-caballito/",
    "/api/plantilla/rotacion-titulares-aduanas/",
    "/api/plantilla/organigrama-deptos/",
    "/api/plantilla/cat-acciones/",
    "/api/plantilla/cat-acciones-motivos/",
]

user = get_user_model().objects.filter(is_superuser=True, is_active=True).first()
# gzip: los caminos cacheados guardan la respuesta ya comprimida.
client = APIClient(SERVER_NAME="localhost", HTTP_ACCEPT_ENCODING="gzip")
client.force_authenticate(user)
for url in ENDPOINTS:
    t = time.time()
    try:
        resp = client.get(url)
        cuerpo = resp.content if hasattr(resp, "content") else b"".join(resp.streaming_content)
        print(f"{resp.status_code} {time.time() - t:.1f}s {len(cuerpo) // 1024}KB {url}")
    except Exception as exc:  # un endpoint roto no debe frenar el resto
        print(f"ERR {time.time() - t:.1f}s {url} {exc!r}")
