"""
Edición manual de celdas de EMPLEADOS_COMPLETOS_SIG vía CeldaOverride.

EMPLEADOS_COMPLETOS_SIG se trunca y recarga completa en cada `importar_zafiro`
(cada 30 min, ver tasks.py), así que cualquier UPDATE manual se perdería en la
siguiente corrida si no se registrara aparte. `registrar_y_aplicar_override_empleado`
guarda el cambio en CeldaOverride y lo aplica de inmediato sobre la tabla viva;
`aplicar_overrides_empleados_completos` lo reaplica tras cada import (mismo
patrón que `tasks._reaplicar_prioridad_nivel_jerarquico`).
"""

import hashlib
import json
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q

from .models import (
    CeldaOverride,
    COLUMNAS_QUINCENAL_VALIDAS,
    EmpleadosCompletosSig,
    EmpleadosCompletosSigBase,
    FECHA_ANUENCIA_CATEGORIAS_VALIDAS,
    MovPos,
    REPORTADA_CHOICES,
    TblColumnasPlantillaQuincenal,
)

TABLA_EMPLEADOS = "EMPLEADOS_COMPLETOS_SIG"

EDITABLE_COLUMNS_EMPLEADOS = {
    f.name
    for f in EmpleadosCompletosSigBase._meta.get_fields()
    if f.name not in ("id", "posicion")
}


def compute_clave_hash(clave_negocio: dict) -> str:
    return hashlib.sha256(
        json.dumps(clave_negocio, sort_keys=True).encode()
    ).hexdigest()


def registrar_y_aplicar_override_empleado(posicion, columna, valor_nuevo, usuario):
    """
    Registra la edición en CeldaOverride y la aplica de inmediato sobre
    EMPLEADOS_COMPLETOS_SIG, todo en una transacción:
      1. Valida que `columna` sea editable.
      2. Bloquea (select_for_update) y lee la fila viva para capturar
         `valor_original` (lo que se está a punto de sobreescribir, sea el
         dato original de ZAFIRO o un override previo ya aplicado).
      3. Si `valor_nuevo` es igual a `valor_original` (normalizando espacios
         y tratando None/"" como equivalentes), no hace nada y devuelve
         `None` — evita ruido en el historial (8.10 QA: entradas
         "(vacío) → (vacío)" o el mismo texto re-guardado con un espacio de
         más, registradas como cambio VIGENTE sin serlo).
      4. Desactiva el override activo previo de esa (tabla, clave, columna),
         si existe — se conserva, no se borra.
      5. Crea el nuevo CeldaOverride (activo=True).
      6. Ejecuta el UPDATE sobre EMPLEADOS_COMPLETOS_SIG.

    Lanza ValueError si la columna no es editable o la posición no existe.

    Nota: MySQL no soporta el UniqueConstraint condicional de CeldaOverride.Meta
    (Django emite W036 y no lo crea a nivel BD) — la unicidad de "un override
    activo por celda" se garantiza aquí por transacción + select_for_update
    sobre la fila de EMPLEADOS_COMPLETOS_SIG, que serializa ediciones
    concurrentes sobre la misma posición.
    """
    if columna not in EDITABLE_COLUMNS_EMPLEADOS:
        raise ValueError(f"Columna '{columna}' no es editable.")

    clave_negocio = {"posicion": posicion}
    clave_hash = compute_clave_hash(clave_negocio)

    with transaction.atomic():
        fila = (
            EmpleadosCompletosSig.objects.select_for_update()
            .filter(posicion=posicion)
            .first()
        )
        if fila is None:
            raise ValueError(
                f"Posición '{posicion}' no existe en EMPLEADOS_COMPLETOS_SIG."
            )

        valor_original = getattr(fila, columna)
        valor_original = None if valor_original is None else str(valor_original)
        valor_nuevo_str = None if valor_nuevo is None else str(valor_nuevo)

        if (valor_original or "").strip() == (valor_nuevo_str or "").strip():
            return None

        CeldaOverride.objects.filter(
            tabla=TABLA_EMPLEADOS,
            clave_negocio_hash=clave_hash,
            columna=columna,
            activo=True,
        ).update(activo=False)

        override = CeldaOverride.objects.create(
            tabla=TABLA_EMPLEADOS,
            clave_negocio=clave_negocio,
            clave_negocio_hash=clave_hash,
            columna=columna,
            valor_original=valor_original,
            valor_nuevo=valor_nuevo_str,
            usuario=usuario,
            activo=True,
        )

        EmpleadosCompletosSig.objects.filter(posicion=posicion).update(
            **{columna: valor_nuevo_str}
        )

    return override


