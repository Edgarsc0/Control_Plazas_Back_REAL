from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ValuacionPresupuestariaPorNivel, CatalogoPlazas, ConceptosPresupuestal, ConstantesSistema
from .serializers import (
    ValuacionPresupuestariaPorNivelSerializer,
    CatalogoPlazasSerializer,
    ConstantesSistemaSerializer,
    ConceptosPresupuestalSerializer,
)
from .valuacion import calcular_valuacion
from django.db import connection
from django.db.models import Q


def _build_catalogo_index():
    """Índice (codigo, nivel) -> [CatalogoPlazas] para resolver cada grupo
    Código Presupuestal + Nivel de nómina contra catalogo_plazas.
    """
    por_codigo_nivel = {}
    for plaza in CatalogoPlazas.objects.all():
        por_codigo_nivel.setdefault((plaza.codigo, plaza.nivel), []).append(plaza)
    return por_codigo_nivel


def _resolver_catalogo(por_codigo_nivel, codigo_presupuestal, escala, nivel):
    """Resuelve la fila única de catalogo_plazas para (Código Presupuestal, Escala, Nivel) de nómina.

    El cruce es exacto por (codigo, nivel): 1) match directo, 2) si no hay,
    sustituir los primeros 2 caracteres del código presupuestal por "EV" y
    reintentar (catalogo_plazas usa códigos "EV" para todas las plazas), 3) si
    hay más de un candidato, desempatar por zona == escala. Si no queda un
    único candidato, el grupo no cruza y no se cuenta.
    """
    codigo_presupuestal = (codigo_presupuestal or '').strip()
    nivel = (nivel or '').strip()

    candidatos = por_codigo_nivel.get((codigo_presupuestal, nivel), [])
    if not candidatos:
        codigo_ev = 'EV' + codigo_presupuestal[2:]
        candidatos = por_codigo_nivel.get((codigo_ev, nivel), [])
    if len(candidatos) > 1:
        candidatos = [c for c in candidatos if str(c.zona) == str(escala).strip()]
    return candidatos[0] if len(candidatos) == 1 else None


