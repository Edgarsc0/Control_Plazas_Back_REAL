import json
import logging

from django.conf import settings
from django.core import exceptions
from django.db.models import (
    Aggregate,
    Case,
    CharField,
    Count,
    F,
    IntegerField,
    Q,
    Sum,
    When,
)
from django.db import transaction
from django.db.models.functions import Trim
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CatAcciones,
    CatAccionesMotivos,
    CatNivelJerarquicoPlaza,
    CatPtoFunc,
    CuadroVacancia,
    DESCRIPCION_NJ_CHOICES,
    EmpleadosCompletosSig,
    MovPos,
    MovPosLatest,
    NivelJerarquicoPrioridadConfig,
    Plantilla1800Plazas,
    RcCatCodPresupuestal,
)
from .nivel_jerarquico_sync import aplicar_prioridad_nivel_jerarquico
from .serializers import (
    CatAccionesMotivosSerializer,
    CatAccionesSerializer,
    CatNivelJerarquicoPlazaSerializer,
    CatPtoFuncSerializer,
    RcCatCodPresupuestalSerializer,
)

logger = logging.getLogger(__name__)


class GroupConcat(Aggregate):
    """Agregado GROUP_CONCAT(DISTINCT ...) para MySQL (no incluido en Django).

    Separador 0x1f (unit separator) para no chocar con comas en los valores.
    """

    function = "GROUP_CONCAT"
    template = "%(function)s(DISTINCT %(expressions)s SEPARATOR 0x1f)"
    output_field = CharField()


# Sentinel que el frontend manda en vez de "" para seleccionar "(Vacío)" en un
# filtro de columna: una cadena vacía real en la URL se descarta antes de
# llegar aquí (buildQuery del front, y el chequeo `not val` de abajo).
EMPTY_VALUE_TOKEN = "__EMPTY__"

# Parámetros de control que NO son columnas filtrables (paginación, orden, etc.).
FILTER_SKIP_PARAMS = frozenset(
    {
        "distinct_field",
        "distinct_search",
        "page",
        "page_size",
        "search",
        "is_latest",
        "no_pagination",
        "sort_by",
        "sort_order",
        "oficio",
        "nivel",
        "advanced_filters",
    }
)


def apply_text_search(queryset, query, fields):
    """Filtro de búsqueda libre: OR de ``icontains`` sobre ``fields``."""
    query = (query or "").strip()
    if not query:
        return queryset
    q = Q()
    for field in fields:
        q |= Q(**{f"{field}__icontains": query})
    return queryset.filter(q)


def apply_dynamic_column_filters(queryset, request, model, skip_params=FILTER_SKIP_PARAMS):
    """Aplica los filtros dinámicos de columna del frontend.

    Soporta ``?campo=val``, selección múltiple (``val1,val2`` -> ``__in``),
    sufijos explícitos (``__istartswith``/``__iexact``/...) y negación
    (``exclude__campo=val``). Las columnas de texto se filtran sobre
    ``Trim(campo)`` (anotando ``trimmed_<campo>``), que es lo que aprovechan los
    índices funcionales. Lógica única compartida por MovPosDetalleView y
    MovimientosPersonalListView (antes estaba duplicada).
    """
    valid_fields = {f.name for f in model._meta.get_fields()}
    text_fields = {
        f.name
        for f in model._meta.get_fields()
        if f.get_internal_type() in ("CharField", "TextField")
    }
    skip = set(skip_params)

    for param, val in request.query_params.items():
        if param in skip:
            continue
        is_exclude = param.startswith("exclude__")
        actual_param = param[9:] if is_exclude else param
        base_field = actual_param.split("__")[0]
        if base_field not in valid_fields or not val:
            continue

        is_text = base_field in text_fields
        target_field = f"trimmed_{base_field}" if is_text else base_field
        if is_text and target_field not in queryset.query.annotations:
            queryset = queryset.annotate(**{target_field: Trim(base_field)})

        if "__" in actual_param:
            suffix = actual_param.split("__", 1)[1]
            actual_param_target = f"{target_field}__{suffix}"
        else:
            suffix = None
            actual_param_target = target_field

        val_list = [
            "" if v.strip() == EMPTY_VALUE_TOKEN else v.strip()
            for v in val.split(",")
            if v.strip()
        ]
        apply = queryset.exclude if is_exclude else queryset.filter

        if suffix == "in" or (not suffix and len(val_list) > 1):
            if "" in val_list:
                # "" en trimmed_<campo> no matchea filas con NULL real en
                # MySQL (Trim(NULL) es NULL); hay que cubrir ambos casos.
                q = Q(**{f"{target_field}__in": val_list}) | Q(
                    **{f"{target_field}__isnull": True}
                )
                queryset = queryset.exclude(q) if is_exclude else queryset.filter(q)
            else:
                queryset = apply(**{f"{target_field}__in": val_list})
        elif suffix:
            value = val_list[0] if len(val_list) == 1 else val_list
            queryset = apply(**{actual_param_target: value})
        elif is_text:
            queryset = apply(**{f"{target_field}__icontains": val_list[0]})
        else:
            queryset = apply(**{target_field: val_list[0]})

    return queryset


def apply_advanced_filters(queryset, request, model, computed_resolver=None):
    """Aplica las condiciones del modal "Filtros Avanzados" (``?advanced_filters=``).

    JSON array de: ``{ column, condition, compareType, compareColumn, value, logic }``.
    ``logic`` en el item i combina (AND/OR) con el Q acumulado de los items 0..i-1.
    ``computed_resolver(column, condition, value) -> Q | None`` permite que el
    caller resuelva columnas calculadas que no son campos reales del modelo
    (p. ej. "ocupacion"/"total_movimientos" en MovPos). Lógica única compartida
    por MovPosDetalleView y MovimientosPersonalListView (antes solo vivía,
    inline, en MovPosDetalleView).
    """
    advanced_filters_raw = request.query_params.get("advanced_filters", "").strip()
    if not advanced_filters_raw:
        return queryset

    try:
        advanced_conditions = json.loads(advanced_filters_raw)
    except (ValueError, TypeError):
        return queryset

    if not isinstance(advanced_conditions, list):
        return queryset
    advanced_conditions = advanced_conditions[:20]  # sanity cap

    valid_fields = {f.name for f in model._meta.get_fields()}
    text_fields = {
        f.name
        for f in model._meta.get_fields()
        if f.get_internal_type() in ("CharField", "TextField")
    }

    date_lookup_by_condition = {
        "before": "lt",
        "after": "gt",
        "before_or_equal": "lte",
        "after_or_equal": "gte",
        "equals": None,
        "not_equals": None,
    }
    text_lookup_by_condition = {
        "contains": ("icontains", False),
        "not_contains": ("icontains", True),
        "starts_with": ("istartswith", False),
        "not_starts_with": ("istartswith", True),
        "ends_with": ("iendswith", False),
        "not_ends_with": ("iendswith", True),
        "equals": ("iexact", False),
        "not_equals": ("iexact", True),
    }

    def resolve_target_field(field_name):
        nonlocal queryset
        if field_name in text_fields:
            target = f"trimmed_{field_name}"
            if target not in queryset.query.annotations:
                queryset = queryset.annotate(**{target: Trim(field_name)})
            return target
        return field_name

    def build_condition_q(cond):
        if not isinstance(cond, dict):
            return None
        column = cond.get("column")

        if column not in valid_fields:
            if computed_resolver is None:
                return None
            if cond.get("compareType", "valor") == "campo":
                return None  # comparing a computed column to another field isn't supported
            value = cond.get("value", "")
            if value is None or str(value).strip() == "":
                return None
            return computed_resolver(
                column, cond.get("condition", "contains"), str(value).strip()
            )

        condition = cond.get("condition", "contains")
        compare_type = cond.get("compareType", "valor")
        target_field = resolve_target_field(column)
        is_text = column in text_fields

        if compare_type == "campo":
            compare_column = cond.get("compareColumn")
            if compare_column not in valid_fields:
                return None
            target_compare_field = resolve_target_field(compare_column)
            f_expr = F(target_compare_field)

            if condition == "equals":
                return Q(**{target_field: f_expr})
            if condition == "not_equals":
                return ~Q(**{target_field: f_expr})
            if condition == "before":
                return Q(**{f"{target_field}__lt": f_expr})
            if condition == "after":
                return Q(**{f"{target_field}__gt": f_expr})
            if condition == "before_or_equal":
                return Q(**{f"{target_field}__lte": f_expr})
            if condition == "after_or_equal":
                return Q(**{f"{target_field}__gte": f_expr})
            return None

        # compare_type == 'valor'
        value = cond.get("value", "")
        if value is None or str(value).strip() == "":
            return None
        value = str(value).strip()

        if condition in ("before", "after", "before_or_equal", "after_or_equal"):
            lookup = date_lookup_by_condition.get(condition)
            if not lookup:
                return None
            return Q(**{f"{target_field}__{lookup}": value})

        if is_text and condition in text_lookup_by_condition:
            lookup, negate = text_lookup_by_condition[condition]
            q = Q(**{f"{target_field}__{lookup}": value})
            return ~q if negate else q

        if condition == "equals":
            return Q(**{target_field: value})
        if condition == "not_equals":
            return ~Q(**{target_field: value})

        return None

    combined_q = None
    for cond in advanced_conditions:
        q = build_condition_q(cond)
        if q is None:
            continue
        if combined_q is None:
            combined_q = q
        elif (cond.get("logic") or "AND").upper() == "OR":
            combined_q = combined_q | q
        else:
            combined_q = combined_q & q

    if combined_q is not None:
        queryset = queryset.filter(combined_q)

    return queryset


MOV_POS_COLUMN_LABELS = {
    "no_pos_actual": "No. Posición",
    "total_movimientos": "Histórico",
    "ocupacion": "Ocupación",
    "fecha_vacancia": "Fecha de Vacancia",
    "estado_psn": "Estado (A/I)",
    "f_efva": "Fecha Efectiva",
    "cd_motivo": "Cod. Motivo",
    "motivo": "Motivo",
    "cd_un": "Cod. UN",
    "unidad_de_negocio": "Unidad Negocio",
    "unidad_adva": "Unidad Adva",
    "cd_departamento": "Cod. Depto",
    "cd_puesto": "Cod. Puesto",
    "puesto_ptal": "Puesto Ptal",
    "estado_ptal": "Estado Ptal",
    "fecha_est": "Fecha Est",
    "maximo": "Máximo",
    "depnd_drt": "Depnd Drt",
    "depnd_indrt": "Depnd Indrt",
    "ubicacion": "Ubicación",
    "nvl_direc": "Nvl Direc",
    "plan_sal": "Plan Sal",
    "grado": "Grado",
    "esc": "Esc",
    "partida_ptal": "Partida Ptal",
    "gp_pago": "Gp Pago",
    "prog_beneficios": "Prog Beneficios",
    "fecha_captura": "Fecha Captura",
    "fh_ult_actz": "F/H Últ Actz",
    "por": "Por",
    "hr_estd_semn": "Hr Estd/Semn",
    "descr": "Descr",
    "gp_trabajo": "Gp Trabajo",
    "org_code": "Org Code",
    "grupo_cd_sal": "Grupo Cd Sal",
    "formal_desc": "Formal Desc",
    "pto_compt": "Pto Compt",
    "posn_clv": "Posn Clv",
    "presupuesto": "Presupuesto",
    "nombre_puesto": "Nombre Puesto",
    "categoria_vacancia": "Categoría Vacancia",
    "tuvo_insubsistencia": "Tuvo Insubsistencia",
}

MOV_POS_MONO_COLUMNS = {
    "no_pos_actual", "cd_un", "cd_departamento", "cd_puesto",
    "maximo", "grado", "esc", "partida_ptal",
}

# Columnas sintéticas del export de "Vacantes": desglosan el mismo registro
# decisivo que MovPosVacanciaDetalleView resuelve para el modal "Detalle de
# Vacancia", pero resuelto por lote para todas las filas del export.
VACANCIA_DETALLE_COLUMN_LABELS = {
    "vac_empleado_relacionado": "Empleado Relacionado",
    "vac_num_empleado": "Número de Empleado",
    "vac_accion": "Acción",
    "vac_motivo": "Motivo de la Vacancia",
    "vac_posicion_destino": "Posición Destino",
    "vac_fecha_efectiva_mov": "Fecha Efectiva del Movimiento",
    "vac_fecha_captura_mov": "Fecha de Captura del Movimiento",
    "vac_insub_persona": "Insubsistencia - Persona",
    "vac_insub_num_empleado": "Insubsistencia - Número de Empleado",
    "vac_insub_motivo": "Insubsistencia - Motivo",
    "vac_insub_fecha_efectiva": "Insubsistencia - Fecha Efectiva",
    "vac_insub_fecha_captura": "Insubsistencia - Fecha de Captura",
}

# Claves insertadas justo después de "categoria_vacancia" (detalle de la baja
# o el traslado que originó la vacancia).
VACANCIA_DETALLE_CATEGORIA_KEYS = [
    "vac_empleado_relacionado", "vac_num_empleado", "vac_accion", "vac_motivo",
    "vac_posicion_destino", "vac_fecha_efectiva_mov", "vac_fecha_captura_mov",
]

# Claves insertadas justo después de "tuvo_insubsistencia".
VACANCIA_DETALLE_INSUBSISTENCIA_KEYS = [
    "vac_insub_persona", "vac_insub_num_empleado", "vac_insub_motivo",
    "vac_insub_fecha_efectiva", "vac_insub_fecha_captura",
]


def _enrich_rows_with_vacancia_detalle(resultados):
    """Rellena en cada fila de MOV_POS (dicts de queryset.values()) las
    columnas sintéticas de VACANCIA_DETALLE_COLUMN_LABELS, resolviendo por
    lote (una sola query IN) los registros decisivos en
    cp_tbl_mov_completo_29_05_26 en vez de repetir la lógica N+1 de
    MovPosVacanciaDetalleView por cada fila."""
    from .models import CpTblMovCompleto290526

    decisivo_ids, insub_ids = set(), set()
    for r in resultados:
        if r.get("id_registro_desicivo"):
            decisivo_ids.add(r["id_registro_desicivo"])
        if (r.get("tuvo_insubsistencia") or "").strip().upper() == "S" and r.get("id_insubsistencia_detectada"):
            insub_ids.add(r["id_insubsistencia_detectada"])

    registros_by_id = {}
    all_ids = decisivo_ids | insub_ids
    if all_ids:
        registros_by_id = {
            reg.id: reg for reg in CpTblMovCompleto290526.objects.filter(id__in=all_ids)
        }

    def _nombre_completo(reg):
        return " ".join(p for p in [reg.nombre, reg.ap_pat, reg.ap_mat] if p).strip()

    for r in resultados:
        for key in VACANCIA_DETALLE_COLUMN_LABELS:
            r[key] = ""

        categoria = (r.get("categoria_vacancia") or "").strip().upper()
        id_decisivo = r.get("id_registro_desicivo")
        if categoria in ("A", "B") and id_decisivo:
            registro = registros_by_id.get(id_decisivo)
            if registro:
                r["vac_empleado_relacionado"] = _nombre_completo(registro)
                r["vac_num_empleado"] = registro.num_empleado
                r["vac_accion"] = registro.accion_nombre or registro.accion
                r["vac_motivo"] = registro.motivo_nombre or registro.motivo
                r["vac_fecha_efectiva_mov"] = registro.fecha_efectiva
                r["vac_fecha_captura_mov"] = registro.fecha_captura
                if categoria == "B":
                    r["vac_posicion_destino"] = registro.posicion

        if (r.get("tuvo_insubsistencia") or "").strip().upper() == "S":
            id_insub = r.get("id_insubsistencia_detectada")
            registro_ins = registros_by_id.get(id_insub) if id_insub else None
            if registro_ins:
                r["vac_insub_persona"] = _nombre_completo(registro_ins)
                r["vac_insub_num_empleado"] = registro_ins.num_empleado
                r["vac_insub_motivo"] = registro_ins.motivo_nombre or registro_ins.motivo
                r["vac_insub_fecha_efectiva"] = registro_ins.fecha_efectiva
                r["vac_insub_fecha_captura"] = registro_ins.fecha_captura


