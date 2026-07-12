from rest_framework.permissions import BasePermission

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


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

    Una vista sin ninguno de estos atributos solo exige autenticación (se
    permite en pasos posteriores retrofitear vistas existentes sin romperlas).
    Superusers pasan siempre (comportamiento nativo de user.has_perm).
    """

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
            return True

        if isinstance(required, (list, tuple, set)):
            return any(user.has_perm(p) for p in required)

        return user.has_perm(required)