def borrar_contenido_celda(posicion, columna):
    """
    Borra el contenido de una celda de EMPLEADOS_COMPLETOS_SIG: pone la
    columna en NULL sobre la fila viva y elimina (hard delete, no solo
    desactiva) todo el historial de CeldaOverride de esa celda, para que
    la próxima importación de ZAFIRO no reaplique un override viejo sobre
    una celda que el usuario borró explícitamente (ver
    `aplicar_overrides_empleados_completos`).

    Lanza ValueError si la columna no es editable o la posición no existe.
    """
    if columna not in EDITABLE_COLUMNS_EMPLEADOS:
        raise ValueError(f"Columna '{columna}' no es editable.")

    clave_negocio = {"posicion": posicion}
    clave_hash = compute_clave_hash(clave_negocio)

    with transaction.atomic():
        fila = (
            EmpleadosCompletosSig.objects.select_for_update()
            .filter(posicion=posicion)
            .first()
        )
        if fila is None:
            raise ValueError(
                f"Posición '{posicion}' no existe en EMPLEADOS_COMPLETOS_SIG."
            )

        CeldaOverride.objects.filter(
            tabla=TABLA_EMPLEADOS,
            clave_negocio_hash=clave_hash,
            columna=columna,
        ).delete()

        EmpleadosCompletosSig.objects.filter(posicion=posicion).update(
            **{columna: None}
        )


def notificar_cambio_celda(posicion, columna, valor_nuevo, usuario, fecha_modificacion):
    """
    Publica el cambio en el canal Redis "plantilla_celda_updates" para que
    CeldaUpdatesSSEView lo reenvíe a los clientes con el tab Detalle abierto
    (ver plantilla.views.CeldaUpdatesSSEView). Mismo patrón que el publish de
    "zafiro_updates" en tasks.importar_zafiro.
    """
    import redis as redis_lib

    r = redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)
    r.publish(
        "plantilla_celda_updates",
        json.dumps({
            "type": "cell_update",
            "posicion": posicion,
            "columna": columna,
            "valor_nuevo": valor_nuevo,
            "usuario": usuario.username,
            "usuario_nombre": usuario.get_full_name() or usuario.username,
            "fecha_modificacion": fecha_modificacion.isoformat() if fecha_modificacion else None,
        }),
    )


def aplicar_overrides_empleados_completos(bitacora=None):
    """
    Reaplica todos los overrides activos de EMPLEADOS_COMPLETOS_SIG sobre la
    tabla recién importada. No falla si una `posicion` ya no existe (baja,
    posición eliminada del CSV de ZAFIRO) — solo la cuenta como huérfana.
    """
    overrides = CeldaOverride.objects.filter(tabla=TABLA_EMPLEADOS, activo=True)
    aplicados, huerfanos = 0, 0
    with transaction.atomic():
        for ov in overrides:
            posicion = ov.clave_negocio.get("posicion")
            updated = EmpleadosCompletosSig.objects.filter(posicion=posicion).update(
                **{ov.columna: ov.valor_nuevo}
            )
            if updated:
                aplicados += 1
            else:
                huerfanos += 1
    return {"aplicados": aplicados, "huerfanos": huerfanos}


