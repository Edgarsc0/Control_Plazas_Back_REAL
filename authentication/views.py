from collections import Counter
from datetime import datetime, time as dt_time, timedelta, timezone as dt_timezone

from rest_framework import generics, status, views, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import Group, User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.db.models import Count
from django.db.models.functions import ExtractHour, TruncDate
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.conf import settings
from .log_context import normalize_path
from .models import ModulePermission, RequestVisit, Whitelist, VerificationCode
from .presence import get_active_sessions, set_presence
from .serializers import GroupSerializer, PermissionSerializer, WhitelistSerializer


class WhitelistViewSet(viewsets.ModelViewSet):
    queryset = Whitelist.objects.all()
    serializer_class = WhitelistSerializer
    view_permission = "authentication.manage_usuarios"
    edit_permission = "authentication.manage_usuarios"

    def perform_update(self, serializer):
        previous_rol_id = serializer.instance.rol_id
        instance = serializer.save()

        # user.groups solo se sincroniza en login (VerifyCodeView); si el usuario
        # ya tiene sesión creada, hay que reflejar aquí el cambio de rol para que
        # sus permisos cambien de inmediato, sin esperar a que vuelva a loguearse.
        if instance.user and instance.rol_id != previous_rol_id:
            instance.user.groups.set([instance.rol])
            # Sincroniza is_superuser/is_staff en ambos sentidos: si el rol deja de
            # ser superadmin hay que revocarlos, no solo activarlos al asignarlo
            # (bug previo: el flag quedaba pegado tras reasignar a otro rol, y
            # Django ignora los permisos del grupo cuando is_superuser=True).
            es_superadmin = instance.rol.name.lower() == "superadmin"
            if instance.user.is_superuser != es_superadmin or instance.user.is_staff != es_superadmin:
                instance.user.is_staff = es_superadmin
                instance.user.is_superuser = es_superadmin
                instance.user.save(update_fields=["is_staff", "is_superuser"])


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
        set_presence(
            email=user.email,
            tab_id=tab_id,
            rol=whitelist_entry.rol.name if whitelist_entry else None,
            ua=whitelist_entry.ua.nombre if whitelist_entry and whitelist_entry.ua else None,
            path=path,
            title=request.data.get("title") or path,
            subtab=request.data.get("subtab"),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PresenceListView(views.APIView):
    """Usuarios activos ahora mismo + página/tab en la que están (tab Usuarios de Roles)."""

    view_permission = "authentication.manage_roles"

    def get(self, request):
        return Response(get_active_sessions())


def _top_page(queryset):
    """Top de páginas normalizadas sobre las 200 rutas crudas más frecuentes
    (evita traer todo el historial a Python; con 200 rutas crudas sobra para
    capturar el top real tras colapsar ids)."""
    raw_counts = queryset.values("path").annotate(count=Count("id")).order_by("-count")[:200]
    collapsed = Counter()
    for row in raw_counts:
        collapsed[normalize_path(row["path"])] += row["count"]
    if not collapsed:
        return None
    path, count = collapsed.most_common(1)[0]
    return {"path": path, "count": count}


class UserVisitsView(views.APIView):
    """Actividad histórica de un usuario: distribución horaria del día
    seleccionado, promedio histórico por hora, página más visitada y detalle
    de cada visita del día. Alimenta el histograma de Roles > Usuarios."""

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

        # ExtractHour/TruncDate con conversión de huso horario dependen de las
        # tablas mysql.time_zone_* (CONVERT_TZ), que no están cargadas en este
        # servidor y devuelven NULL en silencio. Se extrae en UTC crudo
        # (tzinfo=utc evita el CONVERT_TZ) y se desplaza el bucket a mano con
        # el offset del huso horario configurado (America/Mexico_City = -6,
        # sin horario de verano desde 2022).
        offset_hours = int(timezone.localtime().utcoffset().total_seconds() // 3600)

        def bucket_hour(utc_hour):
            return (utc_hour + offset_hours) % 24

        all_qs = RequestVisit.objects.filter(email=email)
        day_qs = all_qs.filter(created_at__gte=day_start, created_at__lt=day_end)

        hourly_distribution_day = [0] * 24
        for row in (
            day_qs.annotate(hour=ExtractHour("created_at", tzinfo=dt_timezone.utc))
            .values("hour")
            .annotate(count=Count("id"))
        ):
            hourly_distribution_day[bucket_hour(row["hour"])] = row["count"]

        active_days = all_qs.annotate(day=TruncDate("created_at", tzinfo=dt_timezone.utc)).values("day").distinct().count()
        hourly_average_all_time = [0.0] * 24
        if active_days:
            for row in (
                all_qs.annotate(hour=ExtractHour("created_at", tzinfo=dt_timezone.utc))
                .values("hour")
                .annotate(count=Count("id"))
            ):
                hourly_average_all_time[bucket_hour(row["hour"])] = round(row["count"] / active_days, 2)

        visits = [
            {
                "time": v["created_at"].astimezone(tz).strftime("%H:%M:%S"),
                "method": v["method"],
                "path": normalize_path(v["path"]),
            }
            for v in day_qs.order_by("created_at").values("created_at", "method", "path")
        ]

        return Response(
            {
                "date": day.isoformat(),
                "total_visits_day": day_qs.count(),
                "hourly_distribution_day": hourly_distribution_day,
                "hourly_average_all_time": hourly_average_all_time,
                "top_page_all_time": _top_page(all_qs),
                "top_page_day": _top_page(day_qs),
                "visits": visits,
            }
        )


class CheckEmailView(views.APIView):
    permission_classes = [AllowAny]  # login: debe ser público
    authentication_classes = []  # evita exigir CSRF si el navegador trae una sessionid vieja

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email es requerido"}, status=status.HTTP_400_BAD_REQUEST
            )
        email = email.strip()

        try:
            entry = Whitelist.objects.get(email=email, activo=True)

            # Generar código
            code = VerificationCode.generate_code()
            VerificationCode.objects.create(email=email, code=code)

            # Preparar correo
            subject = f"{code} es tu código de verificación de Eje Central"
            html_message = render_to_string("emails/otp_code.html", {"code": code})
            plain_message = strip_tags(html_message)
            from_email = settings.EMAIL_HOST_USER

            try:
                send_mail(
                    subject,
                    plain_message,
                    from_email,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                return Response(
                    {"error": f"Error al enviar correo: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "Código de verificación enviado", "email": email},
                status=status.HTTP_200_OK,
            )

        except Whitelist.DoesNotExist:
            return Response(
                {"error": "Correo no autorizado"}, status=status.HTTP_403_FORBIDDEN
            )


class VerifyCodeView(views.APIView):
    permission_classes = [AllowAny]  # login: debe ser público
    authentication_classes = []  # evita exigir CSRF si el navegador trae una sessionid vieja

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response(
                {"error": "Email y código son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = email.strip()
        code = code.strip()

        try:
            vc = VerificationCode.objects.filter(
                email=email, code=code, is_used=False
            ).last()

            if vc and vc.is_valid():
                vc.is_used = True
                vc.save()

                # Obtener info de la whitelist
                whitelist_entry = Whitelist.objects.get(email=email)

                # Crear o obtener usuario
                user, created = User.objects.get_or_create(username=email, email=email)

                # Automatización de privilegios para Administradores. Sincroniza en
                # ambos sentidos (activa Y revoca) para que un cambio de rol previo
                # a "superadmin" no deje is_superuser pegado tras reasignar el rol.
                rol_name = whitelist_entry.rol.name.lower()
                es_superadmin = rol_name == "superadmin"
                if user.is_superuser != es_superadmin or user.is_staff != es_superadmin:
                    user.is_staff = es_superadmin
                    user.is_superuser = es_superadmin
                    user.save()

                # Vincular la entrada de la whitelist con el usuario de Django
                whitelist_entry.user = user
                whitelist_entry.save()

                # Asignar rol (Grupo)
                user.groups.clear()
                user.groups.add(whitelist_entry.rol)

                # Login (sesión de Django)
                login(request, user)

                # Generar o obtener Token para la API
                token, _ = Token.objects.get_or_create(user=user)

                return Response(
                    {
                        "message": "Acceso concedido",
                        "token": token.key,
                        "user": {
                            "email": user.email,
                            "rol": whitelist_entry.rol.name,
                            "ua": (
                                whitelist_entry.ua.nombre
                                if whitelist_entry.ua
                                else None
                            ),
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Código inválido o expirado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
