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

        # Map catalog ids to quantities
        plazas_map = {item['catalogo_id']: item['plazas'] for item in plazas_input}
        ids = list(plazas_map.keys())

        # Fetch relevant catalog entries
        catalogo = CatalogoPlazas.objects.filter(id__in=ids)
        
        # Intermediate sums
        u305 = 0 # sueldo
        y305 = 0 # apoyo_capacitacion
        aa305 = 0 # compensacion_garantizada
        w306 = 0 # asignaciones adicionales (despensa + prev_social + ayuda_serv + apoyo_cap + ayuda_trans)
        ab305 = 0 # gastos_medicos (hardcoded to 0 in todo.md example)
        ai305 = 0 # cuota_issste
        aj305 = 0 # cuota_fovissste
        ak305 = 0 # cuota_cesantia
        bh305 = 0 # epr_quincenal (if tiene_epr)
        
        u_gv1 = 0 # grupo_vacaciones = 1
        u_gv2 = 0 # grupo_vacaciones = 2
        u_gg1 = 0 # grupo_gratificacion = 1
        u_gg2 = 0 # grupo_gratificacion = 2
        
        total_plazas = 0
        tabla_2022 = []

        for plaza in catalogo:
            p_qty = plazas_map.get(plaza.id, 0)
            if p_qty <= 0:
                continue
            
            total_plazas += p_qty
            
            # Sums
            u305 += float(plaza.sueldo) * p_qty
            y305 += float(plaza.apoyo_capacitacion) * p_qty
            aa305 += float(plaza.compensacion_garantizada) * p_qty
            
            asignaciones_plaza = (
                float(plaza.despensa) +
                float(plaza.prev_social_multiple) +
                float(plaza.ayuda_servicios) +
                float(plaza.apoyo_capacitacion) +
                float(plaza.ayuda_transporte)
            )
            w306 += asignaciones_plaza * p_qty
            
            ai305 += float(plaza.cuota_issste) * p_qty
            aj305 += float(plaza.cuota_fovissste) * p_qty
            ak305 += float(plaza.cuota_cesantia) * p_qty
            
            if plaza.tiene_epr:
                bh305 += float(plaza.epr_quincenal) * p_qty
            
            # Vacation groups
            if plaza.grupo_vacaciones == 1:
                u_gv1 += float(plaza.sueldo) * p_qty
            else:
                u_gv2 += float(plaza.sueldo) * p_qty
                
            # Gratification groups
            if plaza.grupo_gratificacion == 1:
                u_gg1 += float(plaza.sueldo) * p_qty
            else:
                u_gg2 += float(plaza.sueldo) * p_qty

            # Table 2022 row
            tabla_2022.append({
                "nivel": plaza.nivel,
                "zona": plaza.zona,
                "codigo": plaza.codigo,
                "puesto": plaza.denominacion,
                "plazas": p_qty,
                "sueldo": float(plaza.sueldo),
                "sueldo_colectivo_periodo": float(plaza.sueldo) * p_qty * meses,
                "compensacion": float(plaza.compensacion_garantizada),
                "compensacion_colectiva_periodo": float(plaza.compensacion_garantizada) * p_qty * meses,
            })

        # Calculations for 13201 and 13202
        u322 = u_gv1 + u_gv2 + (u_gv2 * 0.15)
        t_13201 = u322 / 3
        r_13201 = (t_13201 * meses) / 12

        u326 = (u_gg1 / 30) * 40 * 1.35
        u327 = (u_gg2 / 30) * 40 * 1.17
        t_13202 = u326 + u327
        r_13202 = (t_13202 * meses) / 12

        # Concept rows
        r_12201 = u305 * meses
        t_12201 = u305 * 12
        r_15402 = aa305 * meses
        t_15402 = aa305 * 12

        conceptos_data = [
            ("12201", "Sueldos Base", r_12201, t_12201),
            ("13101", "(Reservado)", 0, 0),
            ("13201", "Primas de vacaciones y dominical", r_13201, t_13201),
            ("13202", "Gratificación de fin de año", r_13202, t_13202),
            ("13409", "(Reservado)", 0, 0),
            ("14101", "Aportaciones ISSSTE", ai305 * meses, ai305 * 12),
            ("14201", "Aportaciones FOVISSSTE", aj305 * meses, aj305 * 12),
            ("14401", "Cuota sindical (1.4%)", (r_12201 + r_15402) * 0.014, (t_12201 + t_15402) * 0.014),
            ("14403", "Cuotas gastos médicos", ab305 * meses, ab305 * 12),
            ("14404", "Seg. separación individualizado", 0, 0),
            ("14405", "Seg. colectivo de retiro", 35.45 * total_plazas * meses, 35.45 * total_plazas * 12),
            ("14301", "Aportación solidaria FOVISSSTE 2%", (u305 + y305) * meses * 0.02, (u305 + y305) * 12 * 0.02),
            ("14105", "Cesantía edad avanzada", ak305 * meses, ak305 * 12),
            ("14302", "Ahorro solidario (res.)", 0, 0),
            ("15402", "Compensación Garantizada", r_15402, t_15402),
            ("15403", "Asignaciones adicionales", w306 * meses, w306 * 12),
        ]

        tabla_q322_t348 = []
        subtotal1 = {"periodo": 0, "anual": 0, "complemento": 0}
        
        for c, desc, r, t in conceptos_data:
            row = {
                "concepto": c,
                "descripcion": desc,
                "periodo": r,
                "anual": t,
                "complemento": t - r
            }
            tabla_q322_t348.append(row)
            subtotal1["periodo"] += r
            subtotal1["anual"] += t
            subtotal1["complemento"] += (t - r)

        c_15901 = {
            "concepto": "15901",
            "descripcion": "EPR Operativo",
            "periodo": bh305 * meses,
            "anual": bh305 * 12,
            "complemento": (bh305 * 12) - (bh305 * meses)
        }
        tabla_q322_t348.append(c_15901)
        
        subtotal2 = {
            "periodo": c_15901["periodo"],
            "anual": c_15901["anual"],
            "complemento": c_15901["complemento"]
        }
        
        total = {
            "periodo": subtotal1["periodo"] + subtotal2["periodo"],
            "anual": subtotal1["anual"] + subtotal2["anual"],
            "complemento": subtotal1["complemento"] + subtotal2["complemento"]
        }

        return Response({
            "tabla_2022": tabla_2022,
            "tabla_q322_t348": tabla_q322_t348,
            "subtotal1": subtotal1,
            "subtotal2": subtotal2,
            "total": total
        })


class ConstantesSistemaViewSet(viewsets.ModelViewSet):
    queryset = ConstantesSistema.objects.all()
    serializer_class = ConstantesSistemaSerializer
    view_permission = "authentication.edit_valuacion_parametros"


class ConceptosPresupuestalViewSet(viewsets.ModelViewSet):
    queryset = ConceptosPresupuestal.objects.all()
    serializer_class = ConceptosPresupuestalSerializer
    view_permission = "authentication.edit_valuacion_parametros"
