from collections import Counter
from datetime import datetime, time as dt_time, timedelta, timezone as dt_timezone

from rest_framework import generics, status, views, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from .models import (
    ModulePermission,
    PresenceLog,
    Whitelist,
    sincronizar_usuario_django,
)
from .presence import get_active_sessions, set_presence
from .serializers import GroupSerializer, PermissionSerializer, WhitelistSerializer


class WhitelistViewSet(viewsets.ModelViewSet):
    queryset = Whitelist.objects.select_related("rol", "ua", "user").all()
    serializer_class = WhitelistSerializer
    view_permission = "authentication.manage_usuarios"
    edit_permission = "authentication.manage_usuarios"
    # La creación del User de Django, la asignación de grupo/flags y el alta o
    # restablecimiento de contraseña los resuelve WhitelistSerializer
    # (_aplicar_password), para que valgan igual desde esta API que desde
    # cualquier otro punto que guarde una entrada de whitelist.


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD de roles (Group) editable desde UI, con asignación de permisos."""

    queryset = Group.objects.all().prefetch_related("permissions__content_type").order_by("name")
    serializer_class = GroupSerializer
    view_permission = "authentication.manage_roles"
    edit_permission = "authentication.manage_roles"

    def perform_destroy(self, instance):
        if Whitelist.objects.filter(rol=instance).exists():
            raise ValidationError(
                "No se puede eliminar un rol con usuarios asignados. Reasigna esos usuarios primero."
            )
        instance.delete()


class PermissionListView(generics.ListAPIView):
    """Catálogo de permisos de negocio asignables a un rol."""

    queryset = ModulePermission.catalog_queryset().select_related("content_type").order_by("codename")
    serializer_class = PermissionSerializer
    view_permission = "authentication.manage_roles"


class MePermissionsView(views.APIView):
    """Rol y permisos efectivos del usuario autenticado (para hidratar el front)."""

    def get(self, request):
        user = request.user
        whitelist_entry = getattr(user, "perfil", None)

        if user.is_superuser:
            # get_all_permissions() no expande automáticamente a "todo" para
            # superusers (solo has_perm() hace ese bypass); exponemos el
            # catálogo completo para que el front no oculte módulos.
            permissions = sorted(
                f"{app_label}.{codename}"
                for app_label, codename in ModulePermission.catalog_queryset().values_list(
                    "content_type__app_label", "codename"
                )
            )
        else:
            permissions = sorted(user.get_all_permissions())

        return Response(
            {
                "email": user.email,
                "role": whitelist_entry.rol.name if whitelist_entry else None,
                "ua": whitelist_entry.ua.nombre if whitelist_entry and whitelist_entry.ua else None,
                "is_superuser": user.is_superuser,
                "permissions": permissions,
            }
        )


class PresenceHeartbeatView(views.APIView):
    """
    Heartbeat de presencia: el front lo llama cada ~20s y en cada cambio de
    ruta/tab para que el panel de Roles > Usuarios muestre quién está activo
    y en qué página está, distinguiendo pestañas/dispositivos por `tab_id`
    (generado y persistido en sessionStorage del lado del front).
    """

    def post(self, request):
        tab_id = request.data.get("tab_id")
        path = request.data.get("path")
        if not tab_id or not path:
            return Response(
                {"error": "tab_id y path son requeridos"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        whitelist_entry = getattr(user, "perfil", None)
        title = request.data.get("title") or path
        subtab = request.data.get("subtab")
        set_presence(
            email=user.email,
            tab_id=tab_id,
            rol=whitelist_entry.rol.name if whitelist_entry else None,
            ua=whitelist_entry.ua.nombre if whitelist_entry and whitelist_entry.ua else None,
            path=path,
            title=title,
            subtab=subtab,
        )
        # Persiste el histórico (presence.py solo vive en Redis con TTL de
        # 45s) para alimentar el histograma de actividad de Roles > Usuarios.
        PresenceLog.objects.create(email=user.email, path=path, title=title, subtab=subtab or "")
        return Response(status=status.HTTP_204_NO_CONTENT)


class PresenceListView(views.APIView):
    """Usuarios activos ahora mismo + página/tab en la que están (tab Usuarios de Roles)."""

    view_permission = "authentication.manage_roles"

    def get(self, request):
        return Response(get_active_sessions())


# El front manda un heartbeat cada 20s (HEARTBEAT_INTERVAL_MS en
# PresenceHeartbeat.jsx) mientras la pestaña está abierta, y además en cada
# cambio de ruta/tab/subtab.
HEARTBEAT_INTERVAL_SECONDS = 20

# Huecos entre heartbeats de hasta esto se consideran parte de la misma
# "visita" (tolera un par de beats perdidos por red/reconexión); un hueco
# mayor cierra la sesión y el siguiente heartbeat abre una nueva.
SESSION_GAP_SECONDS = 90


def _view_label(title, subtab):
    return f"{title} › {subtab}" if subtab else title


class UserVisitsView(views.APIView):
    """Actividad histórica de un usuario a partir de su heartbeat de
    presencia: sesiones del día (con duración y páginas vistas en cada una),
    distribución de tiempo activo en las 24 horas, promedio histórico por
    hora y vista (página › subtab) más visitada. Alimenta el histograma de
    Roles > Usuarios."""

    view_permission = "authentication.manage_roles"

    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"error": "email es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        date_str = request.query_params.get("date")
        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "date inválida, usa YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            day = timezone.localtime().date()

        tz = timezone.get_current_timezone()
        day_start = timezone.make_aware(datetime.combine(day, dt_time.min), tz)
        day_end = day_start + timedelta(days=1)

        all_qs = PresenceLog.objects.filter(email=email)
        day_qs = all_qs.filter(created_at__gte=day_start, created_at__lt=day_end)

        # --- Día seleccionado: se trae completo a Python (acotado a un día,
        # nunca son muchas filas) para poder agrupar por sesión con precisión. ---
        day_rows = list(day_qs.order_by("created_at").values("created_at", "title", "subtab"))

        sessions = []
        hourly_active_seconds_day = [0] * 24
        top_view_day_counter = Counter()
        current = None
        for row in day_rows:
            ts = row["created_at"].astimezone(tz)
            label = _view_label(row["title"], row["subtab"])
            top_view_day_counter[label] += 1

            if current is not None:
                gap = (ts - current["end"]).total_seconds()
                if gap > SESSION_GAP_SECONDS:
                    sessions.append(current)
                    current = None
                else:
                    hourly_active_seconds_day[current["end"].hour] += gap

            if current is None:
                current = {"start": ts, "end": ts, "views": Counter()}

            current["end"] = ts
            current["views"][label] += 1

        if current is not None:
            sessions.append(current)

        total_active_seconds_day = sum(int((s["end"] - s["start"]).total_seconds()) for s in sessions)

        top_view_day = None
        if top_view_day_counter:
            label, count = top_view_day_counter.most_common(1)[0]
            top_view_day = {"label": label, "count": count}

        sessions_payload = [
            {
                "start": s["start"].strftime("%H:%M:%S"),
                "end": s["end"].strftime("%H:%M:%S"),
                "duration_seconds": int((s["end"] - s["start"]).total_seconds()),
                "views": [{"label": lbl, "count": c} for lbl, c in s["views"].most_common()],
            }
            for s in sessions
        ]

        # --- Histórico completo: agregación en la BD (nunca se trae todo el
        # historial a Python). Tiempo activo por hora se aproxima como
        # cantidad_de_heartbeats × HEARTBEAT_INTERVAL_SECONDS: dado que el
        # heartbeat late a intervalo fijo mientras hay pestaña abierta, es
        # una aproximación razonable sin tener que reconstruir sesiones de
        # meses de historial en cada request. ---
        #
        # ExtractHour/TruncDate con conversión de huso horario dependen de
        # las tablas mysql.time_zone_* (CONVERT_TZ), que no están cargadas en
        # este servidor y devuelven NULL en silencio. Se extrae en UTC crudo
        # (tzinfo=utc evita el CONVERT_TZ) y se desplaza el bucket a mano con
        # el offset del huso horario configurado (America/Mexico_City = -6,
        # sin horario de verano desde 2022).
        offset_hours = int(timezone.localtime().utcoffset().total_seconds() // 3600)

        def bucket_hour(utc_hour):
            return (utc_hour + offset_hours) % 24

        active_days = (
            all_qs.annotate(day=TruncDate("created_at", tzinfo=dt_timezone.utc)).values("day").distinct().count()
        )
        hourly_average_active_seconds_all_time = [0.0] * 24
        if active_days:
            for row in (
                all_qs.annotate(hour=ExtractHour("created_at", tzinfo=dt_timezone.utc))
                .values("hour")
                .annotate(count=Count("id"))
            ):
                seconds = row["count"] * HEARTBEAT_INTERVAL_SECONDS
                hourly_average_active_seconds_all_time[bucket_hour(row["hour"])] = round(seconds / active_days, 1)

        top_view_all_time = None
        top_row = (
            all_qs.values("title", "subtab").annotate(count=Count("id")).order_by("-count").first()
        )
        if top_row:
            top_view_all_time = {
                "label": _view_label(top_row["title"], top_row["subtab"]),
                "count": top_row["count"],
            }

        return Response(
            {
                "date": day.isoformat(),
                "sessions_count_day": len(sessions),
                "total_active_seconds_day": total_active_seconds_day,
                "hourly_active_seconds_day": hourly_active_seconds_day,
                "hourly_average_active_seconds_all_time": hourly_average_active_seconds_all_time,
                "top_view_all_time": top_view_all_time,
                "top_view_day": top_view_day,
                "sessions": sessions_payload,
            }
        )


class LoginView(views.APIView):
    """
    Inicio de sesión con correo + contraseña.

    Sustituye al flujo anterior de código de verificación por correo (OTP), que
    dejó de ser viable cuando se bloqueó el envío a las cuentas
    institucionales. La whitelist sigue siendo la que decide QUIÉN puede
    entrar y con qué rol; lo único que cambia es cómo se prueba la identidad.
    """

    permission_classes = [AllowAny]  # login: debe ser público
    authentication_classes = []  # evita exigir CSRF si el navegador trae una sessionid vieja

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response(
                {"error": "Correo y contraseña son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entry = (
            Whitelist.objects.filter(email__iexact=email, activo=True)
            .select_related("rol", "ua", "user")
            .first()
        )

        # Un mismo mensaje y un mismo status para "no está en la whitelist",
        # "está dado de baja" y "contraseña incorrecta": distinguirlos
        # convertiría este endpoint público en un oráculo para averiguar qué
        # correos tienen acceso al sistema.
        credenciales_invalidas = Response(
            {"error": "Correo o contraseña incorrectos"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

        if entry is None or entry.user is None:
            return credenciales_invalidas

        # authenticate() aplica el hash configurado y además rechaza usuarios
        # con is_active=False (ModelBackend), sin que haga falta revisarlo aquí.
        user = authenticate(request, username=entry.user.username, password=password)
        if user is None:
            return credenciales_invalidas

        # Rol y flags se re-sincronizan en cada login: si un admin cambió el rol
        # mientras el usuario estaba fuera, entra ya con los permisos nuevos.
        sincronizar_usuario_django(entry)
        login(request, user)

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Acceso concedido",
                "token": token.key,
                "debe_cambiar_password": entry.debe_cambiar_password,
                "user": {
                    "email": user.email,
                    "rol": entry.rol.name,
                    "ua": entry.ua.nombre if entry.ua else None,
                },
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(views.APIView):
    """
    Cambio de contraseña del propio usuario autenticado.

    Es la contraparte del alta administrada: como la contraseña inicial la
    define un administrador (no hay correo para mandar ligas de reseteo), el
    titular la cambia aquí y con eso se apaga su `debe_cambiar_password`.
    """

    def post(self, request):
        password_actual = request.data.get("password_actual") or ""
        password_nueva = request.data.get("password_nueva") or ""

        if not password_actual or not password_nueva:
            return Response(
                {"error": "La contraseña actual y la nueva son requeridas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if not user.check_password(password_actual):
            return Response(
                {"error": "La contraseña actual es incorrecta"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if password_nueva == password_actual:
            return Response(
                {"error": "La contraseña nueva debe ser distinta de la actual"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password_nueva, user)
        except DjangoValidationError as exc:
            return Response(
                {"error": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(password_nueva)
        user.save(update_fields=["password"])

        entry = getattr(user, "perfil", None)
        if entry and entry.debe_cambiar_password:
            entry.debe_cambiar_password = False
            entry.save(update_fields=["debe_cambiar_password"])

        # set_password no invalida el token de DRF (a diferencia de la sesión),
        # así que se rota a mano: si la contraseña se cambió porque la anterior
        # se filtró, el token emitido con ella tiene que dejar de servir.
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        update_session_auth_hash(request, user)

        return Response(
            {"message": "Contraseña actualizada", "token": token.key},
            status=status.HTTP_200_OK,
        )
