import hashlib
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
from django.shortcuts import get_object_or_404
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from . import mantenimiento
from .models import (
    ModoMantenimiento,
    ModulePermission,
    PresenceLog,
    TableroLayout,
    MemoriaColumnas,
    Whitelist,
    sincronizar_usuario_django,
    RolPerfil,
)
from .presence import get_active_sessions, set_presence
from .scoping import get_columnas_scope_for_user, get_ua_scope_for_user, get_un_scope_for_user
from .permissions import UN_SCOPE_NO_APLICA
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

    queryset = (
        Group.objects.all()
        .prefetch_related("permissions__content_type")
        .select_related("un_scope_config", "columnas_scope_config", "ua_scope_config", "perfil_rol")
        .order_by("name")
    )
    serializer_class = GroupSerializer
    view_permission = "authentication.manage_roles"
    edit_permission = "authentication.manage_roles"

    def perform_destroy(self, instance):
        perfil = RolPerfil.objects.filter(rol=instance).first()
        if perfil and perfil.es_sistema:
            raise ValidationError("Los roles titulares de unidad los define el sistema y no se pueden eliminar.")
        if RolPerfil.objects.filter(padre=instance).exists():
            raise ValidationError(
                "No se puede eliminar un rol que tiene subroles. Elimina o reubica primero sus subroles."
            )
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

    maintenance_exempt = True

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

        # Alcance de datos por Unidad de Negocio — puramente informativo para
        # el front (mostrarle al usuario por qué ve menos registros, y como
        # parte de la llave de caché del navegador). La restricción real se
        # aplica siempre del lado servidor en cada endpoint, sin depender de
        # que el front lea/respete este campo.
        un_scope = get_un_scope_for_user(user)
        # Alcance por Unidad Administrativa (ver RolUaScope). Entra en la
        # misma huella: el front la usa como llave de su caché, y dos roles
        # de la misma UN pero distinta UA no deben compartir datos cacheados.
        ua_scope = get_ua_scope_for_user(user)
        if un_scope is None and ua_scope is None:
            un_scope_fingerprint = "all"
        else:
            huella = "|".join(
                "*" if alcance is None else ",".join(alcance) for alcance in (un_scope, ua_scope)
            )
            un_scope_fingerprint = hashlib.sha256(huella.encode()).hexdigest()[:12]

        # Alcance por columnas de Plantilla Detalle — mismo criterio que
        # un_scope arriba: informativo para el front (qué columnas ofrecer
        # en "Configurar Columnas"), la aplicación real es 100% del backend.
        columnas_detalle = get_columnas_scope_for_user(user)

        return Response(
            {
                "email": user.email,
                "role": whitelist_entry.rol.name if whitelist_entry else None,
                "ua": whitelist_entry.ua.nombre if whitelist_entry and whitelist_entry.ua else None,
                "is_superuser": user.is_superuser,
                "permissions": permissions,
                "tablero": whitelist_entry.tablero if whitelist_entry else None,
                "un_scope": un_scope,
                "ua_scope": ua_scope,
                "un_scope_fingerprint": un_scope_fingerprint,
                "columnas_detalle_permitidas": columnas_detalle,
                # Sin entrada en la whitelist no hay dónde registrar la
                # aceptación (cuentas técnicas): no se les exige.
                "terminos_aceptados": whitelist_entry.terminos_vigentes_aceptados if whitelist_entry else True,
            }
        )


class AceptarTerminosView(views.APIView):
    """Registra que el usuario aceptó el aviso de confidencialidad y los
    términos de uso vigentes (fecha, versión e IP). El front no deja entrar
    al sistema hasta que esto responde 200 (ver TerminosGate.jsx)."""

    maintenance_exempt = True
    un_scope = UN_SCOPE_NO_APLICA

    def post(self, request):
        from django.utils import timezone

        from .models import TERMINOS_VERSION

        entrada = getattr(request.user, "perfil", None)
        if entrada is None:
            return Response({"terminos_aceptados": True})
        reenviada = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        entrada.terminos_aceptados_at = timezone.now()
        entrada.terminos_version = TERMINOS_VERSION
        entrada.terminos_ip = (reenviada or request.META.get("REMOTE_ADDR") or "")[:64]
        entrada.save(update_fields=["terminos_aceptados_at", "terminos_version", "terminos_ip"])
        return Response({"terminos_aceptados": True})


