"""
rotacion_plazas.py
==================
Endpoints del subtab "Rotación de plazas" (MovimientosPersonalTab).

La vista se lee en dos niveles:

  ENTRADA   una fila por plaza con sus métricas de rotación — cuántas gestiones
            ha consumido, cuánto duran, qué tanto tiempo pasa vacante. Es donde
            el usuario ordena y filtra para decidir QUÉ plazas mirar.
  PRINCIPAL un swimlane: eje X el tiempo real, una fila por plaza, una barra por
            ocupante y los huecos como vacancia. Ahí la rotación se lee sin leer:
            fila fragmentada = rota, barra larga = estable.

Y de cualquier plaza se puede saltar al árbol de movimientos, que sigue siendo
la herramienta de detalle para UNA cadena a fondo.

De dónde salen los datos
------------------------
De dos tablas materializadas por `sp_rotacion_plazas` (ver
plantilla/sql/sp_rotacion_plazas.sql), que reconstruye la historia de las 13,254
plazas de una sola pasada en ~21s:

    rotacion_plaza_metrica   una fila por plaza  -> vista de ENTRADA
    rotacion_plaza_periodo   la pila cronológica -> vista PRINCIPAL

NO se llama a sp_historia_plaza aquí. Ese SP resuelve UNA plaza (~30ms); pedirle
las 13,254 son ~6 minutos por request, y ambas vistas necesitan el universo
completo para ordenar y filtrar. El cálculo corre una vez por carga del ETL
(`python manage.py reconstruir_rotacion_plazas`) y estos endpoints quedan como
SELECT planos.

La equivalencia entre el SP por plaza y el materializado está validada fila por
fila en 200 plazas (1,068 filas, 0 diferencias) — ver la cabecera del .sql.
"""

from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Mismo par de permisos que HistoriaPlazaView: es la misma información de
# movimientos de posición, presentada de otra forma.
_PERMISOS = (
    "authentication.view_plantilla_mov_posiciones",
    "authentication.view_plantilla_movimientos",
)

# El cálculo pesado ya está materializado; este caché sólo evita re-serializar
# 13k filas en cada entrada al tab. Se invalida solo al reconstruir (el comando
# borra la llave) y, por si acaso, a las 6 horas.
_CACHE_METRICAS = "rotacion_plazas_metricas_v1"
_CACHE_TTL = 6 * 60 * 60

# Tope de plazas por petición de periodos: el swimlane no puede dibujar más
# filas de las que un humano puede comparar de un vistazo, y sin tope una
# selección accidental de "todas" traería ~50k periodos.
MAX_PLAZAS_SWIMLANE = 300


