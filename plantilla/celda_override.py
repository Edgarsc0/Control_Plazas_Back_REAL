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

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q

from .models import CeldaOverride, EmpleadosCompletosSig, EmpleadosCompletosSigBase

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
    return {
        "id": override.id,
        "posicion": override.clave_negocio.get("posicion"),
        "columna": override.columna,
        "valor_original": override.valor_original,
        "valor_nuevo": override.valor_nuevo,
        "usuario": override.usuario.username,
        "usuario_nombre": override.usuario.get_full_name() or override.usuario.username,
        "fecha_modificacion": override.fecha_modificacion,
        "activo": override.activo,
    }


def obtener_historial_overrides_empleados(
    *, search=None, columna=None, posicion=None, activo=None, limit=100, offset=0
):
    """
    Historial completo (activo e inactivo) de ediciones manuales sobre
    EMPLEADOS_COMPLETOS_SIG, para el modal "Historial de Cambios" del tab
    Detalle. Solo lectura — no reaplica ni modifica nada.
    """
    qs = (
        CeldaOverride.objects.filter(tabla=TABLA_EMPLEADOS)
        .select_related("usuario")
        .order_by("-fecha_modificacion", "-id")
    )
    if columna:
        qs = qs.filter(columna=columna)
    if posicion:
        qs = qs.filter(clave_negocio_hash=compute_clave_hash({"posicion": posicion}))
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


def obtener_estadisticas_overrides_empleados():
    """
    Métricas agregadas del historial completo (sin filtros) para el panel
    resumen del modal "Historial de Cambios".
    """
    base = CeldaOverride.objects.filter(tabla=TABLA_EMPLEADOS)
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
