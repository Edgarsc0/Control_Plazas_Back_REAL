from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import BasePermission

from .mantenimiento import usuario_bloqueado
from .scoping import get_un_scope_for_request

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

# Valores válidos del atributo `un_scope` de una vista — ver el cierre por
# defecto en HasModulePermission.
#
#   "aplicado"  la vista filtra ella misma sus datos por Unidad de Negocio
#               (resolviendo el alcance con authentication.scoping).
#   "no_aplica" la vista no expone datos a nivel empleado/plaza (catálogos,
#               monitoreo del ETL, datos propios del usuario…), así que no hay
#               nada que filtrar.
#   "exento"    la vista SÍ expone datos de varias unidades y así debe ser,
#               por decisión de negocio revisada: su propósito es justamente
#               mostrar la trayectoria completa de un empleado o de una plaza
#               a lo largo de la ANAM. El control de acceso no es el alcance
#               por UN sino su propio permiso (las pestañas del expediente,
#               ver "Expediente del personal"), que se otorga solo a quien
#               necesita esa información. Úsese únicamente con una decisión
#               explícita detrás, nunca para "destrabar" una vista: para eso
#               está filtrarla de verdad.
#
# Cualquier otro valor (o no declararlo) se trata como "todavía no revisada"
# y se NIEGA a los roles con alcance por UN. Ver HasModulePermission.
UN_SCOPE_APLICADO = "aplicado"
UN_SCOPE_NO_APLICA = "no_aplica"
UN_SCOPE_EXENTO = "exento"
UN_SCOPE_VALIDOS = (UN_SCOPE_APLICADO, UN_SCOPE_NO_APLICA, UN_SCOPE_EXENTO)


class MantenimientoActivo(APIException):
    status_code = 503
    default_detail = "Sistema en mantenimiento."
    default_code = "maintenance"


class SinMantenimiento(BasePermission):
    """Niega (503) a los usuarios no exentos mientras el modo mantenimiento
    está activo. Las vistas que el front necesita para mostrar la pantalla de
    mantenimiento (perfil, heartbeat, cambio de contraseña) declaran
    ``maintenance_exempt = True``."""

    def has_permission(self, request, view):
        if getattr(view, "maintenance_exempt", False):
            return True
        if usuario_bloqueado(request.user):
            raise MantenimientoActivo()
        return True


class HasModulePermission(BasePermission):
    """
    Permission class genérica basada en auth_permission/Group.

    Cada vista declara opcionalmente:
      - view_permission = "authentication.view_xxx"  (aplica a métodos seguros)
      - edit_permission = "authentication.edit_xxx"   (aplica a métodos de escritura;
        si falta, cae a view_permission)
      - action_permissions = {"nombre_action": "authentication.xxx", ...}
        (ViewSets: para @action cuyo permiso no se deduce del método HTTP —
        p. ej. un cálculo servido por GET/POST que semánticamente es "ver",
        no "editar". Tiene prioridad sobre view_permission/edit_permission.)

    view_permission/edit_permission también aceptan una lista/tupla de
    codenames: pasa si el usuario tiene AL MENOS UNO (para endpoints cuya data
    alimenta a más de un tab/permiso, ver plantilla/views.py).

      - extra_permission = "authentication.view_xxx" (o lista/tupla)
        Requisito ADICIONAL (AND) al de arriba: hay que tener el permiso de
        módulo Y este. Sirve para contenido que atraviesa módulos y se
        gobierna aparte — hoy, las pestañas del expediente de personal, que
        se abre desde cualquier tab pero se configura por rol de forma
        independiente. Si es lista/tupla basta uno de ellos (misma semántica
        OR), lo que permite dejar pasar al módulo que ya usaba el endpoint
        para otra cosa.

    Una vista sin ninguno de estos atributos solo exige autenticación (se
    permite en pasos posteriores retrofitear vistas existentes sin romperlas).
    Superusers pasan siempre (comportamiento nativo de user.has_perm).

    ALCANCE POR UNIDAD DE NEGOCIO (cierre por defecto)
    --------------------------------------------------
    Tener el permiso de módulo no basta si el rol además está restringido a
    ciertas Unidades de Negocio (ver RolUnScope): la vista tiene que declarar
    explícitamente que ya se hizo cargo de filtrar sus datos, con

        un_scope = UN_SCOPE_APLICADO    # filtra por UN por su cuenta
        un_scope = UN_SCOPE_NO_APLICA   # no expone datos de empleados/plazas

    Una vista que NO lo declare se niega (403) a esos roles. Es deliberado
    que el default sea negar y no permitir: así una vista nueva —o un
    permiso nuevo otorgado a un rol restringido— nunca puede filtrar datos de
    otras UN por olvido. El precio de olvidar la declaración es que la
    funcionalidad deja de servir para esos roles (visible y reportable), no
    una fuga silenciosa de datos.

    El chequeo solo corre para roles CON alcance restringido: un usuario sin
    restricción (o superadmin) no paga ni la consulta, porque
    get_un_scope_for_request memoiza el resultado en el request y devuelve
    None de inmediato.
    """

    #: Mensaje del 403 cuando la vista no declaró `un_scope`. Explícito a
    #: propósito: es un error de configuración del backend, no del usuario.
    MENSAJE_SIN_DECLARAR = (
        "Este módulo todavía no admite roles restringidos por Unidad de Negocio. "
        "Se niega el acceso para no exponer información fuera de su unidad."
    )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        action_permissions = getattr(view, "action_permissions", None)
        action = getattr(view, "action", None)
        if action_permissions and action in action_permissions:
            required = action_permissions[action]
        elif request.method in SAFE_METHODS:
            required = getattr(view, "view_permission", None)
        else:
            required = getattr(view, "edit_permission", None) or getattr(
                view, "view_permission", None
            )

        if not required:
            # Sin permiso de módulo declarado: vistas de infraestructura o
            # de datos propios del usuario (su perfil, sus filtros guardados,
            # sus suscripciones). No se les aplica el cierre por UN — no
            # exponen filas de otros empleados.
            return True

        if not self._tiene_alguno(user, required):
            return False

        extra = getattr(view, "extra_permission", None)
        if extra and not self._tiene_alguno(user, extra):
            return False

        return self._permitir_bajo_alcance_un(request, view)

    @staticmethod
    def _tiene_alguno(user, required):
        """`required` puede ser un codename o una lista/tupla/set de ellos
        (en cuyo caso basta tener uno)."""
        if isinstance(required, (list, tuple, set)):
            return any(user.has_perm(p) for p in required)
        return user.has_perm(required)

    def _permitir_bajo_alcance_un(self, request, view):
        """Cierre por defecto del alcance por Unidad de Negocio — ver el
        docstring de la clase."""
        if get_un_scope_for_request(request) is None:
            return True  # rol sin restricción (o superadmin): nada que revisar

        if getattr(view, "un_scope", None) in UN_SCOPE_VALIDOS:
            return True

        # 403 con mensaje propio en vez de `return False`: el genérico
        # ("no tiene permiso para realizar esta acción") haría parecer que
        # falta un permiso de módulo, cuando lo que falta es cobertura de
        # filtrado por UN en esta vista.
        raise PermissionDenied(self.MENSAJE_SIN_DECLARAR)