def _query_niveles_totales(partida):
    """Total de plazas activas (Estado Psn='A') por Nivel para la partida dada,
    sin filtrar por Estado Nómina, junto con cuántas de esas están ocupadas
    (Estado Nómina <> ' '). Da el universo contra el que se compara el
    desglose por Código Presupuestal de `_resolver_ocupadas`.
    """
    query = """
        WITH base AS (
            SELECT e.`Nivel` AS nivel, e.`Estado Nómina` AS estado_nomina
            FROM EMPLEADOS_COMPLETOS_SIG e
            INNER JOIN MOV_POS m
                ON e.`Posición` = m.`Nº Pos Actual`
            INNER JOIN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY `Nº Pos Actual`
                        ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                    ) AS rn
                    FROM MOV_POS
                ) ranked WHERE rn = 1
            ) latest ON m.id = latest.id
            WHERE m.`Estado Psn` = 'A'
              AND e.Partida = %s
              AND e.`Posición` NOT LIKE '103L%%'
        )
        SELECT nivel, COUNT(*) AS total, SUM(CASE WHEN estado_nomina <> ' ' THEN 1 ELSE 0 END) AS ocupadas
        FROM base
        GROUP BY nivel
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [partida])
        rows = cursor.fetchall()
    return {
        (nivel or '').strip(): {
            "total_plazas": int(total),
            "ocupadas": int(ocupadas),
            "vacantes": int(total) - int(ocupadas),
        }
        for nivel, total, ocupadas in rows
    }


def _resolver_ocupadas(rows, niveles_totales):
    index = _build_catalogo_index()
    plazas, sin_match = [], []
    detalle_niveles = {}
    for codigo_presupuestal, escala, nivel, cantidad in rows:
        nivel_key = (nivel or '').strip()
        plaza = _resolver_catalogo(index, codigo_presupuestal, escala, nivel)

        codigo_entry = {
            "codigo_presupuestal": (codigo_presupuestal or '').strip(),
            "escala": escala,
            "cantidad": cantidad,
            "matched": plaza is not None,
        }
        if plaza:
            codigo_entry.update({"catalogo_id": plaza.id, "zona": plaza.zona, "denominacion": plaza.denominacion})
            plazas.append({
                "catalogo_id": plaza.id,
                "codigo": plaza.codigo,
                "nivel": plaza.nivel,
                "zona": plaza.zona,
                "denominacion": plaza.denominacion,
                "cantidad": cantidad,
            })
        else:
            sin_match.append({
                "codigo_presupuestal": codigo_presupuestal,
                "escala": escala,
                "nivel": nivel,
                "cantidad": cantidad,
            })

        totales = niveles_totales.get(nivel_key, {"total_plazas": None, "ocupadas": None, "vacantes": None})
        detalle = detalle_niveles.setdefault(nivel_key, {**totales, "codigos": []})
        detalle["codigos"].append(codigo_entry)

    for detalle in detalle_niveles.values():
        detalle["codigos"].sort(key=lambda c: c["cantidad"], reverse=True)

    return plazas, sin_match, detalle_niveles


class ValuacionPresupuestariaPorNivelViewSet(viewsets.ModelViewSet):
    queryset = ValuacionPresupuestariaPorNivel.objects.all()
    serializer_class = ValuacionPresupuestariaPorNivelSerializer
    view_permission = "authentication.view_valuacion_presupuestaria"


class CatalogoPlazasViewSet(viewsets.ModelViewSet):
    queryset = CatalogoPlazas.objects.all()
    serializer_class = CatalogoPlazasSerializer
    # El listado (GET) lo consume tanto el tab "Parámetros" como el Simulador
    # (busca/selecciona plazas de este mismo catálogo) — cualquiera de los 2
    # permisos basta para leer. Escribir (editar el catálogo) sí exige
    # específicamente Parámetros. Las 3 @action de abajo las usan Simulador y
    # Asuntos de Plazas con permiso distinto — de ahí action_permissions.
    view_permission = (
        "authentication.view_valuacion_presupuestaria",
        "authentication.edit_valuacion_parametros",
    )
    edit_permission = "authentication.edit_valuacion_parametros"
    action_permissions = {
        "calcular": "authentication.view_valuacion_presupuestaria",
        "eventuales_ocupadas": "authentication.view_valuacion_presupuestaria",
        "permanentes_ocupadas": "authentication.view_valuacion_presupuestaria",
    }

    @action(detail=False, methods=['get'])
    def eventuales_ocupadas(self, request):
        query = """
            WITH base AS (
                SELECT e.`Código Presupuestal`, e.`Escala`, e.`Nivel`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN MOV_POS m
                    ON e.`Posición` = m.`Nº Pos Actual`
                INNER JOIN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (
                            PARTITION BY `Nº Pos Actual`
                            ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                        ) AS rn
                        FROM MOV_POS
                    ) ranked WHERE rn = 1
                ) latest ON m.id = latest.id
                WHERE m.`Estado Psn` = 'A'
                  AND e.Partida = '12201'
                  AND e.`Estado Nómina` <> ' '
            )
            SELECT `Código Presupuestal`, `Escala`, `Nivel`, COUNT(*) AS num_plazas
            FROM base
            GROUP BY `Código Presupuestal`, `Escala`, `Nivel`
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        niveles_totales = _query_niveles_totales('12201')
        plazas, sin_match, detalle_niveles = _resolver_ocupadas(rows, niveles_totales)
        return Response({"plazas": plazas, "sin_match": sin_match, "detalle_niveles": detalle_niveles})

    @action(detail=False, methods=['get'])
    def permanentes_ocupadas(self, request):
        query = """
            WITH base AS (
                SELECT e.`Código Presupuestal`, e.`Escala`, e.`Nivel`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN MOV_POS m
                    ON e.`Posición` = m.`Nº Pos Actual`
                INNER JOIN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (
                            PARTITION BY `Nº Pos Actual`
                            ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                        ) AS rn
                        FROM MOV_POS
                    ) ranked WHERE rn = 1
                ) latest ON m.id = latest.id
                WHERE m.`Estado Psn` = 'A'
                  AND e.Partida = '11301'
                  AND e.`Estado Nómina` <> ' '
                  AND e.`Posición` NOT LIKE '103L%'
            )
            SELECT `Código Presupuestal`, `Escala`, `Nivel`, COUNT(*) AS num_plazas
            FROM base
            GROUP BY `Código Presupuestal`, `Escala`, `Nivel`
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        niveles_totales = _query_niveles_totales('11301')
        plazas, sin_match, detalle_niveles = _resolver_ocupadas(rows, niveles_totales)
        return Response({"plazas": plazas, "sin_match": sin_match, "detalle_niveles": detalle_niveles})

    @action(detail=False, methods=['post'])
    def calcular(self, request):
        meses = request.data.get('meses', 12)
        plazas_input = request.data.get('plazas', []) # List of {catalogo_id: number, plazas: number}

        if not plazas_input:
            return Response({"error": "No se enviaron plazas para calcular"}, status=status.HTTP_400_BAD_REQUEST)

        # La aritmética vive en `presupuesto/valuacion.py` porque la comparte
        # con la generación del Anexo 3 (ver AnuenciaAnexo3View): los importes
        # del simulador y los del Anexo 3 impreso tienen que ser los mismos.
        return Response(calcular_valuacion(meses, plazas_input))


class ConstantesSistemaViewSet(viewsets.ModelViewSet):
    queryset = ConstantesSistema.objects.all()
    serializer_class = ConstantesSistemaSerializer
    view_permission = "authentication.edit_valuacion_parametros"


class ConceptosPresupuestalViewSet(viewsets.ModelViewSet):
    queryset = ConceptosPresupuestal.objects.all()
    serializer_class = ConceptosPresupuestalSerializer
    view_permission = "authentication.edit_valuacion_parametros"