def serializar_override(override: CeldaOverride) -> dict:
    # `clave_negocio` usa "posicion" (EMPLEADOS_COMPLETOS_SIG, PLANTILLA_QUINCENAL)
    # o "no_pos_actual" (MOV_POS) según la tabla — mismo valor de posición en
    # ambos casos, solo cambia el nombre de la key (ver TABLA_MOV_POS más abajo).
    clave = override.clave_negocio or {}
    return {
        "id": override.id,
        "posicion": clave.get("posicion") or clave.get("no_pos_actual"),
        "columna": override.columna,
        "valor_original": override.valor_original,
        "valor_nuevo": override.valor_nuevo,
        "usuario": override.usuario.username,
        "usuario_nombre": override.usuario.get_full_name() or override.usuario.username,
        "fecha_modificacion": override.fecha_modificacion,
        "activo": override.activo,
    }


def obtener_historial_overrides_empleados(
    *, tabla=TABLA_EMPLEADOS, search=None, columna=None, posicion=None, activo=None, limit=100, offset=0
):
    """
    Historial completo (activo e inactivo) de ediciones manuales sobre
    EMPLEADOS_COMPLETOS_SIG (o, vía ``tabla``, sobre PLANTILLA_QUINCENAL/
    MOV_POS — ver EmpleadosCompletosCeldaHistorialView), para el modal
    "Historial de Cambios" del tab Detalle. Solo lectura — no reaplica ni
    modifica nada.

    ``tabla``: un valor de CeldaOverride.tabla, o una lista de varios (p.ej.
    Plantilla Detalle unifica EMPLEADOS_COMPLETOS_SIG + PLANTILLA_QUINCENAL +
    MOV_POS en una sola vista, ya que las 3 se editan desde ese mismo tab).

    ``posicion``: filtra por el hash de AMBAS variantes de clave de negocio
    ({"posicion": X} y {"no_pos_actual": X}) porque MOV_POS usa un nombre de
    key distinto para el mismo valor de posición (ver serializar_override).
    """
    tablas = [tabla] if isinstance(tabla, str) else list(tabla)
    qs = (
        CeldaOverride.objects.filter(tabla__in=tablas)
        .select_related("usuario")
        .order_by("-fecha_modificacion", "-id")
    )
    if columna:
        qs = qs.filter(columna=columna)
    if posicion:
        hashes = [
            compute_clave_hash({"posicion": posicion}),
            compute_clave_hash({"no_pos_actual": posicion}),
        ]
        qs = qs.filter(clave_negocio_hash__in=hashes)
    if activo is not None:
        qs = qs.filter(activo=activo)
    if search:
        qs = qs.filter(
            Q(columna__icontains=search)
            | Q(usuario__username__icontains=search)
            | Q(usuario__first_name__icontains=search)
            | Q(usuario__last_name__icontains=search)
            | Q(valor_nuevo__icontains=search)
            | Q(valor_original__icontains=search)
        )

    total = qs.count()
    resultados = list(qs[offset : offset + limit])
    return resultados, total


