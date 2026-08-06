"""
Sincronización y cruce de cat_nivel_jerarquico_plaza contra MOV_POS y
EMPLEADOS_COMPLETOS_SIG.

Se usa desde:
  - `plantilla.tasks._sincronizar_plazas_nivel_jerarquico` (siembra/actualiza
    plazas desde MOV_POS en cada import ZAFIRO; sin trigger manual porque
    dispararlo a mitad de ciclo contamina `nvl_direc_origen` con un override
    de prioridad recién aplicado).
  - `CatNivelJerarquicoPlazaViewSet.aplicar_prioridad` (aplicación manual desde
    el checkbox de prioridad en el frontend) y
    `plantilla.tasks._reaplicar_prioridad_nivel_jerarquico` (reaplicación
    automática tras cada import ZAFIRO, porque esas dos tablas se truncan y
    recargan completas cada 30 min).
  - `CatNivelJerarquicoPlazaViewSet.bulk_assign` (propagación inmediata, vía
    `aplicar_nivel_a_plazas`, del nivel recién asignado a esas plazas
    puntuales — sin importar qué `fuente` esté configurada como prioridad;
    si luego corre un import ZAFIRO con `fuente=nvl_direc_origen`, ese
    import revierte el valor, igual que ya ocurría antes de este cambio).
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from .models import (
    CatNivelJerarquicoPlaza,
    EmpleadosCompletosSig,
    MovPos,
    MovPosLatest,
    NIVEL_3_PREFIJO_TITULAR_ADUANA,
    NIVEL_JERARQUICO_LABELS,
    NIVEL_JERARQUICO_LABELS_NIVEL_3_TITULAR_ADUANA,
)

logger = logging.getLogger(__name__)


def sincronizar_plazas_desde_mov_pos():
    """
    Siembra/actualiza cat_nivel_jerarquico_plaza desde las posiciones activas
    vigentes de MOV_POS (última captura por `Nº Pos Actual`, vía
    MOV_POS_LATEST): crea las plazas nuevas y refresca `nvl_direc_origen` en
    las existentes.

    Nunca toca `nivel_jerarquico` (asignación manual del usuario) ni borra
    filas de plazas que ya no aparecen activas: por eso, si una posición se da
    de baja y luego se reactiva, esta función vuelve a traerla y refresca su
    `nvl_direc_origen`, pero el `nivel_jerarquico` que el usuario le haya
    asignado antes se conserva intacto (la fila nunca dejó de existir en el
    catálogo).
    """
    latest_ids = MovPosLatest.objects.filter(estado_psn="A").values_list("mov_pos_id", flat=True)
    activas = list(MovPos.objects.filter(id__in=list(latest_ids)).exclude(
        no_pos_actual__isnull=True
    ).values_list("no_pos_actual", "nvl_direc"))

    # bulk_create/bulk_update en vez de loop create()/update() fila por fila:
    # con ~11k plazas activas el loop individual contra la BD remota tardaba
    # minutos (un round-trip de red por fila); en bloque son 1-2 queries.
    existentes = dict(CatNivelJerarquicoPlaza.objects.values_list("plaza", "nvl_direc_origen"))
    nuevas = [
        CatNivelJerarquicoPlaza(plaza=plaza, nvl_direc_origen=nvl_direc)
        for plaza, nvl_direc in activas if plaza not in existentes
    ]
    por_actualizar = []
    for plaza, nvl_direc in activas:
        if plaza in existentes and existentes[plaza] != nvl_direc:
            por_actualizar.append(CatNivelJerarquicoPlaza(plaza=plaza, nvl_direc_origen=nvl_direc))

    with transaction.atomic():
        if nuevas:
            CatNivelJerarquicoPlaza.objects.bulk_create(nuevas, batch_size=1000, ignore_conflicts=True)
        if por_actualizar:
            CatNivelJerarquicoPlaza.objects.bulk_update(por_actualizar, ["nvl_direc_origen"], batch_size=1000)

    return {"creadas": len(nuevas), "actualizadas": len(por_actualizar), "total_activas": len(activas)}


def _mapa_plaza_a_nivel(fuente):
    if fuente == "nivel_jerarquico":
        pares = CatNivelJerarquicoPlaza.objects.exclude(nivel_jerarquico__isnull=True).values_list(
            "plaza", "nivel_jerarquico"
        )
        return dict(pares)

    if fuente == "nvl_direc_origen":
        pares = CatNivelJerarquicoPlaza.objects.exclude(nvl_direc_origen__isnull=True).exclude(
            nvl_direc_origen=""
        ).values_list("plaza", "nvl_direc_origen")
        mapa = {}
        for plaza, raw in pares:
            try:
                nivel = int(str(raw).strip())
            except (TypeError, ValueError):
                continue
            if nivel in NIVEL_JERARQUICO_LABELS:
                mapa[plaza] = nivel
        return mapa

    raise ValueError(f"fuente inválida: {fuente!r}")


def _invalidar_cache_nivel_jerarquico():
    """
    Limpia los caches (Redis, ver `CACHES` en settings) que exponen columnas
    derivadas de `nj`/`nombre_nj` de EMPLEADOS_COMPLETOS_SIG. Sin esto, tras
    aplicar la prioridad el usuario sigue viendo el valor viejo hasta que
    expira el TTL (hasta 20 min) o corre el próximo import ZAFIRO (que sí
    invalida, ver `plantilla.tasks`).
    """
    cache.delete_many(["empleados_completos_activos_detalle", "desglose_jerarquico", "desglose_jerarquico_ocupados"])
    try:
        import redis as redis_lib

        r = redis_lib.Redis.from_url(settings.CELERY_BROKER_URL)
        for key in r.scan_iter("*empleados_completos_activos_detalle_*"):
            r.delete(key)
    except Exception:
        logger.exception("Error al invalidar cache filtrado de empleados_completos_activos_detalle")


def aplicar_prioridad_nivel_jerarquico(fuente):
    """
    Cruza cat_nivel_jerarquico_plaza (columna `fuente`) contra
    EMPLEADOS_COMPLETOS_SIG (por posición) y MOV_POS (sólo la fila activa más
    reciente por posición, vía MOV_POS_LATEST), sobreescribiendo NJ/NJ
    COMP/NJ OK/nombreNJ/NJOperativoComb y Nvl Direc respectivamente.
    """
    return aplicar_nivel_a_plazas(_mapa_plaza_a_nivel(fuente))


def aplicar_nivel_a_plazas(plaza_a_nivel):
    """
    Igual que `aplicar_prioridad_nivel_jerarquico`, pero con un mapeo
    plaza -> nivel (int) explícito en vez de derivarlo de `fuente`. La usa
    `CatNivelJerarquicoPlazaViewSet.bulk_assign` para propagar de inmediato
    el nivel recién asignado a esas plazas puntuales, sin esperar a que se
    dispare "aplicar prioridad" ni al próximo import ZAFIRO.
    """
    if not plaza_a_nivel:
        return {"empleados_actualizados": 0, "posiciones_actualizadas": 0}

    empleados = list(
        EmpleadosCompletosSig.objects.filter(posicion__in=plaza_a_nivel.keys())
        .only("id", "posicion", "nj", "nj_comp", "nj_ok", "nombre_nj", "nj_operativo_comb", "nombre_puesto_funcional")
    )
    for emp in empleados:
        nivel = plaza_a_nivel[emp.posicion]
        # Nivel 3 es "Director" por default, salvo "Titular de Aduana" cuando
        # el puesto funcional del empleado es un Administrador de Aduana
        # (mismo nivel jerárquico 3, sólo cambia la etiqueta).
        if nivel == 3 and str(emp.nombre_puesto_funcional or "").strip().upper().startswith(
            NIVEL_3_PREFIJO_TITULAR_ADUANA.upper()
        ):
            labels = NIVEL_JERARQUICO_LABELS_NIVEL_3_TITULAR_ADUANA
        else:
            labels = NIVEL_JERARQUICO_LABELS[nivel]
        emp.nj = labels["nj"]
        emp.nj_comp = labels["nj_comp"]
        emp.nj_ok = labels["nj_ok"]
        emp.nombre_nj = labels["nombre_nj"]
        emp.nj_operativo_comb = labels["nj_operativo_comb"]

    # Sólo la posición activa/más reciente por plaza (MOV_POS_LATEST): no se
    # reescribe el historial de movimientos, sólo el registro vigente.
    latest_ids = MovPosLatest.objects.filter(
        estado_psn="A", no_pos_actual__in=plaza_a_nivel.keys()
    ).values_list("mov_pos_id", flat=True)
    posiciones = list(MovPos.objects.filter(id__in=list(latest_ids)).only("id", "no_pos_actual", "nvl_direc"))
    for pos in posiciones:
        pos.nvl_direc = str(plaza_a_nivel[pos.no_pos_actual])

    with transaction.atomic():
        if empleados:
            EmpleadosCompletosSig.objects.bulk_update(
                empleados, ["nj", "nj_comp", "nj_ok", "nombre_nj", "nj_operativo_comb"], batch_size=1000
            )
        if posiciones:
            MovPos.objects.bulk_update(posiciones, ["nvl_direc"], batch_size=1000)

    _invalidar_cache_nivel_jerarquico()

    return {"empleados_actualizados": len(empleados), "posiciones_actualizadas": len(posiciones)}