# Descripción de cada categoría de vacancia, igual a CATEGORIA_VACANCIA_TOOLTIP
# en MovimientosTab.jsx (modal "Detalle de Vacancia").
VACANCIA_CATEGORIA_DESCRIPCIONES = {
    "A": "Posición vacante porque empleado que la ocupaba causó baja",
    "B": "Posición vacante porque empleado que la ocupaba cambió a otra posición, vacancia = fecha en que tomó esa nueva posición",
    "C": "Posición vacante porque jamás tuvo ocupante, vacancia = fecha creación posición",
}

# Texto explicativo (2 renglones) mostrado en las filas 7-8 del export de
# "Vacantes", arriba del header real (fila 9). Clave ausente = columna sin nota.
VACANCIA_EXPORT_COLUMN_NOTES = {
    "total_movimientos": ("Cantidad de movimientos", "que ha tenido la posición"),
    "fecha_vacancia": ("Fecha de vacancia calculada por", "el Sistema de Control de Plazas (SCP)"),
    "categoria_vacancia": ("Identificador de causa", "de vacancia asignado por el SCP"),
    "vac_empleado_relacionado": ("Empleado que causó baja o fue trasladado", "a otra posición según aplique el caso (categoría de vacancia)"),
    "vac_num_empleado": ("Número de empleado que causó baja o fue trasladado", "a otra posición según aplique el caso (categoría de vacancia)"),
    "vac_accion": ("Acción del movimiento", "que provocó la baja o traslado"),
    "vac_motivo": ("Motivo del movimiento que provocó", "la baja o traslado"),
    "vac_posicion_destino": ("Posición Destino", "a la que fue trasladado el empleado"),
    "vac_fecha_efectiva_mov": ("Fecha Efectiva del Movimiento", "reportado en las columnas de Acción y Motivo"),
    "vac_fecha_captura_mov": ("Fecha de Captura del Movimiento", "reportado en las columnas de Acción y Motivo"),
    "tuvo_insubsistencia": ("¿Tuvo Insubsistencia", "la posición?"),
    "vac_insub_persona": ("Persona que causó", "la insubsistencia"),
    "vac_insub_num_empleado": ("No. Empleado de la persona que causó", "la insubsistencia"),
    "vac_insub_motivo": ("Motivo", "de la insubsistencia"),
    "vac_insub_fecha_efectiva": ("Fecha efectiva", "de la insubsistencia"),
    "vac_insub_fecha_captura": ("Fecha de captura", "de la insubsistencia"),
}

# Ancho mínimo de columna para que el texto largo de las notas explicativas
# (filas 7-8) y la leyenda (filas 1-5) no se vea cortado.
VACANCIA_EXPORT_MIN_COL_WIDTH = {
    "total_movimientos": 22,
    "fecha_vacancia": 24,
    "categoria_vacancia": 24,
    "vac_empleado_relacionado": 46,
    "vac_num_empleado": 30,
    "vac_accion": 20,
    "vac_motivo": 30,
    "vac_posicion_destino": 26,
    "vac_fecha_efectiva_mov": 30,
    "vac_fecha_captura_mov": 30,
    "tuvo_insubsistencia": 20,
    "vac_insub_persona": 38,
    "vac_insub_num_empleado": 34,
    "vac_insub_motivo": 26,
    "vac_insub_fecha_efectiva": 28,
    "vac_insub_fecha_captura": 28,
}

# La leyenda de categorías (E1:H5) vive en columnas fijas, sin relación con
# `visible_keys`; se les da un ancho mínimo propio para que quepan sus textos.
VACANCIA_LEGEND_MIN_COL_WIDTH = {"F": 60, "G": 22, "H": 40}

# (keys en orden, título del grupo para la fila 6, color de fondo de las filas 7-8)
VACANCIA_EXPORT_GROUPS = [
    (["fecha_vacancia", "categoria_vacancia"], "INFORMACIÓN GENERAL DE LA VACANCIA", "FF2A6099"),
    (VACANCIA_DETALLE_CATEGORIA_KEYS, "DETALLE DE LA VACANCIA", "FFBF0041"),
    (["tuvo_insubsistencia"] + VACANCIA_DETALLE_INSUBSISTENCIA_KEYS, "DETALLE DE LA INSUBSISTENCIA", "FF800080"),
]


def _categoria_vacancia_stats(resultados):
    """Cuenta, por cada fila ya exportada (solo vacantes), cuántas son de cada
    categoría de vacancia y cuántas de esas tuvieron insubsistencia."""
    stats = {c: {"total": 0, "insub": 0} for c in ("A", "B", "C")}
    for r in resultados:
        categoria = (r.get("categoria_vacancia") or "").strip().upper()
        if categoria not in stats:
            continue
        stats[categoria]["total"] += 1
        if (r.get("tuvo_insubsistencia") or "").strip().upper() == "S":
            stats[categoria]["insub"] += 1
    return stats


def _write_vacancia_report_cover(ws, visible_keys, resultados):
    """Escribe, solo para el export de solo-"Vacantes", la portada del reporte:
    - Filas 1-5, columnas E-H: leyenda de categorías de vacancia + cantidad de
      plazas y cantidad con insubsistencia por categoría, con fila de totales.
    - Fila 6: encabezados de grupo (merge) sobre "información general",
      "detalle de la vacancia" y "detalle de la insubsistencia".
    - Filas 7-8: nota explicativa de 2 renglones por columna, coloreada según
      el grupo al que pertenece.
    Las filas 6-8 se ubican dinámicamente según la posición real de cada
    columna en `visible_keys`, ya que el usuario puede ocultar columnas del
    resto de la tabla (no. de posición, estado, etc.) desde la UI.
    """
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    align_center = Alignment(horizontal="center", vertical="center")
    font_label = Font(name="Segoe UI", size=10, bold=True, color="FFFFFFFF")
    font_value = Font(name="Segoe UI", size=10, bold=False, color="FF000000")
    font_bold_black = Font(name="Segoe UI", size=10, bold=True, color="FF000000")

    legend_header_fill = PatternFill(start_color="FF2A6099", end_color="FF2A6099", fill_type="solid")
    legend_cat_fill = PatternFill(start_color="FFB4C7DC", end_color="FFB4C7DC", fill_type="solid")
    legend_total_fill = PatternFill(start_color="FFD9D9D9", end_color="FFD9D9D9", fill_type="solid")

    def _cell(row, col, value, fill=None, font=None):
        cell = ws.cell(row=row, column=col, value=value)
        cell.border = border
        cell.alignment = align_center
        cell.font = font or font_value
        if fill:
            cell.fill = fill
        return cell

    # ── Leyenda de categorías (E1:H4) + fila de totales (E5:H5) ─────────────
    stats = _categoria_vacancia_stats(resultados)
    _cell(1, 5, "CATEGORIA DE LA VACANCIA", legend_header_fill, font_label)
    _cell(1, 6, "Descripción", legend_header_fill, font_label)
    _cell(1, 7, "Cantidad de Plazas", legend_header_fill, font_label)
    _cell(1, 8, "Cantidad de Plazas que Tuvieron Insubsistencia", legend_header_fill, font_label)

    for offset, categoria in enumerate(("A", "B", "C")):
        row = 2 + offset
        _cell(row, 5, categoria, legend_cat_fill, font_bold_black)
        _cell(row, 6, VACANCIA_CATEGORIA_DESCRIPCIONES[categoria])
        _cell(row, 7, stats[categoria]["total"])
        _cell(row, 8, stats[categoria]["insub"])

    total_plazas = sum(s["total"] for s in stats.values())
    total_insub = sum(s["insub"] for s in stats.values())
    _cell(5, 5, "TOTAL", legend_total_fill, font_bold_black)
    ws.merge_cells(start_row=5, start_column=5, end_row=5, end_column=6)
    _cell(5, 6, None, legend_total_fill, font_bold_black)
    _cell(5, 7, total_plazas, legend_total_fill, font_bold_black)
    _cell(5, 8, total_insub, legend_total_fill, font_bold_black)

    # ── Fila 6 (grupos) y filas 7-8 (notas explicativas) ────────────────────
    col_index = {key: idx for idx, key in enumerate(visible_keys, start=1)}
    group_fill_by_key = {}
    for keys, group_title, color in VACANCIA_EXPORT_GROUPS:
        cols = sorted(col_index[k] for k in keys if k in col_index)
        if not cols:
            continue
        group_fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        for k in keys:
            group_fill_by_key[k] = group_fill
        start_col, end_col = cols[0], cols[-1]
        black_fill = PatternFill(start_color="FF000000", end_color="FF000000", fill_type="solid")
        _cell(6, start_col, group_title, black_fill, font_label)
        if end_col > start_col:
            ws.merge_cells(start_row=6, start_column=start_col, end_row=6, end_column=end_col)

    yellow_fill = PatternFill(start_color="FFFFFF38", end_color="FFFFFF38", fill_type="solid")
    for key, (line1, line2) in VACANCIA_EXPORT_COLUMN_NOTES.items():
        col = col_index.get(key)
        if not col:
            continue
        fill = group_fill_by_key.get(key)
        # Columnas sin grupo (fondo amarillo, ej. "Histórico") usan texto negro;
        # el blanco quedaba invisible sobre amarillo.
        note_font = font_label if fill else font_bold_black
        fill = fill or yellow_fill
        _cell(7, col, line1, fill, note_font)
        _cell(8, col, line2, fill, note_font)

    # ── Título + fecha/hora de descarga (A1:D2) ─────────────────────────────
    from django.utils import timezone

    meses_es = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    ahora = timezone.localtime(timezone.now())
    fecha_str = f"{ahora.day:02d} de {meses_es[ahora.month - 1]} de {ahora.year}, {ahora.strftime('%I:%M %p')}"

    title_fill = PatternFill(start_color="FF2B4C7E", end_color="FF2B4C7E", fill_type="solid")

    def _merge_box(row, value):
        _cell(row, 1, value, title_fill, font_label)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        for col in range(2, 5):
            _cell(row, col, None, title_fill, font_label)

    _merge_box(1, "Reporte generado por el Sistema de Control de Plazas (SCP)")
    _merge_box(2, f"Fecha y hora de descarga: {fecha_str}")


# Antes recalculaba ROW_NUMBER() OVER sobre toda MOV_POS en cada request
# (~300ms, ver AUDITORIA_BUGS_BACK.md BE2). MOV_POS_LATEST la materializa la
# tarea de importación de ZAFIRO una sola vez por import.
LATEST_MOVPOS_RAW_SQL = "SELECT id FROM MOV_POS_LATEST"

OCUPADAS_RAW_SQL = """
    SELECT DISTINCT e.`Posición`
    FROM EMPLEADOS_COMPLETOS_SIG e
    WHERE (e.`Id Empleado` IS NOT NULL AND TRIM(e.`Id Empleado`) <> '')
       OR (e.`Nombres` IS NOT NULL AND TRIM(e.`Nombres`) <> '');
"""

from django.core.cache import cache
from django.db import connection

from eje_central_back.renderers import orjson_dumps, orjson_response