def obtener_estadisticas_overrides_empleados(tabla=TABLA_EMPLEADOS):
    """
    Métricas agregadas del historial completo (sin filtros) para el panel
    resumen del modal "Historial de Cambios". Ver ``tabla`` en
    ``obtener_historial_overrides_empleados``.
    """
    tablas = [tabla] if isinstance(tabla, str) else list(tabla)
    base = CeldaOverride.objects.filter(tabla__in=tablas)
    total_cambios = base.count()
    total_activos = base.filter(activo=True).count()
    total_posiciones = base.values("clave_negocio_hash").distinct().count()
    total_usuarios = base.values("usuario").distinct().count()

    top_columnas = list(
        base.values("columna")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    return {
        "total_cambios": total_cambios,
        "total_activos": total_activos,
        "total_sobrescritos": total_cambios - total_activos,
        "total_posiciones_afectadas": total_posiciones,
        "total_usuarios": total_usuarios,
        "columnas_mas_editadas": top_columnas,
    }


# ─────────────────────────────────────────────────────────────────────────
# MOV_POS · fecha_anuencia (override manual sobre un valor calculado, no
# sobre una columna física)
#
# Diferencia clave con el patrón de EMPLEADOS_COMPLETOS_SIG de arriba:
# `fecha_anuencia` NUNCA existe como columna real en MOV_POS — se calcula al
# vuelo en cada request (fecha_vacancia + 30 días, ver
# plantilla.views.annotate_fecha_anuencia). Por eso aquí NO hay UPDATE sobre
# la tabla viva ni un job de "reaplicar tras cada import": el override se
# consulta directo desde CeldaOverride en cada consulta, así que basta con
# registrarlo/desactivarlo — sobrevive el truncado/recarga (blue-green swap,
# ver tasks._swap_blue_green_tables) de MOV_POS sin ningún trabajo extra,
# porque nunca dependió de esa tabla para persistir.
# ─────────────────────────────────────────────────────────────────────────

TABLA_MOV_POS = "MOV_POS"
COLUMNA_FECHA_ANUENCIA = "fecha_anuencia"


def _fecha_anuencia_baseline_excel(no_pos_actual):
    """
    Valor de "Fecha de Anuencia" cargado del Excel (columna AL,
    ``cargar_columnas_quincenal``) para esta posición, o ``None`` si el Excel
    no traía una fecha real para ella (la mayoría solo traen '-' o vacío —
    ``cargar_columnas_quincenal`` no crea fila en ese caso, ver ese comando).
    Consulta directa (no cacheada): se usa solo al registrar/recalcular un
    override individual, donde importa ver el estado más fresco posible.
    """
    return (
        TblColumnasPlantillaQuincenal.objects.filter(
            posicion=no_pos_actual, columna="fecha_anuencia_detalle"
        )
        .values_list("valor", flat=True)
        .first()
    )


def _fecha_anuencia_default(no_pos_actual):
    """Valor por default de `fecha_anuencia` cuando no hay override manual
    activo: prioridad al valor cargado del Excel (``_fecha_anuencia_baseline_excel``)
    y, si el Excel no trae fecha para esta posición, fecha_vacancia + 30 días
    (calculada en Python, para detectar "sin cambios reales" al registrar el
    primer override — mismo espíritu que la comparación de
    `registrar_y_aplicar_override_empleado`, solo que aquí no hay un valor
    "original" real que leer de una tabla física)."""
    baseline = _fecha_anuencia_baseline_excel(no_pos_actual)
    if baseline:
        return baseline

    row = MovPos.objects.filter(no_pos_actual=no_pos_actual).values("fecha_vacancia").first()
    fv = (row or {}).get("fecha_vacancia") or ""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fv):
        return None
    return (datetime.strptime(fv, "%Y-%m-%d").date() + timedelta(days=30)).isoformat()


