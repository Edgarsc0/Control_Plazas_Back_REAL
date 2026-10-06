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

ENDPOINTS = [
    "/api/plantilla/conteo_plazas_historico_serie/",
    "/api/plantilla/empleados_completos_estatus_resumen/",
    "/api/plantilla/mov_pos_alineacion/",
    "/api/plantilla/bajas_sig/historico/",
    "/api/plantilla/desglose_jerarquico_ocupados/",
    "/api/plantilla/bajas_sig/",
]

user = get_user_model().objects.filter(is_superuser=True, is_active=True).first()
client = APIClient(SERVER_NAME="localhost")
client.force_authenticate(user)
for url in ENDPOINTS:
    t = time.time()
    code = client.get(url).status_code
    print(f"{code} {time.time() - t:.1f}s {url}")