def obtener_posiciones_activas():
    # Cache active position codes for 60 seconds to speed up parallel requests on page load
    cache_key = "active_position_codes"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        return cached_val

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT `Nº Pos Actual` FROM MOV_POS_LATEST WHERE `Estado Psn` = 'A'
        """)
        result = [row[0] for row in cursor.fetchall() if row[0]]

    cache.set(cache_key, result, 1200)
    return result


def populate_movpos_occupant_details(resultados, posiciones_ocupadas):
    if not resultados:
        return
    pos_list = [r.get("no_pos_actual") for r in resultados if r.get("no_pos_actual")]
    occupants = {}
    if pos_list:
        with connection.cursor() as cursor:
            format_strings = ','.join(['%s'] * len(pos_list))
            query = f"""
                SELECT `Posición`, `Id Empleado`, `Nombres`
                FROM EMPLEADOS_COMPLETOS_SIG
                WHERE `Posición` IN ({format_strings})
            """
            cursor.execute(query, pos_list)
            for row in cursor.fetchall():
                pos_code = row[0]
                id_emp = row[1]
                name = row[2]
                id_emp_str = str(id_emp).strip() if id_emp is not None else ""
                name_str = str(name).strip() if name is not None else ""
                if id_emp_str or name_str:
                    occupants[pos_code] = {
                        "id_empleado": id_emp_str,
                        "nombres": name_str
                    }

    for r in resultados:
        pos = r.get("no_pos_actual")
        is_occupied = pos in posiciones_ocupadas
        occ = occupants.get(pos)
        if is_occupied and occ:
            r["ocupante_id"] = occ["id_empleado"]
            r["ocupante_nombre"] = occ["nombres"]
        else:
            r["ocupante_id"] = ""
            r["ocupante_nombre"] = ""


# Create your views here.
import io

import pandas as pd
from django.http import HttpResponse
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


class ExportExcelView(APIView):
    """
    Vista genérica para exportar datos JSON a un archivo Excel (.xlsx) real con estilos institucionales.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        filename = request.query_params.get("filename", "Export.xlsx")

        if not data or not isinstance(data, list):
            return Response(
                {"error": "Se requiere una lista de objetos para exportar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Convertir JSON a DataFrame de Pandas
            df = pd.DataFrame(data)

            # Crear el archivo Excel en memoria
            output = io.BytesIO()

            # Forzar conversión de todas las columnas a tipos básicos para evitar errores de serialización
            for col in df.columns:
                if df[col].dtype == "object":
                    df[col] = df[col].fillna("")

            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Plantilla")

                workbook = writer.book
                worksheet = writer.sheets["Plantilla"]

                # --- ESTILOS ROBUSTOS ---
                # Usamos códigos ARGB completos (FF + Hex) para máxima compatibilidad
                header_fill = PatternFill(
                    start_color="FF621F32", end_color="FF621F32", fill_type="solid"
                )
                zebra_fill = PatternFill(
                    start_color="FFF9FAFB", end_color="FFF9FAFB", fill_type="solid"
                )
                header_font = Font(color="FFFFFFFF", bold=True, size=11, name="Calibri")
                data_font = Font(size=10, name="Calibri")

                side = Side(style="thin", color="FFD1D5DB")
                thin_border = Border(left=side, right=side, top=side, bottom=side)

                align_center = Alignment(
                    horizontal="center", vertical="center", wrap_text=True
                )
                align_left = Alignment(
                    horizontal="left", vertical="center", wrap_text=True
                )

                # --- PROCESAR ENCABEZADOS ---
                for col_num, column_title in enumerate(df.columns, 1):
                    cell = worksheet.cell(row=1, column=col_num)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.border = thin_border
                    cell.alignment = align_center

                    # Cálculo de ancho ultra-seguro
                    try:
                        # Obtenemos el máximo largo de los datos en esta columna
                        # Filtramos nulos y convertimos a string antes de medir
                        lengths = df[column_title].astype(str).map(len)
                        max_val_len = lengths.max() if not lengths.empty else 0

                        # Manejo de NaN o valores no numéricos en el cálculo
                        if pd.isna(max_val_len):
                            max_val_len = 0

                        header_len = len(str(column_title))
                        final_width = max(float(max_val_len), float(header_len)) + 3

                        worksheet.column_dimensions[
                            get_column_letter(col_num)
                        ].width = min(final_width, 60)
                    except:
                        worksheet.column_dimensions[
                            get_column_letter(col_num)
                        ].width = 20

                # --- PROCESAR DATOS ---
                # Limitamos el procesamiento de estilos si el dataset es masivo para evitar timeouts
                max_styled_rows = 5000
                rows_to_process = min(len(df), max_styled_rows)

                for row_num in range(2, rows_to_process + 2):
                    is_zebra = row_num % 2 == 0
                    for col_num in range(1, len(df.columns) + 1):
                        cell = worksheet.cell(row=row_num, column=col_num)
                        cell.border = thin_border
                        cell.alignment = align_left
                        cell.font = data_font
                        if is_zebra:
                            cell.fill = zebra_fill

                # Congelar paneles
                worksheet.freeze_panes = "B2"

            output.seek(0)
            file_data = output.read()

            if not file_data:
                raise ValueError("El archivo generado está vacío.")

            # Preparar la respuesta HTTP
            response = HttpResponse(
                file_data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            return response

        except Exception:
            logger.exception("Fallo crítico al generar Excel")
            return Response(
                {"error": "Fallo crítico al generar Excel"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlantillaVacantesPorNivelView(APIView):
    permission_classes = [IsAuthenticated]

    # Devuelve el resumen de las posiciones ocupadas y vacantes por nivel
    def get(self, request):
        cache_key = "plantilla_vacantes_por_nivel"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        active_position_codes = obtener_posiciones_activas()

        resultados = list(
            EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)
            .values("nivel")
            .annotate(
                Activo=Count("estado_nomina", filter=Q(estado_nomina="Activo")),
                Vacante=Count("estado_nomina", filter=Q(estado_nomina="Vacante")),
                Suspendido=Count("estado_nomina", filter=Q(estado_nomina="Suspendido")),
                Permiso_Retribuido=Count(
                    "estado_nomina", filter=Q(estado_nomina="Permiso Retribuido")
                ),
                Permiso=Count("estado_nomina", filter=Q(estado_nomina="Permiso")),
            )
            .order_by("nivel")
        )
        cache.set(cache_key, resultados, 1200)
        return Response(resultados, status=status.HTTP_200_OK)


class PlantillaVacantesPorNivelResumenView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def obtener_resumen_dinamico():
        cache_key = "plantilla_vacantes_por_nivel_resumen"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        active_position_codes = obtener_posiciones_activas()

        base_qs = EmpleadosCompletosSig.objects.filter(
            posicion__in=active_position_codes
        ).exclude(Q(estado_nomina__isnull=True) | Q(estado_nomina="Estado Nomina"))

        estados_unicos = base_qs.values_list("estado_nomina", flat=True).distinct()

        # total_niveles: Conteo de niveles distintos
        # total_registros: Conteo total de filas válidas
        agregaciones = {
            "total_niveles": Count("nivel", distinct=True),
            "total_registros": Count("*"),
        }

        # 3. Iteramos sobre los estados para crear el equivalente al SUM(CASE...)
        for estado in estados_unicos:
            # Usamos el nombre del estado con la primera letra en mayúscula y sin espacios
            # para ser consistentes con la otra vista y evitar colisiones con campos del modelo (que son minúsculas)
            llave = estado.replace(" ", "_")

            agregaciones[llave] = Sum(
                Case(
                    When(estado_nomina=estado, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            )

        # 4. Ejecutamos la consulta pasándole el diccionario desempaquetado (**agregaciones)
        resultado = base_qs.aggregate(**agregaciones)
        cache.set(cache_key, resultado, 1200)

        return resultado

    def get(self, request, *args, **kwargs):
        try:
            datos = self.obtener_resumen_dinamico()
            return Response(datos, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosCompletosEstatusNominaResumenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = "empleados_completos_estatus_resumen"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()
            total_registros = len(active_position_codes)

            # 2. Agrupar EmpleadosCompletosSig en posiciones activas por estado_nomina
            conteo_raw = (
                EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)
                .values("estado_nomina")
                .annotate(total=Count("pk"))
            )

            resumen = {
                "total_registros": total_registros,
                "Activo": 0,
                "Vacante": 0,
                "Suspendido": 0,
                "Licencia": 0,
                "Licencia_Medica": 0,
            }

            for item in conteo_raw:
                estado = item.get("estado_nomina")
                total = item.get("total") or 0

                # Normalizar estados según el mapeo solicitado
                if not estado or estado.strip() == "":
                    label = "Vacante"
                else:
                    estado_upper = estado.strip().upper()
                    if estado_upper == "A":
                        label = "Activo"
                    elif estado_upper == "S":
                        label = "Suspendido"
                    elif estado_upper == "L":
                        label = "Licencia"
                    elif estado_upper == "P":
                        label = "Licencia_Medica"
                    else:
                        label = "Vacante"

                resumen[label] = resumen.get(label, 0) + total

            cache.set(cache_key, resumen, 1200)
            return Response(resumen, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosCompletosActivosDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")

        if oficio or nivel:
            cache_key = f"empleados_completos_activos_detalle_{oficio}_{nivel}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data, status=status.HTTP_200_OK)

            try:
                # Obtener posiciones de Plantilla1800Plazas que cumplan los filtros
                posiciones_qs = Plantilla1800Plazas.objects.all()
                if oficio:
                    if oficio == "(vacío)":
                        posiciones_qs = posiciones_qs.filter(
                            Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud="")
                        )
                    else:
                        posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
                if nivel:
                    posiciones_qs = posiciones_qs.filter(nivel=nivel)

                posiciones_list = list(posiciones_qs.values_list("posición", flat=True))

                # Filtrar EmpleadosCompletosSig
                queryset = EmpleadosCompletosSig.objects.filter(
                    posicion__in=posiciones_list
                )
                resultados = list(queryset.values())

                cache.set(cache_key, resultados, 300)
                return Response(resultados, status=status.HTTP_200_OK)
            except Exception:
                logger.exception("Error inesperado en {}".format(request.path))
                return Response(
                    {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        cache_key = "empleados_completos_activos_detalle"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener todos los registros de EMPLEADOS_COMPLETOS_SIG en esas posiciones
            queryset = EmpleadosCompletosSig.objects.filter(
                posicion__in=active_position_codes
            )

            # 3. Serializar directamente
            resultados = list(queryset.values())

            cache.set(cache_key, resultados, 1200)
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosPorNivelYEstatusView(APIView):
    """
    Retorna empleados filtrados por nivel y estado de nómina.
    Query params: nivel, estado_nomina
    Ejemplo: /api/empleados/?nivel=C1&estado_nomina=Activo
    """

    def get(self, request):
        nivel = request.query_params.get("nivel")
        estado_nomina = request.query_params.get("estado_nomina")

        if not nivel or not estado_nomina:
            return Response(
                {"error": "Los parámetros 'nivel' y 'estado_nomina' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Map full names back to letters for EmpleadosCompletosSig DB query
        estatus_map_reverse = {
            "Activo": "A",
            "Suspendido": "S",
            "Licencia": "L",
            "Licencia Médica": "P",
            "Vacante": "V",
        }
        db_estado_nomina = estatus_map_reverse.get(estado_nomina, estado_nomina)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener los registros de EMPLEADOS_COMPLETOS_SIG correspondientes al nivel y estatus
            base_qs = EmpleadosCompletosSig.objects.filter(
                posicion__in=active_position_codes
            )

            if nivel == "SIN NIVEL":
                base_qs = base_qs.filter(Q(nivel__isnull=True) | Q(nivel__exact=""))
            else:
                base_qs = base_qs.filter(nivel=nivel)

            if estado_nomina == "Vacante":
                # La UI agrupa bajo "Vacante" todo lo que no sea A, S, L, P
                queryset = base_qs.exclude(
                    estado_nomina__in=["A", "a", "S", "s", "L", "l", "P", "p"]
                )
            else:
                queryset = base_qs.filter(estado_nomina__iexact=db_estado_nomina)

            return Response(
                {
                    "total": queryset.count(),
                    "resultados": list(queryset.values()),
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OcupacionPorOficiosResumenView(APIView):
    """
    Devuelve un resumen dinámico de ocupación por 'Of. De Solicitud' con desglose por Nivel.

    Usa Django ORM para construir dinámicamente el equivalente a la query SQL con ROLLUP.
    Las columnas se generan automáticamente según los valores únicos de Nivel encontrados.

    Retorna:
    {
        "filas": [
            {
                "Of. De Solicitud": "Oficina A",
                "A212": 5,
                "D312": 3,
                "(vacío)": 1,
                "Total Resultado": 11
            },
            ...
        ],
        "columnas": ["Of. De Solicitud", "A212", "D312", "(vacío)", "Total Resultado"],
        "total_general": 1857
    }
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def obtener_resumen_dinamico():
        """
        Construye dinámicamente el resumen usando Django ORM de forma optimizada en O(1) queries.
        Equivalente a la query SQL con GROUP BY ... WITH ROLLUP
        """

        # 1. Obtener los niveles únicos (DISTINCT)
        niveles_unicos = (
            Plantilla1800Plazas.objects.exclude(Q(nivel__isnull=True) | Q(nivel=""))
            .values_list("nivel", flat=True)
            .distinct()
            .order_by("nivel")
        )
        niveles = list(niveles_unicos)

        # 2. Hacer una consulta agrupada para obtener los conteos totales de oficina y nivel
        conteo_agrupado = (
            Plantilla1800Plazas.objects.values("of_de_solicitud", "nivel")
            .annotate(cantidad=Count("id"))
            .order_by("of_de_solicitud", "nivel")
        )

        # 3. Procesar en memoria en Python los totales
        data_dict = {}
        for item in conteo_agrupado:
            oficina = item["of_de_solicitud"] or "(vacío)"
            nivel = item["nivel"]
            if not nivel:
                nivel = "(vacío)"
            cantidad = item["cantidad"]

            if oficina not in data_dict:
                data_dict[oficina] = {}
            data_dict[oficina][nivel] = data_dict[oficina].get(nivel, 0) + cantidad

        # 4. Obtener los conteos de ocupados agrupados
        conteo_ocupado = (
            Plantilla1800Plazas.objects.exclude(
                Q(rfc__isnull=True)
                | Q(rfc="")
                | Q(curp__isnull=True)
                | Q(curp="")
                | Q(num_empleado__isnull=True)
                | Q(num_empleado="")
                | Q(nombres__isnull=True)
                | Q(nombres="")
            )
            .values("of_de_solicitud", "nivel")
            .annotate(cantidad=Count("id"))
            .order_by("of_de_solicitud", "nivel")
        )

        ocupadas_dict = {}
        for item in conteo_ocupado:
            oficina = item["of_de_solicitud"] or "(vacío)"
            nivel = item["nivel"]
            if not nivel:
                nivel = "(vacío)"
            cantidad = item["cantidad"]

            if oficina not in ocupadas_dict:
                ocupadas_dict[oficina] = {}
            ocupadas_dict[oficina][nivel] = (
                ocupadas_dict[oficina].get(nivel, 0) + cantidad
            )

        # 5. Construir las filas
        filas = []
        totales_generales = {nivel: 0 for nivel in niveles}
        totales_generales["(vacío)"] = 0

        totales_ocupados_generales = {nivel: 0 for nivel in niveles}
        totales_ocupados_generales["(vacío)"] = 0

        total_gral = 0
        total_ocupadas_gral = 0

        # Ordenar oficinas
        oficinas_ordenadas = sorted(
            list(data_dict.keys()), key=lambda x: (x == "(vacío)", x)
        )

        for oficina in oficinas_ordenadas:
            conteos_nivel = data_dict[oficina]
            total_oficina = sum(conteos_nivel.values())

            ocupadas_oficina = ocupadas_dict.get(oficina, {})
            total_ocupadas_oficina = sum(ocupadas_oficina.values())

            fila = {"Of. De Solicitud": oficina}

            for nivel in niveles:
                count_nivel = conteos_nivel.get(nivel, 0)
                fila[nivel] = count_nivel
                totales_generales[nivel] += count_nivel

                count_ocupadas = ocupadas_oficina.get(nivel, 0)
                fila[f"ocupadas_{nivel}"] = count_ocupadas
                totales_ocupados_generales[nivel] += count_ocupadas

            # Nivel vacío en esta oficina
            count_vacio = conteos_nivel.get("(vacío)", 0)
            fila["(vacío)"] = count_vacio
            totales_generales["(vacío)"] += count_vacio

            count_ocupadas_vacio = ocupadas_oficina.get("(vacío)", 0)
            fila["ocupadas_(vacío)"] = count_ocupadas_vacio
            totales_ocupados_generales["(vacío)"] += count_ocupadas_vacio

            fila["Total Resultado"] = total_oficina
            fila["ocupadas_Total Resultado"] = total_ocupadas_oficina

            total_gral += total_oficina
            total_ocupadas_gral += total_ocupadas_oficina

            filas.append(fila)

        # 6. Agregar fila de totales (equivalente a ROLLUP)
        fila_total = {"Of. De Solicitud": "Total Resultado"}
        for nivel in niveles:
            fila_total[nivel] = totales_generales[nivel]
            fila_total[f"ocupadas_{nivel}"] = totales_ocupados_generales[nivel]

        fila_total["(vacío)"] = totales_generales["(vacío)"]
        fila_total["ocupadas_(vacío)"] = totales_ocupados_generales["(vacío)"]

        fila_total["Total Resultado"] = total_gral
        fila_total["ocupadas_Total Resultado"] = total_ocupadas_gral

        filas.append(fila_total)

        # 7. Definir columnas en el orden correcto
        columnas = ["Of. De Solicitud"] + niveles + ["(vacío)", "Total Resultado"]

        # 8. Conteo de posiciones ocupadas que inician con 2026
        ocupadas_2026 = (
            Plantilla1800Plazas.objects.filter(posición__startswith="2026")
            .exclude(rfc__isnull=True)
            .exclude(rfc__exact="")
            .exclude(curp__isnull=True)
            .exclude(curp__exact="")
            .exclude(num_empleado__isnull=True)
            .exclude(num_empleado__exact="")
            .exclude(nombres__isnull=True)
            .exclude(nombres__exact="")
            .count()
        )

        # 9. Conteo de empleados ocupados en EmpleadosCompletosSig que inician con 2026
        ocupadas_sig = EmpleadosCompletosSig.objects.filter(
            val_estat="Ocupada", posicion__startswith="2026"
        ).count()

        return {
            "filas": filas,
            "columnas": columnas,
            "total_general": Plantilla1800Plazas.objects.count(),
            "ocupadas_2026": ocupadas_2026,
            "ocupadas_sig": ocupadas_sig,
        }

    def get(self, request, *args, **kwargs):
        """
        GET /api/plantilla/ocupacion_por_oficios_resumen/

        Retorna el resumen dinámico de ocupación por oficios con desglose por nivel,
        construido usando Django ORM.
        """
        try:
            datos = self.obtener_resumen_dinamico()
            return Response(datos, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error al generar el resumen de ocupación por oficios")
            return Response(
                {"error": "Error al generar el resumen de ocupación por oficios"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RegistrosPorOficio1800PlazasView(APIView):
    """
    Devuelve los registros detallados del modelo Plantilla1800Plazas filtrados por 'Of. De Solicitud' y opcionalmente por 'Nivel'.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        no_oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")
        resumen = request.query_params.get("resumen") == "true"

        if not no_oficio and not nivel:
            return Response(
                {
                    "error": "No se especificó ningun filtro. Se requiere al menos 'oficio' o 'nivel' como parámetro de consulta."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Plantilla1800Plazas.objects.all()

        # Filtro dinámico por oficio
        if no_oficio:
            if no_oficio == "(vacío)":
                queryset = queryset.filter(
                    Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud="")
                )
            else:
                queryset = queryset.filter(of_de_solicitud=no_oficio)

        # Filtro dinámico por nivel
        if nivel:
            queryset = queryset.filter(nivel=nivel)

        if resumen:
            # Agrupamos por nivel y oficio, y contamos
            resultados = list(
                queryset.values("nivel", "of_de_solicitud")
                .annotate(total=Count("*"))
                .order_by("of_de_solicitud", "nivel")
            )
            total_registros = sum(r["total"] for r in resultados)
            total_count = len(resultados)
        else:
            # Traemos todos los campos (registros completos)
            resultados = list(queryset.order_by("nivel").values())
            total_registros = len(resultados)
            total_count = total_registros

        if not resultados:
            return Response(
                {
                    "mensaje": "No se encontraron registros con los filtros proporcionados."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Respuesta consolidada
        data = {
            "total_registros": total_registros,
            "resultados": resultados,
            "tipo_vista": "resumen" if resumen else "detallado",
        }
        if not resumen:
            data["total"] = total_count
        else:
            data["total_grupos"] = total_count

        if no_oficio:
            data["oficio"] = no_oficio
        if nivel:
            data["nivel"] = nivel

        return Response(data, status=status.HTTP_200_OK)


class Plantilla1800PlazasListView(APIView):
    """
    Vista para listar y actualizar registros de la plantilla de 1800 plazas.
    """

    permission_classes = [IsAuthenticated]

    CACHE_KEY = "plantilla_1800_list_json"

    def get(self, request):
        # El dataset cambia sólo en el sync de ZAFIRO o en PATCH. Servimos los
        # bytes JSON cacheados (orjson) para evitar re-consultar y re-serializar
        # ~12k filas en cada request.
        payload = cache.get(self.CACHE_KEY)
        if payload is None:
            resultados = list(
                Plantilla1800Plazas.objects.all().order_by("id").values()
            )
            payload = orjson_dumps(resultados)
            cache.set(self.CACHE_KEY, payload, 3600)
        return orjson_response(payload)

    def patch(self, request):
        """
        Actualización parcial de registros.
        Se espera un objeto con el ID y los campos a cambiar, o una lista de ellos.
        """
        data = request.data
        if not isinstance(data, list):
            data = [data]

        errores = []

        # Campos reales del modelo (no persistir atributos que no son columnas).
        valid_fields = {f.name for f in Plantilla1800Plazas._meta.get_fields()}

        # Normaliza los ids a int (la PK es entera) y reporta los inválidos.
        ids = []
        for item in data:
            rid = item.get("id")
            if rid in (None, ""):
                errores.append({"error": "ID no proporcionado", "item": item})
                continue
            try:
                ids.append(int(rid))
            except (TypeError, ValueError):
                errores.append(
                    {"error": f"Registro con ID {rid} no existe", "id": rid}
                )

        # 1 sola query para traer todos los registros (antes: 1 get por item).
        registros = Plantilla1800Plazas.objects.in_bulk(ids)

        a_actualizar = []
        campos = set()
        for item in data:
            rid = item.get("id")
            if rid in (None, ""):
                continue
            try:
                key = int(rid)
            except (TypeError, ValueError):
                continue
            registro = registros.get(key)
            if registro is None:
                errores.append(
                    {"error": f"Registro con ID {rid} no existe", "id": rid}
                )
                continue
            for field, value in item.items():
                if field != "id" and field in valid_fields:
                    setattr(registro, field, value)
                    campos.add(field)
            a_actualizar.append(registro)

        # 1 sola query (en lotes) para todas las actualizaciones
        # (antes: 1 save por item).
        if a_actualizar and campos:
            Plantilla1800Plazas.objects.bulk_update(
                a_actualizar, list(campos), batch_size=500
            )
        actualizados = len(a_actualizar)

        cache.delete(self.CACHE_KEY)
        return Response(
            {
                "mensaje": f"{actualizados} registros actualizados correctamente.",
                "errores": errores,
            },
            status=status.HTTP_200_OK if not errores else status.HTTP_207_MULTI_STATUS,
        )


class EmpleadosEstatusPorNivelUaView(APIView):
    """
    Vista para resumir el estatus de la nómina por nivel y por unidad administrativa (UA)
    de los empleados correspondientes a las posiciones activas.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = "empleados_estatus_por_nivel_ua"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener todos los registros de EMPLEADOS_COMPLETOS_SIG en esas posiciones
            active_employees = EmpleadosCompletosSig.objects.filter(
                posicion__in=active_position_codes
            )

            # 3. Agrupación por Nivel y Estado de Nómina
            nivel_data = active_employees.values("nivel", "estado_nomina").annotate(
                count=Count("id")
            )

            por_nivel = {}
            for item in nivel_data:
                nv = item["nivel"] or "SIN NIVEL"
                est = item["estado_nomina"] or "SIN ESTATUS"
                if nv not in por_nivel:
                    por_nivel[nv] = {}
                por_nivel[nv][est] = item["count"]

            # 4. Agrupación por Unidad Administrativa, Nivel y Estado de Nómina
            ua_data = active_employees.values(
                "unidad_administrativa", "nivel", "estado_nomina"
            ).annotate(count=Count("id"))

            por_ua = {}
            for item in ua_data:
                ua_name = item["unidad_administrativa"] or "SIN UA"
                nv = item["nivel"] or "SIN NIVEL"
                est = item["estado_nomina"] or "SIN ESTATUS"
                if ua_name not in por_ua:
                    por_ua[ua_name] = {}
                if nv not in por_ua[ua_name]:
                    por_ua[ua_name][nv] = {}
                por_ua[ua_name][nv][est] = item["count"]

            res_data = {"por_nivel": por_nivel, "por_ua": por_ua}
            cache.set(cache_key, res_data, 1200)
            return Response(res_data, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosDistribucionGeograficaView(APIView):
    """
    Retorna la distribución geográfica agrupada por coordenadas para los empleados activos.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = "empleados_distribucion_geografica"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            active_position_codes = obtener_posiciones_activas()

            # Agregacion en SQL: agrupa ~13k empleados por coordenada en la DB
            # (antes se iteraban todos en Python). GROUP_CONCAT(DISTINCT) trae los
            # valores unicos por grupo; el separador 0x1f evita choques con comas.
            with connection.cursor() as cursor:
                cursor.execute("SET SESSION group_concat_max_len = 1000000")

            grupos = (
                EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)
                .exclude(latitud__isnull=True)
                .exclude(latitud="")
                .exclude(longitud__isnull=True)
                .exclude(longitud="")
                .annotate(lat=Trim("latitud"), lng=Trim("longitud"))
                .values("lat", "lng")
                .annotate(
                    n=Count("id"),
                    descripciones=GroupConcat("descripcion_ubicacion"),
                    aduanas=GroupConcat("aduana"),
                    tipos=GroupConcat("tipo"),
                    uas=GroupConcat("unidad_administrativa"),
                )
            )

            def _split(s):
                return [x for x in (s.split("\x1f") if s else []) if x]

            resultados = []
            for g in grupos:
                lat, lng = g["lat"], g["lng"]
                if not lat or not lng:
                    continue
                try:
                    float(lat)
                    float(lng)
                except (ValueError, TypeError):
                    continue

                descripciones = _split(g["descripciones"])
                aduanas = _split(g["aduanas"])
                tipos = _split(g["tipos"])
                uas = _split(g["uas"])

                is_aduana = any(a.strip().upper().startswith("ADUANA") for a in aduanas)
                aduana_principal = next(
                    (a for a in aduanas if a.strip().upper().startswith("ADUANA")),
                    aduanas[0] if aduanas else "",
                )
                tipo_principal = tipos[0] if tipos else ""
                desc_principal = descripciones[0] if descripciones else ""

                nombre_principal = (
                    aduana_principal if (is_aduana and aduana_principal) else desc_principal
                )
                if not nombre_principal and descripciones:
                    nombre_principal = descripciones[0]

                resultados.append(
                    {
                        "latitud": float(lat),
                        "longitud": float(lng),
                        "nombre": nombre_principal or "Ubicación sin nombre",
                        "is_aduana": is_aduana,
                        "tipo": tipo_principal,
                        "count": g["n"],
                        "descripciones": descripciones,
                        "aduanas": aduanas,
                        "tipos": tipos,
                        "uas": uas,
                    }
                )

            cache.set(cache_key, resultados, 1200)
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_mov_pos_stats():
    cache_key = "mov_pos_card_stats"
    stats = cache.get(cache_key)
    if stats is None:
        from django.db import connection

        query = """
            SELECT
                (SELECT COUNT(*) FROM MOV_POS) as total_movimientos,
                COUNT(*) as todas_posiciones,
                SUM(CASE WHEN `Estado Psn` = 'A' THEN 1 ELSE 0 END) as posiciones_activas,
                SUM(CASE WHEN `Estado Psn` = 'I' THEN 1 ELSE 0 END) as posiciones_inactivas
            FROM MOV_POS_LATEST;
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    stats = {
                        "total_movimientos": int(row[0]) if row[0] is not None else 0,
                        "todas_posiciones": int(row[1]) if row[1] is not None else 0,
                        "posiciones_activas": int(row[2]) if row[2] is not None else 0,
                        "posiciones_inactivas": int(row[3])
                        if row[3] is not None
                        else 0,
                    }
                else:
                    stats = {
                        "total_movimientos": 0,
                        "todas_posiciones": 0,
                        "posiciones_activas": 0,
                        "posiciones_inactivas": 0,
                    }
        except Exception:
            stats = {
                "total_movimientos": 0,
                "todas_posiciones": 0,
                "posiciones_activas": 0,
                "posiciones_inactivas": 0,
            }
        cache.set(cache_key, stats, 600)  # Cache for 10 minutes
    return stats


class MovPosPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 10000

    def get_paginated_response(self, data):
        stats = get_mov_pos_stats()
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "count": self.page.paginator.count,
                "results": data,
                "stats": stats,
            }
        )


class MovPosDetalleView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = MovPosPagination

    def get(self, request, *args, **kwargs):
        from django.db import connection
        from django.db.models import Count, Q
        from django.db.models.functions import Trim

        from .models import MovPos, Plantilla1800Plazas

        queryset = MovPos.objects.all()

        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")

        if oficio or nivel:
            posiciones_qs = Plantilla1800Plazas.objects.all()
            if oficio:
                if oficio == "(vacío)":
                    posiciones_qs = posiciones_qs.filter(
                        Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud="")
                    )
                else:
                    posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
            if nivel:
                posiciones_qs = posiciones_qs.filter(nivel=nivel)

            # Subquery en lugar de materializar miles de posiciones en una lista
            # Python + un IN gigante (evita armar/transferir la lista y deja que
            # MySQL resuelva el filtro).
            queryset = queryset.filter(
                no_pos_actual__in=posiciones_qs.values("posición")
            )

        # is_latest filter (defaults to True unless explicitly requested as 'false')
        is_latest = request.query_params.get("is_latest", "true").lower() != "false"
        if is_latest:
            cache_key_latest = "latest_movpos_sub_ids"
            sub_ids = cache.get(cache_key_latest)
            if sub_ids is None:
                with connection.cursor() as cursor:
                    cursor.execute(LATEST_MOVPOS_RAW_SQL)
                    sub_ids = [row[0] for row in cursor.fetchall() if row[0]]
                cache.set(cache_key_latest, sub_ids, 600)  # Cache for 10 minutes
            queryset = queryset.filter(id__in=sub_ids)

        # Search query
        queryset = apply_text_search(
            queryset,
            request.query_params.get("search", ""),
            [
                "no_pos_actual",
                "motivo",
                "unidad_de_negocio",
                "unidad_adva",
                "puesto_ptal",
                "descr",
                "nombre_puesto",
            ],
        )

        # Dynamic Column Filters
        valid_fields = [f.name for f in MovPos._meta.get_fields()]
        text_fields = [
            f.name
            for f in MovPos._meta.get_fields()
            if f.get_internal_type() in ["CharField", "TextField"]
        ]

        queryset = apply_dynamic_column_filters(queryset, request, MovPos)

        # "ocupacion" is a computed column (not a real model field), so the
        # generic Dynamic Column Filters loop above silently skips it.
        # Apply it explicitly here, before pagination/sorting/distinct.
        # Covers both the dropdown (__in) and the free-text column filter
        # (__icontains/__istartswith/__iendswith/__iexact, incl. exclude__).
        ocupacion_param_key = None
        for k in request.query_params.keys():
            base = k[9:] if k.startswith("exclude__") else k
            if base == "ocupacion" or base.startswith("ocupacion__"):
                ocupacion_param_key = k
                break

        if ocupacion_param_key:
            cache_key_ocupadas = "mov_pos_ocupadas_set"
            posiciones_ocupadas = cache.get(cache_key_ocupadas)
            if posiciones_ocupadas is None:
                with connection.cursor() as cursor:
                    cursor.execute(OCUPADAS_RAW_SQL)
                    posiciones_ocupadas = set(
                        [row[0] for row in cursor.fetchall() if row[0]]
                    )
                cache.set(cache_key_ocupadas, posiciones_ocupadas, 600)

            ocupacion_raw = request.query_params.get(ocupacion_param_key, "")
            is_exclude = ocupacion_param_key.startswith("exclude__")
            suffix = (
                ocupacion_param_key.split("__", 1)[1]
                if "__"
                in (ocupacion_param_key[9:] if is_exclude else ocupacion_param_key)
                else "in"
            )

            if suffix == "in":
                selected_vals = set(
                    v.strip() for v in ocupacion_raw.split(",") if v.strip()
                )
            else:
                # Free-text condition: evaluate against the two possible values.
                needle = ocupacion_raw.strip().lower()
                candidates = ["Ocupada", "Vacante"]
                if suffix in ("icontains",):
                    selected_vals = {c for c in candidates if needle in c.lower()}
                elif suffix in ("istartswith",):
                    selected_vals = {
                        c for c in candidates if c.lower().startswith(needle)
                    }
                elif suffix in ("iendswith",):
                    selected_vals = {
                        c for c in candidates if c.lower().endswith(needle)
                    }
                elif suffix in ("iexact",):
                    selected_vals = {c for c in candidates if c.lower() == needle}
                else:
                    selected_vals = set(candidates)

            if is_exclude:
                selected_vals = {"Ocupada", "Vacante"} - selected_vals

            want_ocupada = "Ocupada" in selected_vals
            want_vacante = "Vacante" in selected_vals

            if want_ocupada and not want_vacante:
                queryset = queryset.filter(no_pos_actual__in=list(posiciones_ocupadas))
            elif want_vacante and not want_ocupada:
                queryset = queryset.exclude(no_pos_actual__in=list(posiciones_ocupadas))
            elif not want_ocupada and not want_vacante:
                queryset = queryset.none()

        # "total_movimientos" is also a computed column (count of historical
        # rows per posicion), so it needs the same explicit handling.
        total_mov_raw = request.query_params.get(
            "total_movimientos__in"
        ) or request.query_params.get("total_movimientos")
        if total_mov_raw:
            selected_counts = set()
            for v in total_mov_raw.split(","):
                v = v.strip()
                if v:
                    try:
                        selected_counts.add(int(v))
                    except ValueError:
                        pass
            if selected_counts:
                pos_list = list(
                    queryset.values_list("no_pos_actual", flat=True).distinct()
                )
                full_counts = dict(
                    MovPos.objects.filter(no_pos_actual__in=pos_list)
                    .values("no_pos_actual")
                    .annotate(c=Count("id"))
                    .values_list("no_pos_actual", "c")
                )
                match_pos = [p for p, c in full_counts.items() if c in selected_counts]
                queryset = queryset.filter(no_pos_actual__in=match_pos)
            else:
                queryset = queryset.none()

        # If distinct_field requested, return distinct values directly
        distinct_field = request.query_params.get("distinct_field", "").strip()

        # Special handling for computed columns not present in the model
        if distinct_field == "ocupacion":
            cache_key_ocupadas = "mov_pos_ocupadas_set"
            posiciones_ocupadas = cache.get(cache_key_ocupadas)
            if posiciones_ocupadas is None:
                with connection.cursor() as cursor:
                    cursor.execute(OCUPADAS_RAW_SQL)
                    posiciones_ocupadas = set(
                        [row[0] for row in cursor.fetchall() if row[0]]
                    )
                cache.set(cache_key_ocupadas, posiciones_ocupadas, 600)
            all_pos = list(queryset.values_list("no_pos_actual", flat=True))
            ocupadas = sum(1 for p in all_pos if p in posiciones_ocupadas)
            vacantes = len(all_pos) - ocupadas
            results = []
            if ocupadas > 0:
                results.append({"value": "Ocupada", "count": ocupadas})
            if vacantes > 0:
                results.append({"value": "Vacante", "count": vacantes})
            return Response(results)

        if distinct_field == "total_movimientos":
            pos_list = list(queryset.values_list("no_pos_actual", flat=True).distinct())
            if pos_list:
                full_counts = dict(
                    MovPos.objects.filter(no_pos_actual__in=pos_list)
                    .values("no_pos_actual")
                    .annotate(c=Count("id"))
                    .values_list("no_pos_actual", "c")
                )
                count_dist = {}
                for c in full_counts.values():
                    count_dist[c] = count_dist.get(c, 0) + 1
                results = [
                    {"value": str(k), "count": v} for k, v in sorted(count_dist.items())
                ]
            else:
                results = []
            return Response(results)

        if distinct_field in valid_fields:
            is_text = distinct_field in text_fields
            target_distinct_field = (
                f"trimmed_{distinct_field}" if is_text else distinct_field
            )
            if is_text and target_distinct_field not in queryset.query.annotations:
                queryset = queryset.annotate(
                    **{target_distinct_field: Trim(distinct_field)}
                )

            # Apply search filter on the distinct field if present
            distinct_search = request.query_params.get("distinct_search", "").strip()
            if distinct_search:
                if is_text:
                    queryset = queryset.filter(
                        **{f"{target_distinct_field}__icontains": distinct_search}
                    )
                else:
                    try:
                        queryset = queryset.filter(
                            **{target_distinct_field: distinct_search}
                        )
                    except (ValueError, exceptions.ValidationError):
                        queryset = queryset.none()

            distinct_qs = (
                queryset.values(target_distinct_field)
                .annotate(count=Count("*"))
                .order_by(target_distinct_field)
            )

            results = []
            for item in distinct_qs:
                val = item[target_distinct_field]
                results.append(
                    {"value": val if val is not None else "", "count": item["count"]}
                )
            return Response(results)

        # Advanced filters (built from the "Filtros Avanzados" modal).
        # "ocupacion" and "total_movimientos" are computed columns (not real
        # model fields), so apply_advanced_filters() needs this resolver to
        # handle them; everything else is generic (see apply_advanced_filters).
        def mov_pos_computed_resolver(column, condition, value):
            def get_posiciones_ocupadas():
                cache_key_ocupadas = "mov_pos_ocupadas_set"
                posiciones_ocupadas = cache.get(cache_key_ocupadas)
                if posiciones_ocupadas is None:
                    with connection.cursor() as cursor:
                        cursor.execute(OCUPADAS_RAW_SQL)
                        posiciones_ocupadas = set(
                            [row[0] for row in cursor.fetchall() if row[0]]
                        )
                    cache.set(cache_key_ocupadas, posiciones_ocupadas, 600)
                return posiciones_ocupadas

            def text_condition_matches(haystack, condition, needle):
                s = str(haystack).lower()
                n = str(needle).lower()
                if condition == "contains":
                    return n in s
                if condition == "not_contains":
                    return n not in s
                if condition == "starts_with":
                    return s.startswith(n)
                if condition == "not_starts_with":
                    return not s.startswith(n)
                if condition == "ends_with":
                    return s.endswith(n)
                if condition == "not_ends_with":
                    return not s.endswith(n)
                if condition == "equals":
                    return s == n
                if condition == "not_equals":
                    return s != n
                return False

            if column == "ocupacion":
                posiciones_ocupadas = get_posiciones_ocupadas()
                candidates = ["Ocupada", "Vacante"]
                selected = {
                    c for c in candidates if text_condition_matches(c, condition, value)
                }

                want_ocupada = "Ocupada" in selected
                want_vacante = "Vacante" in selected
                if want_ocupada and want_vacante:
                    return Q(no_pos_actual__isnull=False) | Q(no_pos_actual__isnull=True)
                if want_ocupada:
                    return Q(no_pos_actual__in=list(posiciones_ocupadas))
                if want_vacante:
                    return ~Q(no_pos_actual__in=list(posiciones_ocupadas))
                return Q(pk__in=[])

            if column == "total_movimientos":
                pos_list = list(
                    queryset.values_list("no_pos_actual", flat=True).distinct()
                )
                if not pos_list:
                    return Q(pk__in=[])
                full_counts = dict(
                    MovPos.objects.filter(no_pos_actual__in=pos_list)
                    .values("no_pos_actual")
                    .annotate(c=Count("id"))
                    .values_list("no_pos_actual", "c")
                )
                match_pos = [
                    p for p, c in full_counts.items()
                    if text_condition_matches(c, condition, value)
                ]
                if not match_pos:
                    return Q(pk__in=[])
                return Q(no_pos_actual__in=match_pos)

            return None

        queryset = apply_advanced_filters(
            queryset, request, MovPos, computed_resolver=mov_pos_computed_resolver
        )

        # Sorting
        sort_by_param = request.query_params.get("sort_by", "").strip()
        sort_order = request.query_params.get("sort_order", "desc").strip().lower()
        if sort_by_param:
            sort_fields = [f.strip() for f in sort_by_param.split(",")]
            order_by_args = []
            for field in sort_fields:
                if field in valid_fields:
                    is_text = field in text_fields
                    target_sort_field = f"trimmed_{field}" if is_text else field
                    if is_text and target_sort_field not in queryset.query.annotations:
                        queryset = queryset.annotate(**{target_sort_field: Trim(field)})
                    if sort_order == "desc":
                        order_by_args.append(f"-{target_sort_field}")
                    else:
                        order_by_args.append(target_sort_field)
            if order_by_args:
                queryset = queryset.order_by(*order_by_args)
            else:
                queryset = queryset.order_by(
                    "-f_efva", "-fecha_captura", "no_pos_actual"
                )
        else:
            # Default ordering requested by the user:
            # SELECT * FROM MOV_POS ORDERY BY fecha efectiva DESC, FECHA CAPTURA DESC, y ordenar tambien por posicion
            queryset = queryset.order_by("-f_efva", "-fecha_captura", "no_pos_actual")

        # Excel download or full list without pagination (bypass pagination if is_latest is true)
        no_pagination = (
            request.query_params.get("no_pagination", "false").strip().lower() == "true"
            or is_latest
        )
        if no_pagination:
            resultados = list(queryset.values())
            counts = dict(
                MovPos.objects.values_list("no_pos_actual").annotate(c=Count("id"))
            )

            cache_key_ocupadas = "mov_pos_ocupadas_set"
            posiciones_ocupadas = cache.get(cache_key_ocupadas)
            if posiciones_ocupadas is None:
                with connection.cursor() as cursor:
                    cursor.execute(OCUPADAS_RAW_SQL)
                    posiciones_ocupadas = set(
                        [row[0] for row in cursor.fetchall() if row[0]]
                    )
                cache.set(cache_key_ocupadas, posiciones_ocupadas, 600)

            populate_movpos_occupant_details(resultados, posiciones_ocupadas)
            for r in resultados:
                pos = r.get("no_pos_actual")
                r["total_movimientos"] = counts.get(pos, 1)
                r["estatus_ocupacion"] = (
                    "Ocupada" if pos in posiciones_ocupadas else "Vacante"
                )
                r["ocupacion"] = r["estatus_ocupacion"]
                r["fecha_vacancia"] = (
                    "" if pos in posiciones_ocupadas else r.get("fecha_vacancia", "")
                )

            is_excel_mode = (
                request.query_params.get("no_pagination", "false").strip().lower()
                == "true"
            )
            if not is_excel_mode:
                stats = get_mov_pos_stats()
                return Response(
                    {
                        "next": None,
                        "previous": None,
                        "count": len(resultados),
                        "results": resultados,
                        "stats": stats,
                    }
                )
            return Response(resultados)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset.values(), request, view=self)
        if page is not None:
            resultados = list(page)
            counts = dict(
                MovPos.objects.values_list("no_pos_actual").annotate(c=Count("id"))
            )

            cache_key_ocupadas = "mov_pos_ocupadas_set"
            posiciones_ocupadas = cache.get(cache_key_ocupadas)
            if posiciones_ocupadas is None:
                with connection.cursor() as cursor:
                    cursor.execute(OCUPADAS_RAW_SQL)
                    posiciones_ocupadas = set(
                        [row[0] for row in cursor.fetchall() if row[0]]
                    )
                cache.set(cache_key_ocupadas, posiciones_ocupadas, 600)

            populate_movpos_occupant_details(resultados, posiciones_ocupadas)
            for r in resultados:
                pos = r.get("no_pos_actual")
                r["total_movimientos"] = counts.get(pos, 1)
                r["estatus_ocupacion"] = (
                    "Ocupada" if pos in posiciones_ocupadas else "Vacante"
                )
                r["ocupacion"] = r["estatus_ocupacion"]
                r["fecha_vacancia"] = (
                    "" if pos in posiciones_ocupadas else r.get("fecha_vacancia", "")
                )
            return paginator.get_paginated_response(resultados)

        resultados = list(queryset.values())
        counts = dict(
            MovPos.objects.values_list("no_pos_actual").annotate(c=Count("id"))
        )

        cache_key_ocupadas = "mov_pos_ocupadas_set"
        posiciones_ocupadas = cache.get(cache_key_ocupadas)
        if posiciones_ocupadas is None:
            with connection.cursor() as cursor:
                cursor.execute(OCUPADAS_RAW_SQL)
                posiciones_ocupadas = set(
                    [row[0] for row in cursor.fetchall() if row[0]]
                )
            cache.set(cache_key_ocupadas, posiciones_ocupadas, 600)

        populate_movpos_occupant_details(resultados, posiciones_ocupadas)
        for r in resultados:
            pos = r.get("no_pos_actual")
            r["total_movimientos"] = counts.get(pos, 1)
            r["estatus_ocupacion"] = (
                "Ocupada" if pos in posiciones_ocupadas else "Vacante"
            )
            r["ocupacion"] = r["estatus_ocupacion"]
            r["fecha_vacancia"] = (
                "" if pos in posiciones_ocupadas else r.get("fecha_vacancia", "")
            )
        return Response(resultados)


class MovPosHistoriaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        posicion = request.query_params.get("posicion")
        if not posicion:
            return Response(
                {"error": "Parámetro 'posicion' es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Obtener todos los registros para la posición, ordenados del más reciente al más antiguo
            queryset = MovPos.objects.filter(no_pos_actual=posicion).order_by("-id")

            resultados = list(queryset.values())

            return Response(resultados, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MovPosVacanciaDetalleView(APIView):
    """
    Devuelve el detalle dinámico (por categoría de vacancia A/B/C) del
    registro decisivo que originó la fecha de vacancia de una posición.

    - Categoría A (baja): el registro decisivo vive en
      cp_tbl_mov_completo_29_05_26 y describe al empleado que causó la baja,
      el motivo, fecha efectiva y fecha de captura de esa baja.
    - Categoría B (cambio de posición): mismo origen de datos; la posición
      origen es la posición sobre la que se consulta y la posición destino
      es `posicion` del registro decisivo.
    - Categoría C (nunca ocupada): el registro decisivo vive en el propio
      MOV_POS y es el primer movimiento histórico de esa plaza.

    Parámetro: ?id=<id de MOV_POS> (el id del renglón de MOV_POS sobre el
    que se muestra la fecha de vacancia, NO el idRegistroDesicivo).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import CpTblMovCompleto290526

        mov_id = request.query_params.get("id")
        if not mov_id:
            return Response(
                {"error": "Parámetro 'id' es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            mov_row = MovPos.objects.get(id=mov_id)
        except (MovPos.DoesNotExist, ValueError):
            return Response(
                {"error": "Registro de MOV_POS no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        categoria = (mov_row.categoria_vacancia or "").strip().upper()
        id_decisivo = mov_row.id_registro_desicivo

        tuvo_insubsistencia = (mov_row.tuvo_insubsistencia or "").strip().upper()
        insubsistencia = None
        if tuvo_insubsistencia == "S" and mov_row.id_insubsistencia_detectada:
            try:
                reg_ins = CpTblMovCompleto290526.objects.get(
                    id=mov_row.id_insubsistencia_detectada
                )
                insubsistencia = {
                    "empleado": {
                        "num_empleado": reg_ins.num_empleado,
                        "nombre_completo": " ".join(
                            p for p in [reg_ins.nombre, reg_ins.ap_pat, reg_ins.ap_mat] if p
                        ).strip(),
                    },
                    "posicion": reg_ins.posicion,
                    "motivo": reg_ins.motivo,
                    "motivo_nombre": reg_ins.motivo_nombre,
                    "accion": reg_ins.accion,
                    "accion_nombre": reg_ins.accion_nombre,
                    "fecha_efectiva": reg_ins.fecha_efectiva,
                    "fecha_captura": reg_ins.fecha_captura,
                }
            except CpTblMovCompleto290526.DoesNotExist:
                insubsistencia = {
                    "error": "Registro de insubsistencia no encontrado en cp_tbl_mov_completo_29_05_26."
                }

        base = {
            "categoria_vacancia": categoria,
            "no_pos_actual": mov_row.no_pos_actual,
            "fecha_vacancia": mov_row.fecha_vacancia,
            "tuvo_insubsistencia": tuvo_insubsistencia,
            "insubsistencia": insubsistencia,
        }

        if not categoria or not id_decisivo:
            return Response(
                {**base, "error": "No hay registro decisivo asociado a esta vacancia."}
            )

        if categoria in ("A", "B"):
            try:
                registro = CpTblMovCompleto290526.objects.get(id=id_decisivo)
            except CpTblMovCompleto290526.DoesNotExist:
                return Response(
                    {
                        **base,
                        "error": "Registro decisivo no encontrado en cp_tbl_mov_completo_29_05_26.",
                    }
                )

            empleado_nombre = " ".join(
                p for p in [registro.nombre, registro.ap_pat, registro.ap_mat] if p
            ).strip()

            detalle = {
                **base,
                "empleado": {
                    "num_empleado": registro.num_empleado,
                    "nombre_completo": empleado_nombre,
                },
                "accion": registro.accion,
                "accion_nombre": registro.accion_nombre,
                "motivo": registro.motivo,
                "motivo_nombre": registro.motivo_nombre,
                "fecha_efectiva": registro.fecha_efectiva,
                "fecha_captura": registro.fecha_captura,
            }

            if categoria == "B":
                detalle["posicion_origen"] = mov_row.no_pos_actual
                detalle["posicion_destino"] = registro.posicion

            return Response(detalle)

        if categoria == "C":
            try:
                registro = MovPos.objects.get(id=id_decisivo)
            except MovPos.DoesNotExist:
                return Response(
                    {**base, "error": "Registro decisivo no encontrado en MOV_POS."}
                )

            detalle = {
                **base,
                "fecha_efectiva": registro.f_efva,
                "fecha_captura": registro.fecha_captura,
            }
            return Response(detalle)

        return Response(
            {**base, "error": f"Categoría de vacancia desconocida: {categoria}"}
        )


class MovPosExportExcelView(APIView):
    """Genera y descarga directamente el Excel de Movimientos de Posiciones
    con los filtros activos en el frontend. Evita que el cliente descargue
    todos los datos en JSON y ejecute ExcelJS localmente."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.db import connection as db_connection
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter

        # ── 1. Columnas visibles ────────────────────────────────────────────
        visible_raw = request.query_params.get("visible_columns", "").strip()
        if visible_raw:
            visible_keys = [k.strip() for k in visible_raw.split(",") if k.strip()]
        else:
            visible_keys = list(MOV_POS_COLUMN_LABELS.keys())

        # ── 2. Construir queryset con los mismos filtros que MovPosDetalleView ──
        queryset = MovPos.objects.all()

        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")
        if oficio or nivel:
            posiciones_qs = Plantilla1800Plazas.objects.all()
            if oficio:
                if oficio == "(vacío)":
                    posiciones_qs = posiciones_qs.filter(
                        Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud="")
                    )
                else:
                    posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
            if nivel:
                posiciones_qs = posiciones_qs.filter(nivel=nivel)
            queryset = queryset.filter(
                no_pos_actual__in=posiciones_qs.values("posición")
            )

        is_latest = request.query_params.get("is_latest", "true").lower() != "false"
        if is_latest:
            cache_key_latest = "latest_movpos_sub_ids"
            sub_ids = cache.get(cache_key_latest)
            if sub_ids is None:
                with db_connection.cursor() as cursor:
                    cursor.execute(LATEST_MOVPOS_RAW_SQL)
                    sub_ids = [row[0] for row in cursor.fetchall() if row[0]]
                cache.set(cache_key_latest, sub_ids, 600)
            queryset = queryset.filter(id__in=sub_ids)

        queryset = apply_text_search(
            queryset,
            request.query_params.get("search", ""),
            ["no_pos_actual", "motivo", "unidad_de_negocio", "unidad_adva",
             "puesto_ptal", "descr", "nombre_puesto"],
        )

        queryset = apply_dynamic_column_filters(queryset, request, MovPos)

        # ocupacion computed column
        ocupacion_param_key = None
        for k in request.query_params.keys():
            base = k[9:] if k.startswith("exclude__") else k
            if base == "ocupacion" or base.startswith("ocupacion__"):
                ocupacion_param_key = k
                break

        cache_key_ocupadas = "mov_pos_ocupadas_set"

        def _get_posiciones_ocupadas():
            pos_ocup = cache.get(cache_key_ocupadas)
            if pos_ocup is None:
                with db_connection.cursor() as cursor:
                    cursor.execute(OCUPADAS_RAW_SQL)
                    pos_ocup = set(row[0] for row in cursor.fetchall() if row[0])
                cache.set(cache_key_ocupadas, pos_ocup, 600)
            return pos_ocup

        is_vacantes_only = False
        if ocupacion_param_key:
            posiciones_ocupadas = _get_posiciones_ocupadas()
            ocupacion_raw = request.query_params.get(ocupacion_param_key, "")
            is_exclude = ocupacion_param_key.startswith("exclude__")
            suffix = (
                ocupacion_param_key.split("__", 1)[1]
                if "__" in (ocupacion_param_key[9:] if is_exclude else ocupacion_param_key)
                else "in"
            )
            if suffix == "in":
                selected_vals = set(v.strip() for v in ocupacion_raw.split(",") if v.strip())
            else:
                needle = ocupacion_raw.strip().lower()
                candidates = ["Ocupada", "Vacante"]
                if suffix in ("icontains",):
                    selected_vals = {c for c in candidates if needle in c.lower()}
                elif suffix in ("istartswith",):
                    selected_vals = {c for c in candidates if c.lower().startswith(needle)}
                elif suffix in ("iendswith",):
                    selected_vals = {c for c in candidates if c.lower().endswith(needle)}
                elif suffix in ("iexact",):
                    selected_vals = {c for c in candidates if c.lower() == needle}
                else:
                    selected_vals = set(candidates)
            if is_exclude:
                selected_vals = {"Ocupada", "Vacante"} - selected_vals
            want_ocupada = "Ocupada" in selected_vals
            want_vacante = "Vacante" in selected_vals
            if want_ocupada and not want_vacante:
                queryset = queryset.filter(no_pos_actual__in=list(posiciones_ocupadas))
            elif want_vacante and not want_ocupada:
                queryset = queryset.exclude(no_pos_actual__in=list(posiciones_ocupadas))
                is_vacantes_only = True
            elif not want_ocupada and not want_vacante:
                queryset = queryset.none()

        total_mov_raw = (
            request.query_params.get("total_movimientos__in")
            or request.query_params.get("total_movimientos")
        )
        if total_mov_raw:
            selected_counts = set()
            for v in total_mov_raw.split(","):
                v = v.strip()
                if v:
                    try:
                        selected_counts.add(int(v))
                    except ValueError:
                        pass
            if selected_counts:
                pos_list = list(queryset.values_list("no_pos_actual", flat=True).distinct())
                full_counts = dict(
                    MovPos.objects.filter(no_pos_actual__in=pos_list)
                    .values("no_pos_actual")
                    .annotate(c=Count("id"))
                    .values_list("no_pos_actual", "c")
                )
                match_pos = [p for p, c in full_counts.items() if c in selected_counts]
                queryset = queryset.filter(no_pos_actual__in=match_pos)
            else:
                queryset = queryset.none()

        # Advanced filters
        def _computed_resolver(column, condition, value):
            def _text_match(haystack, cond, needle):
                s, n = str(haystack).lower(), str(needle).lower()
                if cond == "contains": return n in s
                if cond == "not_contains": return n not in s
                if cond == "starts_with": return s.startswith(n)
                if cond == "not_starts_with": return not s.startswith(n)
                if cond == "ends_with": return s.endswith(n)
                if cond == "not_ends_with": return not s.endswith(n)
                if cond == "equals": return s == n
                if cond == "not_equals": return s != n
                return False

            if column == "ocupacion":
                pos_ocup = _get_posiciones_ocupadas()
                selected = {c for c in ["Ocupada", "Vacante"] if _text_match(c, condition, value)}
                want_o = "Ocupada" in selected
                want_v = "Vacante" in selected
                if want_o and want_v:
                    return Q(no_pos_actual__isnull=False) | Q(no_pos_actual__isnull=True)
                if want_o:
                    return Q(no_pos_actual__in=list(pos_ocup))
                if want_v:
                    return ~Q(no_pos_actual__in=list(pos_ocup))
                return Q(pk__in=[])
            if column == "total_movimientos":
                pos_list = list(queryset.values_list("no_pos_actual", flat=True).distinct())
                if not pos_list:
                    return Q(pk__in=[])
                full_counts = dict(
                    MovPos.objects.filter(no_pos_actual__in=pos_list)
                    .values("no_pos_actual")
                    .annotate(c=Count("id"))
                    .values_list("no_pos_actual", "c")
                )
                match_pos = [p for p, c in full_counts.items() if _text_match(c, condition, value)]
                return Q(no_pos_actual__in=match_pos) if match_pos else Q(pk__in=[])
            return None

        queryset = apply_advanced_filters(queryset, request, MovPos, computed_resolver=_computed_resolver)

        # Sorting
        valid_fields = [f.name for f in MovPos._meta.get_fields()]
        text_fields_set = {
            f.name for f in MovPos._meta.get_fields()
            if f.get_internal_type() in ("CharField", "TextField")
        }
        sort_by_param = request.query_params.get("sort_by", "").strip()
        sort_order = request.query_params.get("sort_order", "desc").strip().lower()
        if sort_by_param:
            sort_fields = [f.strip() for f in sort_by_param.split(",")]
            order_by_args = []
            for field in sort_fields:
                if field in valid_fields:
                    is_text = field in text_fields_set
                    target_sort_field = f"trimmed_{field}" if is_text else field
                    if is_text and target_sort_field not in queryset.query.annotations:
                        queryset = queryset.annotate(**{target_sort_field: Trim(field)})
                    order_by_args.append(f"-{target_sort_field}" if sort_order == "desc" else target_sort_field)
            if order_by_args:
                queryset = queryset.order_by(*order_by_args)
            else:
                queryset = queryset.order_by("-f_efva", "-fecha_captura", "no_pos_actual")
        else:
            queryset = queryset.order_by("-f_efva", "-fecha_captura", "no_pos_actual")

        # ── 3. Materializar datos ───────────────────────────────────────────
        resultados = list(queryset.values())
        counts = dict(MovPos.objects.values_list("no_pos_actual").annotate(c=Count("id")))
        posiciones_ocupadas = _get_posiciones_ocupadas()
        for r in resultados:
            pos = r.get("no_pos_actual")
            r["total_movimientos"] = counts.get(pos, 1)
            r["ocupacion"] = "Ocupada" if pos in posiciones_ocupadas else "Vacante"
            r["fecha_vacancia"] = "" if pos in posiciones_ocupadas else r.get("fecha_vacancia", "")

        # Export de solo "Vacantes": desglosa el registro decisivo (baja o
        # traslado) y la insubsistencia de cada posición vacante en columnas
        # extra, insertadas junto a "Categoría Vacancia" y "Tuvo Insubsistencia"
        # aunque el usuario las haya ocultado en la UI de la tabla.
        if is_vacantes_only:
            _enrich_rows_with_vacancia_detalle(resultados)

            for anchor_key in ("fecha_vacancia", "categoria_vacancia", "tuvo_insubsistencia"):
                if anchor_key not in visible_keys:
                    visible_keys.append(anchor_key)

            def _insert_after(keys, anchor, new_keys):
                new_keys = [k for k in new_keys if k not in keys]
                if not new_keys:
                    return keys
                idx = keys.index(anchor) + 1
                return keys[:idx] + new_keys + keys[idx:]

            visible_keys = _insert_after(visible_keys, "categoria_vacancia", VACANCIA_DETALLE_CATEGORIA_KEYS)
            visible_keys = _insert_after(visible_keys, "tuvo_insubsistencia", VACANCIA_DETALLE_INSUBSISTENCIA_KEYS)

        # ── 4. Generar Excel ────────────────────────────────────────────────
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Movimientos_Posiciones"

            header_fill = PatternFill(start_color="FF2B4C7E", end_color="FF2B4C7E", fill_type="solid")
            zebra_fill = PatternFill(start_color="FFF4F7FA", end_color="FFF4F7FA", fill_type="solid")
            header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFFFF")
            data_font = Font(name="Segoe UI", size=9)
            gold_side = Side(style="thin", color="FFBC955C")
            gold_border = Border(left=gold_side, right=gold_side, top=gold_side, bottom=gold_side)
            align_center = Alignment(horizontal="center", vertical="center")
            align_left = Alignment(horizontal="left", vertical="center")

            # Export de solo "Vacantes": portada con leyenda de categorías +
            # conteos y grupos de columnas explicados, encima del header real.
            if is_vacantes_only:
                _write_vacancia_report_cover(ws, visible_keys, resultados)
            header_row = 9 if is_vacantes_only else 1
            data_start_row = header_row + 1

            # Header row
            for col_idx, key in enumerate(visible_keys, start=1):
                label = MOV_POS_COLUMN_LABELS.get(key) or VACANCIA_DETALLE_COLUMN_LABELS.get(key, key)
                cell = ws.cell(row=header_row, column=col_idx, value=label)
                cell.fill = header_fill
                cell.font = header_font
                cell.border = gold_border
                cell.alignment = align_center
            ws.row_dimensions[header_row].height = 24

            # Data rows
            for row_idx, row_data in enumerate(resultados, start=data_start_row):
                is_zebra = (row_idx - data_start_row) % 2 == 1
                for col_idx, key in enumerate(visible_keys, start=1):
                    val = row_data.get(key)
                    if val is None:
                        val = ""
                    elif not isinstance(val, (int, float, bool)):
                        val = str(val)
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.font = data_font
                    cell.border = gold_border
                    cell.alignment = align_center if key in MOV_POS_MONO_COLUMNS else align_left
                    if is_zebra:
                        cell.fill = zebra_fill
                ws.row_dimensions[row_idx].height = 20

            # Auto-fit column widths (con piso extra para las columnas de
            # detalle de vacancia/insubsistencia, que en el export de Vacantes
            # también cargan el texto largo de la portada en las filas 1-8)
            for col_idx, key in enumerate(visible_keys, start=1):
                col_letter = get_column_letter(col_idx)
                header_len = len(MOV_POS_COLUMN_LABELS.get(key) or VACANCIA_DETALLE_COLUMN_LABELS.get(key, key))
                max_len = max(
                    (len(str(r.get(key, "") or "")) for r in resultados),
                    default=0,
                )
                width = min(max(max_len, header_len) + 4, 60)
                if is_vacantes_only:
                    width = max(width, VACANCIA_EXPORT_MIN_COL_WIDTH.get(key, 0))
                ws.column_dimensions[col_letter].width = width

            if is_vacantes_only:
                for col_letter in ("F", "G", "H"):
                    ws.column_dimensions[col_letter].width = max(
                        ws.column_dimensions[col_letter].width or 0,
                        VACANCIA_LEGEND_MIN_COL_WIDTH.get(col_letter, 0),
                    )

            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="Movimientos_Posiciones.xlsx"'
            return response

        except Exception:
            logger.exception("Error generando Excel de movimientos de posiciones")
            return Response(
                {"error": "Error generando Excel"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CadenaMandoView(APIView):
    """
    Vista para buscar la cadena de mando jerárquica (Bottom-Up) en EMPLEADOS_COMPLETOS_SIG.
    Busca por posición, nombre completo o número de empleado, y usa un CTE recursivo para subir la jerarquía.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"error": "Se requiere el parámetro 'q' para buscar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Buscar la posición base (la hoja/subordinado)
        base_employee = EmpleadosCompletosSig.objects.filter(
            Q(posicion=query) | Q(nombres__icontains=query) | Q(id_empleado=query)
        ).first()

        if not base_employee:
            return Response(
                {"error": f"No se encontró un empleado con el criterio '{query}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        base_posicion = base_employee.posicion

        # 2. Ejecutar CTE recursivo
        sql = """
            WITH RECURSIVE CadenaHaciaArriba AS (
                SELECT 
                    `Posición` AS Posicion,
                    `Nombres` AS Empleado,
                    `Nombre Puesto Funcional` AS Puesto_Funcional,
                    `Nivel` AS Nivel,
                    `DependenciaDirecta` AS Jefe_Directo,
                    1 AS Nivel_Hacia_Arriba
                FROM EMPLEADOS_COMPLETOS_SIG
                WHERE `Posición` = %s

                UNION ALL

                SELECT 
                    jefe.`Posición`,
                    jefe.`Nombres`,
                    jefe.`Nombre Puesto Funcional`,
                    jefe.`Nivel`,
                    jefe.`DependenciaDirecta`,
                    empleado.Nivel_Hacia_Arriba + 1
                FROM EMPLEADOS_COMPLETOS_SIG jefe
                INNER JOIN CadenaHaciaArriba empleado ON jefe.`Posición` = empleado.Jefe_Directo
                WHERE empleado.Jefe_Directo IS NOT NULL 
                  AND empleado.Jefe_Directo != '' 
                  AND empleado.Jefe_Directo != '0'
                  AND jefe.`Posición` != empleado.Posicion
            )
            SELECT 
                Posicion, Empleado, Puesto_Funcional, Nivel, Jefe_Directo, Nivel_Hacia_Arriba 
            FROM CadenaHaciaArriba 
            ORDER BY Nivel_Hacia_Arriba ASC;
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, [base_posicion])
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

                return Response(
                    {
                        "empleado_base": {
                            "posicion": base_employee.posicion,
                            "nombres": base_employee.nombres,
                            "puesto_funcional": base_employee.nombre_puesto_funcional
                            if hasattr(base_employee, "nombre_puesto_funcional")
                            else "",
                            "nivel": base_employee.nivel
                            if hasattr(base_employee, "nivel")
                            else "",
                        },
                        "cadena": results,
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from .models import ZafiroBitacora


class ZafiroBitacoraView(APIView):
    """
    Endpoint para obtener el historial de ejecuciones de ZAFIRO.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        logs = ZafiroBitacora.objects.all()[:limit]

        data = []
        for log in logs:
            data.append(
                {
                    "id": log.id,
                    "fecha_ejecucion": log.fecha_ejecucion.isoformat(),
                    "duracion_segundos": log.duracion_segundos,
                    "registros_posiciones": log.registros_posiciones,
                    "registros_completos": log.registros_completos,
                    "registros_bajas": log.registros_bajas,
                    "registros_historial": log.registros_historial,
                    "status": log.status,
                    "error_message": log.error_message,
                    "es_historico": log.es_historico,
                    "logs_en_vivo": log.logs_en_vivo,
                }
            )

        return Response(data, status=status.HTTP_200_OK)


class UltimaActualizacionZafiroView(APIView):
    """
    Endpoint público para obtener la fecha y estatus de la última actualización exitosa de ZAFIRO.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        last_success = (
            ZafiroBitacora.objects.filter(status="EXITO")
            .order_by("-fecha_ejecucion")
            .first()
        )
        if not last_success:
            last_success = (
                ZafiroBitacora.objects.filter(status="OK")
                .order_by("-fecha_ejecucion")
                .first()
            )
        if not last_success:
            last_success = ZafiroBitacora.objects.all().first()

        if last_success:
            from datetime import timedelta
            fecha_fin = last_success.fecha_ejecucion
            if last_success.duracion_segundos:
                fecha_fin += timedelta(seconds=last_success.duracion_segundos)

            return Response(
                {
                    "fecha": fecha_fin.isoformat(),
                    "status": last_success.status,
                },
                status=status.HTTP_200_OK,
            )

        return Response({"fecha": None, "status": None}, status=status.HTTP_200_OK)


class IniciarSincronizacionZafiroView(APIView):
    """
    Endpoint para arrancar manualmente la sincronización de ZAFIRO.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if ZafiroBitacora.objects.filter(status="RUNNING").exists():
            return Response(
                {"error": "Ya hay una sincronización en ejecución en este momento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import importar_zafiro

        importar_zafiro.delay()
        return Response(
            {"message": "Sincronización manual iniciada correctamente."},
            status=status.HTTP_200_OK,
        )


from django.views import View


class ZafiroSSEView(View):
    """
    Endpoint de Server-Sent Events (SSE) para notificar actualizaciones en tiempo real a clientes.
    """

    def get(self, request):
        import redis
        from django.http import StreamingHttpResponse

        def event_stream():
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            pubsub = r.pubsub()
            pubsub.subscribe("zafiro_updates")

            # Enviamos evento de inicialización de conexión
            yield "data: init\n\n"

            try:
                while True:
                    # Esperar mensajes en el canal de redis con timeout de 20s
                    message = pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=20.0
                    )
                    if message:
                        date_str = message["data"].decode("utf-8")
                        yield f"data: {date_str}\n\n"
                    else:
                        # Mantener conexión viva enviando pings
                        yield ": ping\n\n"
            except GeneratorExit:
                try:
                    pubsub.unsubscribe("zafiro_updates")
                    pubsub.close()
                except Exception:
                    pass

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        # GZipMiddleware bufferea internamente (zlib sin flush por chunk) y
        # retiene todos los mensajes hasta que la conexión se cierra,
        # rompiendo el streaming en tiempo real. Content-Encoding ya seteado
        # hace que GZipMiddleware.process_response la omita.
        response["Content-Encoding"] = "identity"
        return response


from .models import BajasSig


class BajasSigListView(APIView):
    """
    Endpoint para obtener todos los registros de bajas sin paginación.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")

        if oficio or nivel:
            cache_key = f"bajas_sig_list_{oficio}_{nivel}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data, status=status.HTTP_200_OK)

            try:
                # Obtener posiciones de Plantilla1800Plazas que cumplan los filtros
                posiciones_qs = Plantilla1800Plazas.objects.all()
                if oficio:
                    if oficio == "(vacío)":
                        posiciones_qs = posiciones_qs.filter(
                            Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud="")
                        )
                    else:
                        posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
                if nivel:
                    posiciones_qs = posiciones_qs.filter(nivel=nivel)

                posiciones_list = list(posiciones_qs.values_list("posición", flat=True))

                bajas = list(
                    BajasSig.objects.filter(posicion__in=posiciones_list).values()
                )
                cache.set(cache_key, bajas, 300)
                return Response(bajas, status=status.HTTP_200_OK)
            except Exception:
                logger.exception("Error inesperado en {}".format(request.path))
                return Response(
                    {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        cache_key = "bajas_sig_list"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        bajas = list(BajasSig.objects.all().values())
        cache.set(cache_key, bajas, 1200)
        return Response(bajas, status=status.HTTP_200_OK)


class BajasMotivosPieView(APIView):
    """
    Devuelve el conteo de bajas agrupado por Motivo para la gráfica de pastel.
    Respuesta: [{"motivo": "...", "total": N}, ...] ordenado por total descendente.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "bajas_motivos_pie"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        data = (
            BajasSig.objects.exclude(motivo_descr__isnull=True)
            .exclude(motivo_descr__exact="")
            .values("motivo_descr")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        result = [
            {"motivo": row["motivo_descr"], "total": row["total"]} for row in data
        ]
        cache.set(cache_key, result, 1200)
        return Response(result, status=status.HTTP_200_OK)


class BajasHistoricoView(APIView):
    """
    Devuelve la evolución histórica de bajas_sig obtenida de ZAFIRO_BITACORA.
    Agrupado por día (el registro más reciente de cada día donde registros_bajas > 0).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "bajas_historico"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        from .models import ZafiroBitacora

        queryset = ZafiroBitacora.objects.filter(registros_bajas__gt=0).order_by(
            "fecha_ejecucion"
        )
        bajas_por_dia = {}
        for r in queryset:
            bajas_por_dia[str(r.fecha_ejecucion.date())] = r.registros_bajas

        resultado = [
            {"fecha": fecha, "registros_bajas": count}
            for fecha, count in sorted(bajas_por_dia.items())
        ]
        cache.set(cache_key, resultado, 1200)
        return Response(resultado, status=status.HTTP_200_OK)


class ExportarEstatusExcelView(APIView):
    """
    Genera y exporta un archivo Excel (.xlsx) estructurado e interactivo.
    Si ya existe en caché para esa consulta exacta, lo retorna instantáneamente.
    Si no, lo genera de forma síncrona en el hilo de la petición y lo retorna.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.core.cache import cache
        from django.utils import timezone

        from plantilla.tasks import generar_excel_estatus_task

        uas_param = request.query_params.get("uas", "")
        levels_param = request.query_params.get("levels", "")
        group_by = request.query_params.get("group_by", "ua")

        # Consultar si ya existe el archivo Excel final generado en caché para esta consulta exacta
        import hashlib

        raw_key = f"excel_estatus_file_{uas_param}_{levels_param}_{group_by}"
        cache_key_excel = (
            f"excel_estatus_file_{hashlib.md5(raw_key.encode('utf-8')).hexdigest()}"
        )
        cached_excel_data = cache.get(cache_key_excel)
        if cached_excel_data is not None:
            filename = (
                f"Reporte_Plantilla_Estatus_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
            )
            response = HttpResponse(
                cached_excel_data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        try:
            # Ejecutar la generación de forma síncrona
            generar_excel_estatus_task.__wrapped__(uas_param, levels_param, group_by)
        except Exception:
            logger.exception("Error generando el reporte de Excel de estatus")
            return HttpResponse("Error generando el reporte de Excel", status=500)

        # Recuperar el archivo generado desde la caché
        file_data = cache.get(cache_key_excel)
        if not file_data:
            return HttpResponse(
                "Error: No se pudo recuperar el archivo generado de la caché.",
                status=500,
            )

        filename = (
            f"Reporte_Plantilla_Estatus_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
        )
        response = HttpResponse(
            file_data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class OrganigramaSearchView(APIView):
    """
    Busca sobre la tabla cruda ORGANIGRAMA_ANAM por descripcion_larga o departamento.
    Si no se envía query, retorna todo el catálogo (útil para caché en memoria).
    Retorna la unidad_negocio para que el frontend sepa qué JSON cargar.
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()

        with connection.cursor() as cursor:
            if not query:
                sql = """
                    SELECT departamento, descripcion_larga, unidad_negocio, nivel_direccion 
                    FROM ORGANIGRAMA_ANAM
                """
                cursor.execute(sql)
            else:
                sql = """
                    SELECT departamento, descripcion_larga, unidad_negocio, nivel_direccion 
                    FROM ORGANIGRAMA_ANAM 
                    WHERE descripcion_larga LIKE %s OR departamento LIKE %s
                    LIMIT 50
                """
                cursor.execute(sql, [f"%{query}%", f"%{query}%"])

            rows = cursor.fetchall()

        results = [
            {
                "departamento": r[0],
                "descripcion_larga": r[1],
                "unidad_negocio": r[2],
                "nivel_direccion": r[3],
            }
            for r in rows
        ]
        return Response(results)


class TorreCaballito3DView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db import connection

        query = """
            SELECT 
                e.`Descripción ubicación`,
                e.`Unidad Administrativa`,
                COUNT(*) as Total
            FROM EMPLEADOS_COMPLETOS_SIG e
            INNER JOIN MOV_POS_LATEST activas
                ON e.`Posición` = activas.`Nº Pos Actual` AND activas.`Estado Psn` = 'A'
            WHERE e.`Descripción ubicación` IS NOT NULL
              AND (
                  e.`Descripción ubicación` LIKE '%Caballito Reforma 10 P%'
                  OR e.`Descripción ubicación` LIKE '%Torre Caballito Reforma 10 P%'
              )
            GROUP BY e.`Descripción ubicación`, e.`Unidad Administrativa`
            ORDER BY e.`Descripción ubicación`, Total DESC;
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

        # Aggregate by floor
        floors_dict = {}
        for row in results:
            piso = row[0]
            ua = row[1] if row[1] else "No Asignada"
            count = row[2]

            if piso not in floors_dict:
                floors_dict[piso] = {"piso": piso, "count": 0, "uas": []}

            floors_dict[piso]["count"] += count
            floors_dict[piso]["uas"].append({"nombre": ua, "count": count})

        return Response(list(floors_dict.values()))


class TorreCaballitoEmpleadosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        piso = request.query_params.get("piso", None)
        ua = request.query_params.get("ua", None)

        if not piso:
            return Response({"error": "Falta el parametro piso"}, status=400)

        from django.db import connection

        if ua and ua.strip():
            query = """
                SELECT 
                    e.`Posición`,
                    e.`Numempleado`,
                    e.`Nombres`,
                    e.`Unidad Administrativa`,
                    e.`Descripción ubicación`,
                    e.`Estado Nómina`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN MOV_POS_LATEST activas
                    ON e.`Posición` = activas.`Nº Pos Actual` AND activas.`Estado Psn` = 'A'
                WHERE e.`Descripción ubicación` = %s 
                  AND e.`Unidad Administrativa` = %s
                ORDER BY e.`Nombres`;
            """
            params = [piso, ua]
        else:
            query = """
                SELECT 
                    e.`Posición`,
                    e.`Numempleado`,
                    e.`Nombres`,
                    e.`Unidad Administrativa`,
                    e.`Descripción ubicación`,
                    e.`Estado Nómina`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN MOV_POS_LATEST activas
                    ON e.`Posición` = activas.`Nº Pos Actual` AND activas.`Estado Psn` = 'A'
                WHERE e.`Descripción ubicación` = %s 
                ORDER BY e.`Nombres`;
            """
            params = [piso]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        data = []
        for row in results:
            raw_estatus = row[5]
            if not raw_estatus or str(raw_estatus).strip() == "":
                estatus = "Vacante"
            else:
                val = str(raw_estatus).strip().upper()
                if val == "A":
                    estatus = "Activo"
                elif val == "S":
                    estatus = "Suspendido"
                elif val == "L":
                    estatus = "Licencia"
                elif val == "P":
                    estatus = "Licencia Médica"
                else:
                    estatus = "Vacante"

            data.append(
                {
                    "posicion": row[0],
                    "num_empleado": row[1],
                    "nombre": row[2],
                    "ua": row[3],
                    "ubicacion": row[4],
                    "estado_nomina": estatus,
                }
            )

        return Response(data)


class TorreCaballitoSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q or len(q) < 3:
            return Response({"results": []})

        from django.db import connection

        query = """
            SELECT
                e.`Posición`,
                e.`Numempleado`,
                e.`Nombres`,
                e.`Unidad Administrativa`,
                e.`Descripción ubicación`
            FROM EMPLEADOS_COMPLETOS_SIG e
            INNER JOIN MOV_POS_LATEST activas
                ON e.`Posición` = activas.`Nº Pos Actual` AND activas.`Estado Psn` = 'A'
            WHERE e.`Descripción ubicación` IS NOT NULL
              AND (
                  e.`Descripción ubicación` LIKE '%%Caballito Reforma 10 P%%'
                  OR e.`Descripción ubicación` LIKE '%%Torre Caballito Reforma 10 P%%'
              )
              AND (e.`Nombres` LIKE %s OR e.`Numempleado` LIKE %s)
            LIMIT 20;
        """

        like_q = f"%{q}%"
        with connection.cursor() as cursor:
            cursor.execute(query, [like_q, like_q])
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Parse piso for frontend convenience
        import re

        for r in results:
            match = re.search(
                r"10\s*P(?:iso)?\s*(\d+)",
                r["Descripción ubicación"] or "",
                re.IGNORECASE,
            )
            if match:
                r["piso_num"] = match.group(1)
            else:
                r["piso_num"] = None

        return Response({"results": results})


from rest_framework.pagination import PageNumberPagination


class MovimientosPersonalPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 10000


class MovimientosPersonalListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = MovimientosPersonalPagination

    def get(self, request):
        from .models import CpTblMovCompleto290526
        from .serializers import CpTblMovCompleto290526Serializer

        queryset = CpTblMovCompleto290526.objects.all()

        # Check if requesting distinct values for a field
        distinct_field = request.query_params.get("distinct_field", "").strip()

        # Search query
        queryset = apply_text_search(
            queryset,
            request.query_params.get("search", ""),
            [
                "posicion",
                "num_empleado",
                "nombre",
                "ap_pat",
                "ap_mat",
                "accion_nombre",
                "motivo_nombre",
                "un_admin",
            ],
        )

        # Dynamic Column Filters
        valid_fields = [f.name for f in CpTblMovCompleto290526._meta.get_fields()]
        text_fields = [
            f.name
            for f in CpTblMovCompleto290526._meta.get_fields()
            if f.get_internal_type() in ["CharField", "TextField"]
        ]
        from django.db.models.functions import Trim

        queryset = apply_dynamic_column_filters(queryset, request, CpTblMovCompleto290526)

        # If distinct_field requested, return distinct values directly
        if distinct_field in valid_fields:
            is_text = distinct_field in text_fields
            target_distinct_field = (
                f"trimmed_{distinct_field}" if is_text else distinct_field
            )
            if is_text and target_distinct_field not in queryset.query.annotations:
                queryset = queryset.annotate(
                    **{target_distinct_field: Trim(distinct_field)}
                )

            # Apply search filter on the distinct field if present
            distinct_search = request.query_params.get("distinct_search", "").strip()
            if distinct_search:
                if is_text:
                    queryset = queryset.filter(
                        **{f"{target_distinct_field}__icontains": distinct_search}
                    )
                else:
                    try:
                        queryset = queryset.filter(
                            **{target_distinct_field: distinct_search}
                        )
                    except (ValueError, exceptions.ValidationError):
                        queryset = queryset.none()

            distinct_qs = (
                queryset.values(target_distinct_field)
                .annotate(count=Count("*"))
                .order_by(target_distinct_field)
            )

            results = []
            for item in distinct_qs:
                val = item[target_distinct_field]
                results.append(
                    {"value": val if val is not None else "", "count": item["count"]}
                )
            return Response(results)

        # Advanced filters (built from the "Filtros Avanzados" modal). No
        # computed columns here (unlike MovPosDetalleView), so no resolver needed.
        queryset = apply_advanced_filters(queryset, request, CpTblMovCompleto290526)

        # Sorting
        sort_by_param = request.query_params.get("sort_by", "").strip()
        sort_order = request.query_params.get("sort_order", "asc").strip().lower()
        if sort_by_param:
            sort_fields = [f.strip() for f in sort_by_param.split(",")]
            order_by_args = []
            for field in sort_fields:
                if field in valid_fields:
                    is_text = field in text_fields
                    target_sort_field = f"trimmed_{field}" if is_text else field
                    if is_text and target_sort_field not in queryset.query.annotations:
                        queryset = queryset.annotate(**{target_sort_field: Trim(field)})
                    if sort_order == "desc":
                        order_by_args.append(f"-{target_sort_field}")
                    else:
                        order_by_args.append(target_sort_field)
            if order_by_args:
                queryset = queryset.order_by(*order_by_args)
            else:
                queryset = queryset.order_by("-fecha_efectiva", "-sec")
        else:
            # Default ordering
            queryset = queryset.order_by("-fecha_efectiva", "-sec")

        # Excel download or full list without pagination
        no_pagination = (
            request.query_params.get("no_pagination", "false").strip().lower() == "true"
        )
        if no_pagination:
            serializer = CpTblMovCompleto290526Serializer(queryset, many=True)
            return Response(serializer.data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = CpTblMovCompleto290526Serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CpTblMovCompleto290526Serializer(queryset, many=True)
        return Response(serializer.data)


class OrganigramaDeptoView(APIView):
    """
    Catálogo departamento→descripcion_larga/nivel_direccion de ORGANIGRAMA_ANAM.
    Respuesta: [{"departamento": "00100000000", "descripcion_larga": "...", "nivel_direccion": "..."}, ...]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db import connection
        sql = """
            SELECT departamento, descripcion_larga, nivel_direccion
            FROM ORGANIGRAMA_ANAM
            ORDER BY departamento
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        return Response([
            {"departamento": r[0], "descripcion_larga": r[1], "nivel_direccion": r[2]}
            for r in rows
        ])


class OrganigramaTreeView(APIView):
    """
    Árbol jerárquico de ORGANIGRAMA_ANAM para una unidad_negocio, con la misma
    forma que los antiguos JSON estáticos (nodo raíz con `subordinados` anidados).
    Lógica de parentesco en organigrama_tree.build_tree.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .organigrama_tree import build_tree

        unidad_negocio = request.GET.get("unidad_negocio", "").strip()
        if not unidad_negocio:
            return Response({"error": "Falta el parámetro unidad_negocio"}, status=400)

        sql = """
            SELECT departamento, descripcion_larga, nivel_direccion, unidad_negocio,
                   unidad_administrativa, doaf, num_posicion_gerente, posicion_director
            FROM ORGANIGRAMA_ANAM
            WHERE unidad_negocio = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [unidad_negocio])
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not rows:
            return Response({"error": f"Sin datos para unidad_negocio={unidad_negocio}"}, status=404)

        tree = build_tree(rows)
        return Response(tree)


class OrganigramaPosicionInfoView(APIView):
    """
    Dado un número de plaza (posición), indica si está activa al día de hoy
    (según MOV_POS_LATEST, que ya trae la última fila por posición) y, de
    estarlo, el ocupante actual en EMPLEADOS_COMPLETOS_SIG.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db import connection

        posicion = request.GET.get("posicion", "").strip()
        if not posicion or posicion in ("(en blanco)",):
            return Response({"error": "Falta el parámetro posicion"}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM MOV_POS_LATEST WHERE `Nº Pos Actual` = %s AND `Estado Psn` = 'A'",
                [posicion],
            )
            activa = cursor.fetchone() is not None

        if not activa:
            return Response({"posicion": posicion, "activa": False})

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT `Nombres`, `Numempleado`, `Estado Nómina`
                FROM EMPLEADOS_COMPLETOS_SIG
                WHERE `Posición` = %s
                LIMIT 1
                """,
                [posicion],
            )
            row = cursor.fetchone()

        if not row or not str(row[2] or "").strip():
            return Response({"posicion": posicion, "activa": True, "vacante": True})

        nombre, num_empleado, estado_nomina = row
        return Response({
            "posicion": posicion,
            "activa": True,
            "vacante": False,
            "nombre": nombre,
            "num_empleado": num_empleado,
            "estado_nomina": estado_nomina,
        })


class AuditedViewSetMixin:
    """
    Llena `modificado_por` con el usuario autenticado en cada create/update.
    `fecha_modificacion` se autollena vía `auto_now=True` en el modelo.
    """

    def perform_create(self, serializer):
        serializer.save(modificado_por=self.request.user.username)

    def perform_update(self, serializer):
        serializer.save(modificado_por=self.request.user.username)


class CatAccionesViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD del catálogo cat_acciones (action→action_description/descripcion).
    El listado (GET) mantiene la misma forma que el APIView previo; los
    consumidores existentes (`useAccionesMotivosCatalog.js`) leen los campos
    por nombre y no se ven afectados por los campos extra (effective_status,
    modificado_por, fecha_modificacion).
    """
    queryset = CatAcciones.objects.all()
    serializer_class = CatAccionesSerializer


class CatAccionesMotivosViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD del catálogo cat_acciones_motivos (accion+cd_motivo→descripcion).
    """
    queryset = CatAccionesMotivos.objects.all()
    serializer_class = CatAccionesMotivosSerializer


class CatPtoFuncViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD del catálogo CAT_PTO_FUNC (Cd Pto Funcional → Nombre Puesto
    Funcional), usado por el SP `sp_llenar_nombre_puesto` tras cada
    importación de ZAFIRO.
    """
    queryset = CatPtoFunc.objects.all()
    serializer_class = CatPtoFuncSerializer


class RcCatCodPresupuestalViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD del catálogo rc_cat_cod_presupuestal (SMB/SMN/nivel jerárquico por
    código presupuestal + escala), usado por los SPs
    `sp_corregir_smb_smn_empleados` y `sp_llenar_niveles_vacios_pos_activas`.

    Pk compuesta (codigo_presupuestal, escala): las rutas de detalle llevan
    ambos valores como segmentos de URL en vez de un solo `pk`.
    """
    queryset = RcCatCodPresupuestal.objects.all()
    serializer_class = RcCatCodPresupuestalSerializer

    def get_object(self):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(
            self.get_queryset(),
            codigo_presupuestal=self.kwargs["codigo_presupuestal"],
            escala=self.kwargs["escala"],
        )
        self.check_object_permissions(self.request, obj)
        return obj


class CatNivelJerarquicoPlazaViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD + acciones en bloque del catálogo cat_nivel_jerarquico_plaza.

    La siembra/actualización de plazas desde MOV_POS (`nvl_direc_origen`) ya
    no es una acción manual: corre automáticamente en cada import ZAFIRO (ver
    `plantilla.tasks._sincronizar_plazas_nivel_jerarquico`), justo antes de
    reaplicar la prioridad. Se quitó el trigger manual porque dispararlo a
    mitad de ciclo (con MOV_POS ya sobreescrito por una prioridad
    `nivel_jerarquico` recién aplicada) contaminaba `nvl_direc_origen` con el
    propio override, en vez de con el dato original de ZAFIRO.

    - `bulk-assign`: asigna una misma descripción de nivel jerárquico (enum)
      a varias plazas seleccionadas desde el frontend.
    """
    queryset = CatNivelJerarquicoPlaza.objects.all()
    serializer_class = CatNivelJerarquicoPlazaSerializer
    lookup_value_regex = "[^/]+"

    def get_object(self):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(self.get_queryset(), plaza=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=["get"])
    def niveles(self, request):
        """Catálogo estático (NJ, descripción) para poblar el select del frontend."""
        return Response([
            {"descripcion_nivel_jerarquico": value, "label": label}
            for value, label in DESCRIPCION_NJ_CHOICES
        ])

    @action(detail=False, methods=["post"], url_path="bulk-assign")
    def bulk_assign(self, request):
        plazas = request.data.get("plazas") or []
        descripcion = request.data.get("descripcion_nivel_jerarquico")
        if not plazas or not isinstance(plazas, list):
            return Response({"detail": "Se requiere una lista no vacía de plazas."}, status=status.HTTP_400_BAD_REQUEST)
        if descripcion not in dict(DESCRIPCION_NJ_CHOICES):
            return Response({"detail": "descripcion_nivel_jerarquico inválido."}, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user.username
        actualizadas = 0
        with transaction.atomic():
            for plaza in plazas:
                obj, _ = CatNivelJerarquicoPlaza.objects.get_or_create(plaza=plaza)
                obj.descripcion_nivel_jerarquico = descripcion
                obj.modificado_por = usuario
                obj.save()
                actualizadas += 1
        return Response({"actualizadas": actualizadas})

    @action(detail=False, methods=["get"], url_path="prioridad")
    def prioridad(self, request):
        """Fuente de prioridad configurada actualmente (o null si no se ha fijado)."""
        config = NivelJerarquicoPrioridadConfig.objects.first()
        return Response({"fuente": config.fuente if config else None})

    @action(detail=False, methods=["post"], url_path="aplicar-prioridad")
    def aplicar_prioridad(self, request):
        """
        Fija qué columna manda como fuente de verdad del nivel jerárquico
        ("nivel_jerarquico" o "nvl_direc_origen") y de inmediato cruza
        cat_nivel_jerarquico_plaza contra MOV_POS y EMPLEADOS_COMPLETOS_SIG,
        sobreescribiendo sus columnas de nivel jerárquico donde la posición
        coincida. La misma fuente se reaplica automáticamente en cada import
        de ZAFIRO (esas dos tablas se truncan y recargan completas cada 30
        min, ver plantilla.tasks._reaplicar_prioridad_nivel_jerarquico).
        """
        fuente = request.data.get("fuente")
        if fuente not in ("nivel_jerarquico", "nvl_direc_origen"):
            return Response({"detail": "fuente inválida."}, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user.username
        with transaction.atomic():
            config, _ = NivelJerarquicoPrioridadConfig.objects.get_or_create(pk=1)
            config.fuente = fuente
            config.modificado_por = usuario
            config.save()
            stats = aplicar_prioridad_nivel_jerarquico(fuente)

        return Response({"fuente": fuente, **stats})


class MovimientosPersonalHistorialView(APIView):
    """
    Devuelve el historial completo (sin filtro de año) de los empleados indicados,
    ordenado por num_empleado, fecha_efectiva, sec ASC.
    Consulta directa a cp_tbl_mov_completo_29_05_26 via raw SQL.

    Usar POST con body {"num_empleado": [123, 456, 789]} para listas grandes
    (evita el límite de longitud de URL de un GET). Se mantiene ?num_empleado__in=
    por compatibilidad con clientes existentes.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw_param = request.query_params.get("num_empleado__in", "").strip()
        emp_ids = [e.strip() for e in raw_param.split(",") if e.strip()]
        return self._historial(emp_ids)

    def post(self, request):
        emp_ids = request.data.get("num_empleado", [])
        if isinstance(emp_ids, str):
            emp_ids = [e.strip() for e in emp_ids.split(",") if e.strip()]
        else:
            emp_ids = [str(e).strip() for e in emp_ids if str(e).strip()]
        return self._historial(emp_ids)

    def _historial(self, emp_ids):
        from django.db import connection

        if not emp_ids:
            return Response([])

        placeholders = ", ".join(["%s"] * len(emp_ids))
        sql = f"""
            SELECT
                id, posicion, num_empleado,
                nombre, ap_pat, ap_mat,
                accion, accion_nombre,
                motivo, motivo_nombre,
                fecha_efectiva, sec, fecha_captura,
                est_hr, estado_pago, partida_presup,
                un, un_admin,
                id_depto, depen_direc,
                plan_sal, grado, escala,
                puesto_ptal, nivel_tabular,
                gp_pago, prog_benef, sal_base,
                cd_puesto, ubicacion, id_estbl,
                salida_prevista, fecha_ult_actz, por,
                ult_inicio, fecha_inicial, gp_trabajo,
                grupo_cd_sal, antiguo_empr,
                rfc, curp, id_persona,
                desc_larga_p, nv_jerarquico, desc_larga_un,
                sexo, fecha_entrada, fecha_posicion
            FROM cp_tbl_mov_completo_29_05_26
            WHERE num_empleado IN ({placeholders})
            ORDER BY num_empleado ASC, fecha_efectiva ASC, sec ASC
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, emp_ids)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()

        results = []
        for row in rows:
            record = {}
            for i, col in enumerate(cols):
                val = row[i]
                if hasattr(val, "isoformat"):
                    val = val.isoformat()
                record[col] = val
            results.append(record)

        return Response(results)


class MovimientosPersonalStatsView(APIView):
    """
    Devuelve la estadística de movimientos de personal agrupado por accion_nombre y año.
    Respuesta: {
        "by_year": {
            "2026": [{"accion_nombre": "REINGRESO", "total": 10}, ...],
            ...
        },
        "all": [{"accion_nombre": "REINGRESO", "total": 150}, ...]
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        accion_nombre = request.query_params.get("accion_nombre")
        fecha_captura__in = request.query_params.get("fecha_captura__in")

        import hashlib

        from django.core.cache import cache

        cache_key_base = "movimientos_personal_stats"
        if accion_nombre:
            cache_key_base += f"_{accion_nombre}"
        if fecha_captura__in:
            cache_key_base += f"_fc_{fecha_captura__in}"

        name_hash = hashlib.md5(cache_key_base.encode("utf-8")).hexdigest()
        cache_key = f"mov_stats_{name_hash}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        from django.db.models import Count
        from django.db.models.functions import ExtractYear

        from .models import CpTblMovCompleto290526

        queryset = CpTblMovCompleto290526.objects

        if fecha_captura__in:
            val_list = [v.strip() for v in fecha_captura__in.split(",") if v.strip()]
            from django.db.models import Q

            q_objects = Q()
            for val in val_list:
                q_objects |= Q(fecha_captura__startswith=val)
            queryset = queryset.filter(q_objects)

        if accion_nombre:
            queryset = queryset.filter(accion_nombre=accion_nombre)
            group_field = "motivo_nombre"
        else:
            group_field = "accion_nombre"

        # Fetch stats grouped by year and group_field
        stats_by_year = (
            queryset.exclude(**{f"{group_field}__isnull": True})
            .exclude(**{f"{group_field}__exact": ""})
            .annotate(year=ExtractYear("fecha_efectiva"))
            .values("year", group_field)
            .annotate(total=Count("*"))
            .order_by("-year", "-total")
        )

        # Fetch stats for ALL years combined
        stats_all = (
            queryset.exclude(**{f"{group_field}__isnull": True})
            .exclude(**{f"{group_field}__exact": ""})
            .values(group_field)
            .annotate(total=Count("*"))
            .order_by("-total")
        )

        by_year_dict = {}
        for row in stats_by_year:
            year_val = row["year"]
            year_str = str(year_val) if year_val is not None else "Sin Año"
            if year_str not in by_year_dict:
                by_year_dict[year_str] = []
            by_year_dict[year_str].append(
                {group_field: row[group_field], "total": row["total"]}
            )

        all_list = [
            {group_field: row[group_field], "total": row["total"]} for row in stats_all
        ]

        result = {"by_year": by_year_dict, "all": all_list}

        cache.set(cache_key, result, 1200)
        return Response(result, status=status.HTTP_200_OK)


class CuadroVacanciaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            resultados = CuadroVacancia.objects.all().order_by("-fecha").values()
            return Response(list(resultados), status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DesgloseJerarquicoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.db import connection

        cache_key = "desglose_jerarquico"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        query = """
        SELECT
            e.NJ,
            e.`Nombre Puesto Funcional`,
            e.`Nivel`,
            e.`Posición`,
            e.`Unidad de Negocio`,
            e.`Cd UA`,
            COALESCE(u.nombre, e.`Cd UA`) AS `nombre_ua`,
            e.`Cd UN`,
            e.`Código Presupuestal`,
            e.`Escala`,
            e.`Partida`,
            e.`TIPO DE CONTRATACIÓN`,
            e.`Sindicato`,
            e.`Entidad Federativa`,
            e.`nombreNJ`,
            e.`Id Departamento`,
            e.`Departamento`
        FROM EMPLEADOS_COMPLETOS_SIG e
        INNER JOIN MOV_POS m
            ON e.`Posición` = m.`Nº Pos Actual`
        INNER JOIN MOV_POS_LATEST latest ON m.id = latest.id
        LEFT JOIN ua_unidadadministrativa u
            ON TRIM(e.`Cd UA`) = TRIM(u.codigo)
        WHERE m.`Estado Psn` = 'A'
          AND e.`Estado Nómina` = ' '
          AND m.`Nº Pos Actual` NOT LIKE '103L%%'
          AND m.`Nº Pos Actual` NOT LIKE '1039%%'
          AND m.`Partida Ptal` <> '11401';
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cache.set(cache_key, results, 1200)
            return Response(results, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DesgloseJerarquicoOcupadosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.db import connection

        cache_key = "desglose_jerarquico_ocupados"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        query = """
        SELECT
            e.NJ,
            e.`Nombre Puesto Funcional`,
            e.`Nivel`,
            e.`Posición`,
            e.`Unidad de Negocio`,
            e.`Cd UA`,
            COALESCE(u.nombre, e.`Cd UA`) AS `nombre_ua`,
            e.`Cd UN`,
            e.`Código Presupuestal`,
            e.`Escala`,
            e.`Partida`,
            e.`TIPO DE CONTRATACIÓN`,
            e.`Sindicato`,
            e.`Entidad Federativa`,
            e.`nombreNJ`,
            e.`Id Empleado`,
            e.`Nombres`,
            e.`RFC`,
            e.`CURP`
        FROM EMPLEADOS_COMPLETOS_SIG e
        INNER JOIN MOV_POS m
            ON e.`Posición` = m.`Nº Pos Actual`
        INNER JOIN MOV_POS_LATEST latest ON m.id = latest.id
        LEFT JOIN ua_unidadadministrativa u
            ON TRIM(e.`Cd UA`) = TRIM(u.codigo)
        WHERE m.`Estado Psn` = 'A'
          AND e.`Estado Nómina` <> ' '
          AND m.`Nº Pos Actual` NOT LIKE '103L%%'
          AND m.`Nº Pos Actual` NOT LIKE '1039%%'
          AND m.`Partida Ptal` <> '11401';
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cache.set(cache_key, results, 1200)
            return Response(results, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error inesperado en {}".format(request.path))
            return Response(
                {"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