def registrar_override_fecha_anuencia(no_pos_actual, valor_nuevo, usuario):
    """
    Registra (reemplazando cualquier override previo) la fecha de anuencia
    manual de una posición. No siempre es una fecha real: el Excel de origen
    trae, además de fechas, 4 categorías de texto fijo (ver
    FECHA_ANUENCIA_CATEGORIAS_VALIDAS) para posiciones donde aún no aplica
    una fecha — el usuario puede seguir editando con cualquiera de esas
    categorías o con una fecha 'YYYY-MM-DD' real, pero no con texto libre.

    Lanza ValueError si la posición no existe en MOV_POS o si `valor_nuevo`
    no es ni una fecha 'YYYY-MM-DD' válida ni una de las categorías fijas.
    Devuelve `None` (sin crear nada) si el valor coincide con el vigente —
    evita ruido en el historial (mismo criterio 8.10 QA que Empleados).
    """
    if not MovPos.objects.filter(no_pos_actual=no_pos_actual).exists():
        raise ValueError(f"La posición '{no_pos_actual}' no existe en MOV_POS.")

    valor_str = str(valor_nuevo).strip()
    if valor_str in FECHA_ANUENCIA_CATEGORIAS_VALIDAS:
        valor_nuevo_str = valor_str
    else:
        try:
            valor_nuevo_str = datetime.strptime(valor_str, "%Y-%m-%d").date().isoformat()
        except (TypeError, ValueError):
            raise ValueError(
                "La fecha debe tener el formato 'YYYY-MM-DD' o ser una de estas categorías: "
                f"{sorted(FECHA_ANUENCIA_CATEGORIAS_VALIDAS)}"
            )

    clave_negocio = {"no_pos_actual": no_pos_actual}
    clave_hash = compute_clave_hash(clave_negocio)

    with transaction.atomic():
        activo_previo = (
            CeldaOverride.objects.select_for_update()
            .filter(
                tabla=TABLA_MOV_POS,
                clave_negocio_hash=clave_hash,
                columna=COLUMNA_FECHA_ANUENCIA,
                activo=True,
            )
            .first()
        )
        valor_original = (
            activo_previo.valor_nuevo if activo_previo else _fecha_anuencia_default(no_pos_actual)
        )

        if valor_original == valor_nuevo_str:
            return None

        if activo_previo:
            activo_previo.activo = False
            activo_previo.save(update_fields=["activo"])

        override = CeldaOverride.objects.create(
            tabla=TABLA_MOV_POS,
            clave_negocio=clave_negocio,
            clave_negocio_hash=clave_hash,
            columna=COLUMNA_FECHA_ANUENCIA,
            valor_original=valor_original,
            valor_nuevo=valor_nuevo_str,
            usuario=usuario,
            activo=True,
        )

    return override


def borrar_override_fecha_anuencia(no_pos_actual):
    """
    Revierte al cálculo automático (fecha_vacancia + 30 días): desactiva el
    override activo de esa posición SIN borrar el historial. A diferencia de
    `borrar_contenido_celda` (que sí hace hard-delete porque si no,
    `aplicar_overrides_empleados_completos` reaplicaría el valor viejo tras
    el siguiente import): `fecha_anuencia` no tiene ese job de reaplicación,
    así que desactivar basta y conserva la auditoría completa.

    Devuelve `True` si había un override activo (y quedó desactivado), o
    `False` si la posición ya estaba en automático.
    """
    clave_hash = compute_clave_hash({"no_pos_actual": no_pos_actual})
    updated = CeldaOverride.objects.filter(
        tabla=TABLA_MOV_POS,
        clave_negocio_hash=clave_hash,
        columna=COLUMNA_FECHA_ANUENCIA,
        activo=True,
    ).update(activo=False)
    return updated > 0


def get_fecha_anuencia_overrides_map():
    """
    ``{no_pos_actual: date}`` de todos los overrides activos de
    `fecha_anuencia` QUE SON FECHA REAL — consumido por
    `plantilla.views.annotate_fecha_anuencia` (anotación SQL, ``DateField``)
    para dar prioridad a la fecha manual sobre el cálculo automático. Un
    override con una de las 4 categorías de texto fijo (ver
    ``get_fecha_anuencia_overrides_texto_map``) NO puede vivir en una
    anotación ``DateField``, así que aquí se omite — el texto se resuelve
    aparte, a nivel Python, en ``corregir_fecha_anuencia_row``. Query única y
    barata (tabla CeldaOverride es chica y solo unos pocos overrides estarán
    activos a la vez).
    """
    overrides = CeldaOverride.objects.filter(
        tabla=TABLA_MOV_POS, columna=COLUMNA_FECHA_ANUENCIA, activo=True
    ).values_list("clave_negocio", "valor_nuevo")

    mapa = {}
    for clave_negocio, valor_nuevo in overrides:
        pos = clave_negocio.get("no_pos_actual") if clave_negocio else None
        if not pos or not valor_nuevo:
            continue
        try:
            mapa[pos] = datetime.strptime(valor_nuevo, "%Y-%m-%d").date()
        except ValueError:
            continue
    return mapa


