"""Resolución del alcance de datos (por Unidad de Negocio y por columnas) de
un usuario.

Punto único de verdad — todo endpoint que exponga filas de
EMPLEADOS_COMPLETOS_SIG (o tablas hermanas) debe resolver el scope aquí,
nunca reimplementar la lógica de resolución.

Ver RolUnScope/RolColumnScope (authentication/models.py) para el contrato de
semántica (sin fila = sin restricción, lista vacía = fail-closed).
"""

import hashlib

from .models import RolColumnScope, RolUnScope
from .un_catalog import expandir_alias_un


def get_un_scope_for_user(user):
    """None = sin restricción (superadmin, o rol sin RolUnScope asociado).
    list[str] = códigos de UN permitidos (unión, si por alguna vía el usuario
    terminara con más de un grupo — normalmente es exactamente uno)."""
    if not user or not getattr(user, "is_authenticated", False):
        return []  # fail-closed: nunca debería llegar aquí, HasModulePermission ya lo bloquea

    if user.is_superuser:
        return None

    # Vía `rol__user=user` (no `user.perfil.rol`) para no depender de que
    # exista un Whitelist — sincronizar_usuario_django() fija `user.groups`
    # a exactamente el grupo del rol en cada login/alta.
    listas = list(RolUnScope.objects.filter(rol__user=user).values_list("cd_un_codes", flat=True))
    if not listas:
        return None

    codigos = set()
    for lista in listas:
        codigos.update(lista or [])
    # Se expande aquí, en el único punto donde se resuelve el scope, para que
    # todo filtro lo herede sin acordarse de hacerlo (ver expandir_alias_un).
    return expandir_alias_un(sorted(codigos))


def get_un_scope_for_request(request):
    """Como get_un_scope_for_user, memoizado en el request para que una
    misma vista pueda llamarlo varias veces sin volver a consultar la BD.

    Sin caché entre requests a propósito: un scope editado por un admin debe
    surtir efecto en la siguiente petición del usuario afectado, no esperar
    a que expire algún TTL.
    """
    if not hasattr(request, "_un_scope_cache"):
        request._un_scope_cache = get_un_scope_for_user(getattr(request, "user", None))
    return request._un_scope_cache


def get_columnas_scope_for_user(user):
    """None = sin restricción (superadmin, o rol sin RolColumnScope
    asociado). list[str] = columnas de Plantilla Detalle permitidas (unión
    de las de todos sus grupos, ver get_un_scope_for_user)."""
    if not user or not getattr(user, "is_authenticated", False):
        return []

    if user.is_superuser:
        return None

    listas = list(
        RolColumnScope.objects.filter(rol__user=user).values_list("columnas_permitidas", flat=True)
    )
    if not listas:
        return None

    columnas = set()
    for lista in listas:
        columnas.update(lista or [])
    return sorted(columnas)


def get_columnas_scope_for_request(request):
    """Como get_columnas_scope_for_user, memoizado en el request."""
    if not hasattr(request, "_columnas_scope_cache"):
        request._columnas_scope_cache = get_columnas_scope_for_user(getattr(request, "user", None))
    return request._columnas_scope_cache


def huella_scope(un_codes, columnas_permitidas=None):
    """Identificador corto y estable del alcance de datos de quien pide, para
    usarlo como parte de la clave de caché de artefactos que NO se pueden
    recortar una vez generados (los .xlsx: son bytes opacos).

    Donde se puede filtrar al salir se prefiere siempre eso —una sola copia
    sin recortar en Redis, recortada en cada respuesta— pero un libro de Excel
    ya armado no admite recorte, así que la alternativa es cachear una copia
    por alcance. Devuelve "all" para el caso sin restricción, de modo que los
    usuarios sin alcance (la gran mayoría) sigan compartiendo una sola copia.
    """
    if un_codes is None and columnas_permitidas is None:
        return "all"
    partes = [
        "*" if un_codes is None else ",".join(sorted(un_codes)),
        "*" if columnas_permitidas is None else ",".join(sorted(columnas_permitidas)),
    ]
    return hashlib.md5("|".join(partes).encode("utf-8")).hexdigest()[:12]