class PresenceHeartbeatView(views.APIView):
    """
    Heartbeat de presencia: el front lo llama cada ~20s y en cada cambio de
    ruta/tab para que el panel de Roles > Usuarios muestre quién está activo
    y en qué página está, distinguiendo pestañas/dispositivos por `tab_id`
    (generado y persistido en sessionStorage del lado del front).
    """

    maintenance_exempt = True

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


class UserDescargasExcelView(views.APIView):
    """Historial de archivos Excel generados por un usuario (bitácora
    DescargaExcelLog): fecha, columnas, filtros y si llevaban fotografías o
    datos personales. Alimenta la pestaña "Historial de descargas de Excel"
    del diálogo de actividad en Roles > Usuarios."""

    view_permission = "authentication.manage_roles"
    MAX_FILAS = 300

    def get(self, request):
        from .models import DescargaExcelLog

        email = (request.query_params.get("email") or "").strip()
        if not email:
            return Response({"error": "email es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        qs = DescargaExcelLog.objects.filter(email__iexact=email).select_related("regenerada_de")
        total = qs.count()
        resultados = []
        for d in qs[: self.MAX_FILAS]:
            origen = d.regenerada_de
            resultados.append(
                {
                    "id": d.id,
                    "fecha": d.created_at.isoformat(),
                    "modulo": d.modulo,
                    "modo": d.modo,
                    "fecha_historica": d.fecha_historica,
                    "total_filas": d.total_filas,
                    "columnas": d.columnas,
                    "filtros": d.filtros,
                    "incluyo_fotos": d.incluyo_fotos,
                    "incluyo_datos_personales": d.incluyo_datos_personales,
                    "nombre_archivo": d.nombre_archivo,
                    "rol": d.rol,
                    "ip": d.ip,
                    "regenerable": bool((origen or d).snapshot),
                    "regenerada_de": (
                        {"id": origen.id, "email": origen.email, "fecha": origen.created_at.isoformat()}
                        if origen
                        else None
                    ),
                }
            )
        return Response({"total": total, "results": resultados})


class RegistrarDescargaExcelGenericaView(views.APIView):
    """Registra en la bitácora un Excel generado en cualquier pantalla del
    sistema. Lo llama el front en el momento de la descarga (ver
    lib/excelAudit.js: intercepta toda descarga .xlsx/.xlsm). Plantilla
    Detalle NO pasa por aquí: tiene su propio registro con copia de las filas
    (plantilla.views.RegistrarDescargaExcelView). Estas descargas no guardan
    copia, así que no se pueden regenerar desde el historial."""

    # No devuelve datos de plantilla: aplica igual a roles con alcance UN/UA.
    un_scope = UN_SCOPE_NO_APLICA
    MAX_COLUMNAS = 300

    def post(self, request):
        import json

        from .models import DescargaExcelLog

        datos = request.data if isinstance(request.data, dict) else {}
        columnas = []
        for c in (datos.get("columnas") or [])[: self.MAX_COLUMNAS]:
            if isinstance(c, dict) and (c.get("label") or c.get("key")):
                etiqueta = str(c.get("label") or c.get("key"))[:200]
                columnas.append({"key": str(c.get("key") or etiqueta)[:100], "label": etiqueta})
            elif isinstance(c, str) and c.strip():
                columnas.append({"key": c.strip()[:100], "label": c.strip()[:200]})
        filtros = datos.get("filtros")
        if not isinstance(filtros, dict) or len(json.dumps(filtros, default=str)) > 20000:
            filtros = {}
        try:
            total_filas = max(0, int(datos.get("total_filas") or 0))
        except (TypeError, ValueError):
            total_filas = 0

        grupo = request.user.groups.first()
        reenviada = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        log = DescargaExcelLog.objects.create(
            email=(request.user.email or request.user.get_username())[:254],
            rol=(grupo.name if grupo else ("SuperAdmin" if request.user.is_superuser else ""))[:150],
            modulo=str(datos.get("modulo") or "Sin identificar")[:200],
            total_filas=total_filas,
            columnas=columnas,
            filtros=filtros,
            incluyo_fotos=bool(datos.get("incluyo_fotos")),
            incluyo_datos_personales=bool(datos.get("incluyo_datos_personales")),
            nombre_archivo=str(datos.get("nombre_archivo") or "")[:255],
            ip=(reenviada or request.META.get("REMOTE_ADDR") or "")[:64],
        )
        return Response({"id": log.id}, status=status.HTTP_201_CREATED)


class UserVisitsHeatmapView(views.APIView):
    """Mapa de calor mensual de actividad de un usuario: segundos activos
    aproximados por día (heartbeats × HEARTBEAT_INTERVAL_SECONDS, misma
    aproximación que el promedio histórico por hora de UserVisitsView).
    Alimenta el mapa de calor del histograma de Roles > Usuarios."""

    view_permission = "authentication.manage_roles"

    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"error": "email es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        month_str = request.query_params.get("month")
        if month_str:
            try:
                month_start = datetime.strptime(month_str, "%Y-%m").date().replace(day=1)
            except ValueError:
                return Response(
                    {"error": "month inválido, usa YYYY-MM"}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            month_start = timezone.localtime().date().replace(day=1)

        next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

        tz = timezone.get_current_timezone()
        range_start = timezone.make_aware(datetime.combine(month_start, dt_time.min), tz)
        range_end = timezone.make_aware(datetime.combine(next_month_start, dt_time.min), tz)

        # Mismo truco que hourly_average_active_seconds_all_time: CONVERT_TZ
        # no está disponible, así que se agrupa en UTC crudo y el día local se
        # calcula a mano desplazando con el offset fijo del huso horario.
        offset_hours = int(timezone.localtime().utcoffset().total_seconds() // 3600)

        qs = (
            PresenceLog.objects.filter(email=email, created_at__gte=range_start, created_at__lt=range_end)
            .annotate(
                utc_day=TruncDate("created_at", tzinfo=dt_timezone.utc),
                utc_hour=ExtractHour("created_at", tzinfo=dt_timezone.utc),
            )
            .values("utc_day", "utc_hour")
            .annotate(count=Count("id"))
        )

        days_seconds = {}
        for row in qs:
            local_day = row["utc_day"]
            if row["utc_hour"] + offset_hours < 0:
                local_day -= timedelta(days=1)
            key = local_day.isoformat()
            days_seconds[key] = days_seconds.get(key, 0) + row["count"] * HEARTBEAT_INTERVAL_SECONDS

        return Response(
            {
                "month": month_start.strftime("%Y-%m"),
                "days": days_seconds,
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
                    "tablero": entry.tablero,
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

    maintenance_exempt = True

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


class TableroLayoutView(views.APIView):
    """
    Layout del tablero personalizable (ver Whitelist.tablero ==
    'personalizable') del usuario autenticado. Autoescopado a `request.user`
    (un usuario nunca puede leer/escribir el layout de otro), por eso no
    declara view_permission/edit_permission — mismo criterio que
    FiltrosGuardadosView (plantilla/views.py).

    GET -> {"widgets": [...], "escritorios": ["nombre", ...]} (listas vacías si el
    usuario aún no personaliza nada).
    PUT {"widgets": [...], "escritorios": [...]} -> reemplaza el layout completo.
    `escritorios` es opcional: si no viene, se conserva el guardado.
    """

    MAX_ESCRITORIOS = 50
    MAX_NOMBRE = 60

    def get(self, request):
        return Response(self.leer_layout(request.user))

    def put(self, request):
        return self.guardar_layout(request.user, request.data)

    @staticmethod
    def leer_layout(usuario):
        layout = TableroLayout.objects.filter(usuario=usuario).first()
        return {
            "widgets": layout.widgets if layout else [],
            "escritorios": layout.escritorios if layout else [],
        }

    def guardar_layout(self, usuario, data):
        widgets = data.get("widgets")
        if not isinstance(widgets, list):
            return Response(
                {"error": "'widgets' debe ser una lista."}, status=status.HTTP_400_BAD_REQUEST
            )
        defaults = {"widgets": widgets}
        if "escritorios" in data:
            escritorios = data.get("escritorios")
            if (
                not isinstance(escritorios, list)
                or len(escritorios) > self.MAX_ESCRITORIOS
                or not all(isinstance(n, str) for n in escritorios)
            ):
                return Response(
                    {"error": "'escritorios' debe ser una lista de textos."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            defaults["escritorios"] = [n.strip()[: self.MAX_NOMBRE] for n in escritorios]
        layout, _ = TableroLayout.objects.update_or_create(usuario=usuario, defaults=defaults)
        return Response({"widgets": layout.widgets, "escritorios": layout.escritorios})


class TableroLayoutUsuarioView(TableroLayoutView):
    """
    Lo mismo que TableroLayoutView pero sobre el tablero de OTRO usuario,
    identificado por su id de Whitelist. Es para que un administrador cargue un
    tablero por defecto a un usuario recién dado de alta (o respalde el de
    alguien), por eso exige `manage_usuarios` en vez de ir autoescopado.

    Si el usuario de Django todavía no existe (alta sin contraseña) se crea
    igual que al administrarlo desde la whitelist, para poder colgarle el layout.
    """

    view_permission = "authentication.manage_usuarios"
    edit_permission = "authentication.manage_usuarios"

    def _usuario(self, whitelist_id):
        entry = get_object_or_404(Whitelist.objects.select_related("user", "rol"), pk=whitelist_id)
        return sincronizar_usuario_django(entry)

    def get(self, request, whitelist_id):
        return Response(self.leer_layout(self._usuario(whitelist_id)))

    def put(self, request, whitelist_id):
        return self.guardar_layout(self._usuario(whitelist_id), request.data)


class MantenimientoView(views.APIView):
    """Modo mantenimiento del sistema.

    GET (público, con o sin token): estado para que el front decida si muestra
    la pantalla de mantenimiento. ``bloqueado`` ya viene resuelto para quien
    pregunta (los exentos nunca lo están; los superadmins solo si no se marcan). Solo un superadmin recibe
    además la lista de exentos.
    PUT (superadmin): enciende/apaga, cambia el mensaje y define los exentos
    (ids de Whitelist — los desarrolladores a quienes no se les niega el servicio).
    """

    permission_classes = [AllowAny]
    maintenance_exempt = True

    def _payload(self, request):
        estado = mantenimiento.obtener_estado()
        user = request.user
        data = {
            "activo": estado["activo"],
            "mensaje": estado["mensaje"],
            "bloqueado": mantenimiento.usuario_bloqueado(user, estado),
        }
        if user.is_authenticated and user.is_superuser:
            config = ModoMantenimiento.objects.filter(pk=1).first()
            data["exentos"] = list(config.exentos.values_list("id", flat=True)) if config else []
        return data

    def get(self, request):
        return Response(self._payload(request))

    def put(self, request):
        user = request.user
        if not (user.is_authenticated and user.is_superuser):
            return Response({"detail": "Solo un superadmin puede cambiar el modo mantenimiento."}, status=status.HTTP_403_FORBIDDEN)

        activo = request.data.get("activo")
        if not isinstance(activo, bool):
            raise ValidationError({"activo": "Debe ser true o false."})
        mensaje = str(request.data.get("mensaje") or "").strip()[:300]
        exentos = request.data.get("exentos", [])
        if not isinstance(exentos, list) or not all(isinstance(i, int) for i in exentos):
            raise ValidationError({"exentos": "Debe ser una lista de ids de usuario."})

        config, _ = ModoMantenimiento.objects.get_or_create(pk=1)
        config.activo = activo
        config.mensaje = mensaje
        config.actualizado_por = user
        config.save()
        # Quien lo activa nunca se auto-bloquea: si no, no podría apagarlo.
        propio = Whitelist.objects.filter(user=user).values_list("id", flat=True)
        config.exentos.set(Whitelist.objects.filter(id__in=set(exentos) | set(propio)))
        mantenimiento.invalidar_cache()
        return Response(self._payload(request))


class MemoriasColumnasView(views.APIView):
    """Memorias de columnas (hasta 3 por tabla) del usuario autenticado — ver MemoriaColumnas.
    Autoescopado a `request.user` (nadie lee ni escribe las de otro), así que como
    TableroLayoutView no declara permiso de módulo: son datos propios, no filas de empleados.

    GET    ?tabla=<t>                              -> [{slot, nombre, columnas}, ...]
    PUT    {tabla, slot, nombre, columnas: [...]}  -> guarda/reemplaza ese slot
    DELETE ?tabla=<t>&slot=<n>                     -> borra ese slot

    Restricción de columnas del rol: en `plantilla_detalle` las columnas se recortan al guardar
    contra RolColumnScope (+ el set fijo siempre incluido + la foto). El front ya solo ofrece
    las permitidas; esto es la segunda capa, para que una memoria nunca las guarde aunque se
    llame a la API directo. Las otras tablas no tienen restricción de columnas por rol.
    """

    TABLAS = {"plantilla_detalle", "bajas", "mov_posiciones", "movimientos", "alineacion"}
    MAX_COLUMNAS = 300
    MAX_NOMBRE = 40

    def _tabla(self, valor):
        tabla = (valor or "").strip()
        return tabla if tabla in self.TABLAS else None

    @staticmethod
    def _serializar(m):
        return {"slot": m.slot, "nombre": m.nombre, "columnas": m.columnas}

    def get(self, request):
        tabla = self._tabla(request.query_params.get("tabla"))
        if not tabla:
            return Response({"error": "Tabla no válida."}, status=status.HTTP_400_BAD_REQUEST)
        memorias = MemoriaColumnas.objects.filter(usuario=request.user, tabla=tabla).order_by("slot")
        return Response([self._serializar(m) for m in memorias])

    def put(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        tabla = self._tabla(data.get("tabla"))
        try:
            slot = int(data.get("slot"))
        except (TypeError, ValueError):
            slot = None
        columnas = data.get("columnas")
        if not tabla or slot not in MemoriaColumnas.SLOTS:
            return Response({"error": "Tabla o espacio de memoria no válido."}, status=status.HTTP_400_BAD_REQUEST)
        if (
            not isinstance(columnas, list)
            or len(columnas) > self.MAX_COLUMNAS
            or not all(isinstance(c, str) and 0 < len(c) <= 100 for c in columnas)
        ):
            return Response({"error": "'columnas' debe ser una lista de claves."}, status=status.HTTP_400_BAD_REQUEST)

        columnas = list(dict.fromkeys(c.strip() for c in columnas))
        if tabla == "plantilla_detalle":
            from .columnas_detalle_catalog import COLUMNAS_DETALLE_SIEMPRE_INCLUIDAS
            from .scoping import get_columnas_scope_for_request

            permitidas = get_columnas_scope_for_request(request)
            if permitidas is not None:
                validas = set(permitidas) | set(COLUMNAS_DETALLE_SIEMPRE_INCLUIDAS) | {"foto"}
                columnas = [c for c in columnas if c in validas]
        if not columnas:
            return Response({"error": "La memoria debe tener al menos una columna."}, status=status.HTTP_400_BAD_REQUEST)

        nombre = str(data.get("nombre") or "").strip()[: self.MAX_NOMBRE]
        memoria, _ = MemoriaColumnas.objects.update_or_create(
            usuario=request.user, tabla=tabla, slot=slot,
            defaults={"nombre": nombre, "columnas": columnas},
        )
        return Response(self._serializar(memoria))

    def delete(self, request):
        tabla = self._tabla(request.query_params.get("tabla"))
        try:
            slot = int(request.query_params.get("slot"))
        except (TypeError, ValueError):
            slot = None
        if not tabla or slot not in MemoriaColumnas.SLOTS:
            return Response({"error": "Tabla o espacio de memoria no válido."}, status=status.HTTP_400_BAD_REQUEST)
        MemoriaColumnas.objects.filter(usuario=request.user, tabla=tabla, slot=slot).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