def get_fecha_anuencia_overrides_texto_map():
    """
    ``{no_pos_actual: str}`` de TODOS los overrides activos de
    `fecha_anuencia` (fecha real o categoría de texto fijo), sin descartar
    nada — usado por ``corregir_fecha_anuencia_row`` para pintar el texto tal
    cual cuando el override es una categoría (p.ej. "Nueva Creación") en vez
    de una fecha.
    """
    overrides = CeldaOverride.objects.filter(
        tabla=TABLA_MOV_POS, columna=COLUMNA_FECHA_ANUENCIA, activo=True
    ).values_list("clave_negocio", "valor_nuevo")

    mapa = {}
    for clave_negocio, valor_nuevo in overrides:
        pos = clave_negocio.get("no_pos_actual") if clave_negocio else None
        if pos and valor_nuevo:
            mapa[pos] = valor_nuevo
    return mapa


def get_fecha_anuencia_baseline_map():
    """
    ``{no_pos_actual: date}`` — valor de "Fecha de Anuencia" cargado del
    Excel QUE ES FECHA REAL (ver ``_fecha_anuencia_baseline_excel``), para
    TODAS las posiciones que tengan una. Versión bulk (una sola query), para
    usarse en listados completos (``annotate_fecha_anuencia`` en views.py,
    anotación SQL ``DateField``) en vez de una consulta por fila. Una de las
    4 categorías de texto fijo (ver ``get_fecha_anuencia_baseline_texto_map``)
    no puede vivir en un ``DateField`` y se omite aquí — se resuelve aparte,
    a nivel Python, en ``corregir_fecha_anuencia_row``. Prioridad de lectura
    completa: override manual > este baseline > cálculo automático
    (fecha_vacancia + 30 días).
    """
    rows = TblColumnasPlantillaQuincenal.objects.filter(
        columna="fecha_anuencia_detalle"
    ).values_list("posicion", "valor")

    mapa = {}
    for pos, valor in rows:
        if not pos or not valor:
            continue
        try:
            mapa[pos] = datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
    return mapa


def get_fecha_anuencia_baseline_texto_map():
    """
    ``{no_pos_actual: str}`` — valor CRUDO de "Fecha de Anuencia" cargado del
    Excel para TODAS las posiciones que tengan uno (fecha real o alguna de
    las 4 categorías de texto fijo) — respeta el contenido del Excel tal
    cual, sin descartar las categorías de texto. Usado por
    ``corregir_fecha_anuencia_row`` para pintar el texto cuando el baseline
    no es una fecha real.
    """
    return dict(
        TblColumnasPlantillaQuincenal.objects.filter(columna="fecha_anuencia_detalle")
        .exclude(valor="")
        .values_list("posicion", "valor")
    )


# ─────────────────────────────────────────────────────────────────────────
# PLANTILLA_QUINCENAL · columnas AL–AV editables (excepto fecha_anuencia_detalle,
# que se unificó arriba con el sistema de MOV_POS)
#
# Mismo patrón que `registrar_y_aplicar_override_empleado`, pero sin "tabla
# viva" que actualizar (no existe un campo físico en ninguna tabla de ZAFIRO
# para estas columnas — ver TblColumnasPlantillaQuincenal): el valor
# "original" a capturar es el valor EFECTIVO justo antes de este cambio
# (override activo previo si existe, si no el baseline cargado del Excel),
# y la lectura en cada request resuelve override > baseline > "" (ver
# `plantilla.views._get_mapa_quincenal`).
# ─────────────────────────────────────────────────────────────────────────

TABLA_QUINCENAL = "PLANTILLA_QUINCENAL"
COLUMNAS_QUINCENAL_EDITABLES = COLUMNAS_QUINCENAL_VALIDAS - {"fecha_anuencia_detalle"}


