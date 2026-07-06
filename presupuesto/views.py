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
import re

_NIVEL_LETRA_RE = re.compile(r'^[A-Za-z]')


def _build_catalogo_index():
    """Índices para resolver ambigüedad de `nivel` contra catalogo_plazas.

    - `por_nivel`: nivel -> [CatalogoPlazas]. Los niveles letra+número (P12, D209...)
      son únicos en todo el catálogo, sin importar el codigo.
    - `por_codigo_nivel`: (codigo, nivel) -> [CatalogoPlazas]. Los niveles numéricos
      puros (2..11) se repiten entre distintos codigos (uno por cada puesto), así
      que ahí sí hace falta el codigo para desambiguar.
    """
    por_nivel, por_codigo_nivel = {}, {}
    for plaza in CatalogoPlazas.objects.all():
        por_nivel.setdefault(plaza.nivel, []).append(plaza)
        por_codigo_nivel.setdefault((plaza.codigo, plaza.nivel), []).append(plaza)
    return por_nivel, por_codigo_nivel


def _resolver_catalogo(indices, codigo_presupuestal, escala, nivel):
    """Resuelve la fila única de catalogo_plazas para (Código Presupuestal, Escala, Nivel) de nómina.

    Regla de negocio: niveles letra+número son únicos por nivel solo; niveles
    numéricos puros necesitan 1) match directo por codigo+nivel, 2) si no hay,
    sustituir los primeros 2 caracteres del código presupuestal por "EV" y
    reintentar, 3) si hay más de un candidato, desempatar por zona == escala.
    """
    por_nivel, por_codigo_nivel = indices
    codigo_presupuestal = (codigo_presupuestal or '').strip()
    nivel = (nivel or '').strip()

    if _NIVEL_LETRA_RE.match(nivel):
        candidatos = por_nivel.get(nivel, [])
        return candidatos[0] if len(candidatos) == 1 else None

    candidatos = por_codigo_nivel.get((codigo_presupuestal, nivel), [])
    if not candidatos:
        codigo_ev = 'EV' + codigo_presupuestal[2:]
        candidatos = por_codigo_nivel.get((codigo_ev, nivel), [])
    if len(candidatos) > 1:
        candidatos = [c for c in candidatos if str(c.zona) == str(escala).strip()]
    return candidatos[0] if len(candidatos) == 1 else None


def _resolver_ocupadas(rows):
    index = _build_catalogo_index()
    plazas, sin_match = [], []
    for codigo_presupuestal, escala, nivel, cantidad in rows:
        plaza = _resolver_catalogo(index, codigo_presupuestal, escala, nivel)
        if plaza:
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
    return plazas, sin_match


class ValuacionPresupuestariaPorNivelViewSet(viewsets.ModelViewSet):
    queryset = ValuacionPresupuestariaPorNivel.objects.all()
    serializer_class = ValuacionPresupuestariaPorNivelSerializer


class CatalogoPlazasViewSet(viewsets.ModelViewSet):
    queryset = CatalogoPlazas.objects.all()
    serializer_class = CatalogoPlazasSerializer

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
        plazas, sin_match = _resolver_ocupadas(rows)
        return Response({"plazas": plazas, "sin_match": sin_match})

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
        plazas, sin_match = _resolver_ocupadas(rows)
        return Response({"plazas": plazas, "sin_match": sin_match})

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


class ConceptosPresupuestalViewSet(viewsets.ModelViewSet):
    queryset = ConceptosPresupuestal.objects.all()
    serializer_class = ConceptosPresupuestalSerializer