def _filas(cursor):
    columnas = [c[0] for c in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def _leer_meta(cursor):
    """Sello de la última reconstrucción, para que la UI pueda decir 'datos al X'."""
    cursor.execute(
        "SELECT calculado_en, segundos, num_plazas, num_periodos, fuente "
        "FROM rotacion_plaza_meta WHERE id = 1"
    )
    filas = _filas(cursor)
    return filas[0] if filas else None


class RotacionPlazasMetricasView(APIView):
    """Una fila por plaza con sus métricas de rotación (vista de ENTRADA).

    Devuelve el universo completo (13,254 filas) en una sola respuesta, igual que
    los demás tabs de plantilla: así el ordenamiento, los Filtros Avanzados y el
    ColumnFilterDropdown del front operan en cliente sin ida y vuelta por cada
    interacción. La carga es de ~4 MB y se sirve del caché.

    GET /plantilla/rotacion-plazas/metricas/
        ?refrescar=1   omite el caché de la respuesta (NO recalcula la tabla:
                       para eso está el comando reconstruir_rotacion_plazas)
    """

    view_permission = _PERMISOS

    def get(self, request, *args, **kwargs):
        if request.query_params.get("refrescar") != "1":
            en_cache = cache.get(_CACHE_METRICAS)
            if en_cache is not None:
                return Response(en_cache, status=status.HTTP_200_OK)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT posicion,
                       ocupada, num_empleado_actual, nombre_actual, dias_en_estado_actual,
                       fecha_creacion, fecha_primer_movimiento, fecha_ultimo_movimiento,
                       dias_desde_creacion,
                       num_gestiones, num_ocupantes_distintos, num_insubsistencias,
                       num_transitos, num_vacancias, num_salidas_traslado, num_salidas_baja,
                       num_periodos_inconsistentes,
                       dias_ocupada, dias_vacante, pct_vacante,
                       gestion_dias_min, gestion_dias_max, gestion_dias_prom,
                       gestion_dias_mediana, gestiones_por_anio,
                       aduana, unidad_administrativa, puesto, nivel, ubicacion,
                       entidad_federativa, nj, tipo_contratacion,
                       personal_militar_civil, rango
                FROM rotacion_plaza_metrica
                ORDER BY posicion
                """
            )
            plazas = _filas(cursor)
            meta = _leer_meta(cursor)

        if not plazas:
            return Response(
                {
                    "detail": (
                        "La tabla de rotación está vacía. Ejecuta "
                        "`python manage.py reconstruir_rotacion_plazas`."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        datos = {"meta": meta, "plazas": plazas}
        cache.set(_CACHE_METRICAS, datos, timeout=_CACHE_TTL)
        return Response(datos, status=status.HTTP_200_OK)


class RotacionPlazasPeriodosView(APIView):
    """Pila cronológica de las plazas indicadas (vista PRINCIPAL, el swimlane).

    Devuelve exactamente lo que devolvería sp_historia_plaza para cada una, más
    `posicion`. El front no re-deriva nada: cada periodo ya viene clasificado
    (creacion / vacancia / ocupacion / insubsistencia / transito) con sus fechas,
    y el swimlane sólo convierte fechas a píxeles.

    POST /plantilla/rotacion-plazas/periodos/   body {"posicion": ["10300009", ...]}
    GET  /plantilla/rotacion-plazas/periodos/?posicion__in=10300009,10300010

    Se usa POST para listas grandes: 300 posiciones no caben en una URL.
    """

    view_permission = _PERMISOS

    def get(self, request, *args, **kwargs):
        crudo = request.query_params.get("posicion__in", "")
        return self._periodos([p.strip() for p in crudo.split(",") if p.strip()])

    def post(self, request, *args, **kwargs):
        posiciones = request.data.get("posicion", [])
        if isinstance(posiciones, str):
            posiciones = [p.strip() for p in posiciones.split(",") if p.strip()]
        else:
            posiciones = [str(p).strip() for p in posiciones if str(p).strip()]
        return self._periodos(posiciones)

    def _periodos(self, posiciones):
        if not posiciones:
            return Response({"periodos": [], "posiciones": []}, status=status.HTTP_200_OK)

        # dict.fromkeys y no set(): conserva el orden en que el usuario las
        # seleccionó, que es el orden de los carriles del swimlane.
        posiciones = list(dict.fromkeys(posiciones))
        if len(posiciones) > MAX_PLAZAS_SWIMLANE:
            return Response(
                {
                    "detail": (
                        f"Máximo {MAX_PLAZAS_SWIMLANE} plazas por consulta; "
                        f"se pidieron {len(posiciones)}. Filtra más en la tabla."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        marcadores = ", ".join(["%s"] * len(posiciones))
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT posicion, orden, tipo_periodo, num_gestion, num_empleado,
                       nombre_completo, fecha_inicio, fecha_fin, dias,
                       id_registro_inicio, fuente_id_inicio, id_registro_fin,
                       accion_entrada, motivo_entrada, accion_salida, motivo_salida,
                       tipo_cierre, posicion_destino, es_ocupante_actual, inconsistente,
                       nivel_entrada, nivel_salida
                FROM rotacion_plaza_periodo
                WHERE posicion IN ({marcadores})
                ORDER BY posicion, orden
                """,
                posiciones,
            )
            periodos = _filas(cursor)
            meta = _leer_meta(cursor)

        return Response(
            {"meta": meta, "posiciones": posiciones, "periodos": periodos},
            status=status.HTTP_200_OK,
        )