def registrar_y_aplicar_override_quincenal(posicion, columna, valor_nuevo, usuario):
    """
    Registra la edición manual de una columna quincenal (AL–AV, excepto
    fecha_anuencia_detalle) en CeldaOverride. No hay UPDATE sobre ninguna
    tabla viva (ver cabecera de esta sección) — el valor se resuelve en cada
    lectura vía `plantilla.views._get_mapa_quincenal`.

    Lanza ValueError si la columna no es editable o 'reportada' no es un
    valor válido. Devuelve `None` (sin crear nada) si el valor coincide con
    el vigente — mismo criterio 8.10 QA que el resto de overrides.
    """
    if columna not in COLUMNAS_QUINCENAL_EDITABLES:
        raise ValueError(f"Columna '{columna}' no es editable.")
    if columna == "reportada" and valor_nuevo not in ("", None, *REPORTADA_CHOICES):
        raise ValueError(f"'reportada' solo acepta: {REPORTADA_CHOICES}")

    clave_negocio = {"posicion": posicion}
    clave_hash = compute_clave_hash(clave_negocio)
    valor_nuevo_str = "" if valor_nuevo is None else str(valor_nuevo).strip()

    with transaction.atomic():
        activo_previo = (
            CeldaOverride.objects.select_for_update()
            .filter(tabla=TABLA_QUINCENAL, clave_negocio_hash=clave_hash, columna=columna, activo=True)
            .first()
        )
        valor_original = (
            activo_previo.valor_nuevo
            if activo_previo
            else TblColumnasPlantillaQuincenal.objects.filter(posicion=posicion, columna=columna)
            .values_list("valor", flat=True)
            .first()
        )
        valor_original = None if valor_original is None else str(valor_original)

        if (valor_original or "").strip() == valor_nuevo_str.strip():
            return None

        if activo_previo:
            activo_previo.activo = False
            activo_previo.save(update_fields=["activo"])

        override = CeldaOverride.objects.create(
            tabla=TABLA_QUINCENAL,
            clave_negocio=clave_negocio,
            clave_negocio_hash=clave_hash,
            columna=columna,
            valor_original=valor_original,
            valor_nuevo=valor_nuevo_str,
            usuario=usuario,
            activo=True,
        )

    return override


def borrar_override_quincenal(posicion, columna):
    """
    Revierte una columna quincenal al valor baseline del Excel (o a vacío si
    el Excel no traía nada): desactiva el override activo SIN borrar el
    historial (no hay job de reaplicado del cual protegerse — a diferencia
    de `borrar_contenido_celda` — así que basta desactivar, igual que
    `borrar_override_fecha_anuencia`).

    Devuelve `True` si había un override activo (y quedó desactivado), `False`
    si la posición ya estaba en su valor baseline.
    """
    if columna not in COLUMNAS_QUINCENAL_EDITABLES:
        raise ValueError(f"Columna '{columna}' no es editable.")
    clave_hash = compute_clave_hash({"posicion": posicion})
    updated = CeldaOverride.objects.filter(
        tabla=TABLA_QUINCENAL, clave_negocio_hash=clave_hash, columna=columna, activo=True
    ).update(activo=False)
    return updated > 0


def get_quincenal_overrides_map():
    """
    ``{posicion: {columna: valor_nuevo}}`` de todos los overrides ACTIVOS de
    columnas quincenal — se mergea sobre el baseline del Excel en
    `plantilla.views._get_mapa_quincenal` (override gana).
    """
    overrides = CeldaOverride.objects.filter(tabla=TABLA_QUINCENAL, activo=True).values_list(
        "clave_negocio", "columna", "valor_nuevo"
    )
    mapa = {}
    for clave_negocio, columna, valor_nuevo in overrides:
        pos = clave_negocio.get("posicion") if clave_negocio else None
        if not pos:
            continue
        mapa.setdefault(pos, {})[columna] = valor_nuevo or ""
    return mapa
