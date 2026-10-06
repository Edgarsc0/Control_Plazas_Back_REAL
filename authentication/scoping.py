"""Resolución del alcance de datos (por Unidad de Negocio y por columnas) de
un usuario.

Punto único de verdad — todo endpoint que exponga filas de
EMPLEADOS_COMPLETOS_SIG (o tablas hermanas) debe resolver el scope aquí,
nunca reimplementar la lógica de resolución.

Ver RolUnScope/RolColumnScope (authentication/models.py) para el contrato de
semántica (sin fila = sin restricción, lista vacía = fail-closed).
"""

import hashlib

from .models import RolColumnScope, RolUaScope, RolUnScope, ancestros_de_rol
from .ua_catalog import un_de_ua
from .un_catalog import expandir_alias_un


class AlcanceUN(list):
    """Alcance por Unidad de Negocio (la lista de códigos de siempre) que
    además carga el alcance por Unidad Administrativa en `.ua`.

    Va en el MISMO objeto a propósito: `un_scope` ya recorre todos los helpers
    de plantilla/views.py (_scope_un_queryset, _scope_un_filas,
    _clausula_un_sql, huella_scope...) y, sobre todo, las CLAVES DE CACHÉ. Si
    la UA viajara por un parámetro aparte, bastaría olvidarlo en una sola
    llamada para que una aduana recibiera la respuesta cacheada de otra.

    `.ua`: None = sin recorte por UA; list[str] = códigos de UA (3 dígitos).

    CUIDADO al tocar código que recibe un alcance: `list(x)`, `sorted(x)`,
    `set(x)` o `x + [...]` devuelven una lista común y PIERDEN `.ua`. Úsese
    `ua_de_alcance(x)` para leerla antes de copiar. Como red de seguridad, una
    vista solo atiende a roles con alcance por UA si declara `ua_scope` (ver
    HasModulePermission), y eso solo se declara tras revisar todo su camino.
    """

    ua = None


def ua_de_alcance(un_codes):
    """Códigos de UA que acompañan a un alcance por UN (None = sin recorte)."""
    return getattr(un_codes, "ua", None)


def _alcance_efectivo(user, modelo, campo):
    """Alcance de `user` para un tipo de restricción (UN, UA o columnas),
    respetando el árbol de roles (ver RolPerfil).

    Por cada rol del usuario se junta su propia restricción con la de TODOS
    sus ancestros y se INTERSECTAN: un hijo nunca ve más que su padre, y un
    subrol sin restricción propia hereda la del padre. Se resuelve en vivo en
    cada request, así que recortarle el alcance a un padre recorta de
    inmediato a toda su descendencia sin tocar ninguna otra fila.

    None = ningún rol de la cadena restringe (sin restricción).
    set() = restringido a nada (fail-closed).

    Si el usuario tuviera más de un rol (normalmente es exactamente uno, ver
    sincronizar_usuario_django) se UNEN los alcances de cada cadena, y basta
    una cadena sin restricción para quedar sin restricción.
    """
    alcance_total = set()
    for rol in user.groups.all():
        alcance = alcance_efectivo_de_rol(rol, modelo, campo)
        if alcance is None:
            return None
        alcance_total |= alcance
    return alcance_total


def alcance_efectivo_de_rol(rol, modelo, campo):
    """Alcance de UN rol (no de un usuario): su restricción intersectada con
    la de todos sus ancestros. None = nadie en la cadena restringe."""
    cadena = [rol.pk] + [a.pk for a in ancestros_de_rol(rol)]
    listas = list(modelo.objects.filter(rol_id__in=cadena).values_list(campo, flat=True))
    if not listas:
        return None
    alcance = set(listas[0] or [])
    for lista in listas[1:]:
        alcance &= set(lista or [])
    return alcance


def get_un_scope_for_user(user):
    """None = sin restricción (superadmin, o rol sin RolUnScope asociado).
    list[str] = códigos de UN permitidos (unión, si por alguna vía el usuario
    terminara con más de un grupo — normalmente es exactamente uno)."""
    if not user or not getattr(user, "is_authenticated", False):
        return []  # fail-closed: nunca debería llegar aquí, HasModulePermission ya lo bloquea

    if user.is_superuser:
        return None

    codigos = _alcance_efectivo(user, RolUnScope, "cd_un_codes")
    uas = _alcance_efectivo(user, RolUaScope, "cd_ua_codes")
    if codigos is None and uas is None:
        return None
    if codigos is None:
        # Restringido por UA pero no por UN: la UN queda implícita (cada UA
        # pertenece a una sola), así que se deriva para que todo filtro por
        # UN que ya existe siga cerrando el paso.
        codigos = {un_de_ua(ua) for ua in uas} - {None}
    # Se expande aquí, en el único punto donde se resuelve el scope, para que
    # todo filtro lo herede sin acordarse de hacerlo (ver expandir_alias_un).
    alcance = AlcanceUN(expandir_alias_un(sorted(codigos)))
    alcance.ua = None if uas is None else sorted(uas)
    return alcance


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


def get_ua_scope_for_user(user):
    """None = sin restricción por Unidad Administrativa. list[str] = códigos
    de UA (3 dígitos) permitidos. Mismo contrato que get_un_scope_for_user;
    se aplica ADEMÁS del alcance por UN (ver RolUaScope)."""
    if not user or not getattr(user, "is_authenticated", False):
        return []

    if user.is_superuser:
        return None

    codigos = _alcance_efectivo(user, RolUaScope, "cd_ua_codes")
    return None if codigos is None else sorted(codigos)


def get_ua_scope_for_request(request):
    """Como get_ua_scope_for_user, memoizado en el request."""
    if not hasattr(request, "_ua_scope_cache"):
        request._ua_scope_cache = get_ua_scope_for_user(getattr(request, "user", None))
    return request._ua_scope_cache


def get_columnas_scope_for_user(user):
    """None = sin restricción (superadmin, o rol sin RolColumnScope
    asociado). list[str] = columnas de Plantilla Detalle permitidas (unión
    de las de todos sus grupos, ver get_un_scope_for_user)."""
    if not user or not getattr(user, "is_authenticated", False):
        return []

    if user.is_superuser:
        return None

    columnas = _alcance_efectivo(user, RolColumnScope, "columnas_permitidas")
    return None if columnas is None else sorted(columnas)


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
    uas = ua_de_alcance(un_codes)
    partes = [
        "*" if un_codes is None else ",".join(sorted(un_codes)),
        "*" if columnas_permitidas is None else ",".join(sorted(columnas_permitidas)),
    ]
    # La UA entra en la huella (ver AlcanceUN): dos aduanas de la misma UN
    # nunca deben compartir una copia cacheada. Solo se agrega cuando existe,
    # para no cambiar las huellas ya en uso de los roles sin recorte por UA.
    if uas is not None:
        partes.append("ua:" + ",".join(sorted(uas)))
    return hashlib.md5("|".join(partes).encode("utf-8")).hexdigest()[:12]
