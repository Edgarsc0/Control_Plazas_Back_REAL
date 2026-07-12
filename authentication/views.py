from rest_framework import generics, status, views, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import Group, User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import ModulePermission, Whitelist, VerificationCode
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
            if instance.rol.name.lower() == "superadmin" and not instance.user.is_superuser:
                instance.user.is_staff = True
                instance.user.is_superuser = True
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

                # Automatización de privilegios para Administradores
                rol_name = whitelist_entry.rol.name.lower()
                if rol_name == "superadmin":
                    user.is_staff = True
                    user.is_superuser = True
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
