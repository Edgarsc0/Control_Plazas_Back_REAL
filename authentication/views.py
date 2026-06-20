from rest_framework import status, views, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Whitelist, VerificationCode
from .serializers import WhitelistSerializer


class WhitelistViewSet(viewsets.ModelViewSet):
    queryset = Whitelist.objects.all()
    serializer_class = WhitelistSerializer


class CheckEmailView(views.APIView):
    permission_classes = [AllowAny]  # login: debe ser público

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email es requerido"}, status=status.HTTP_400_BAD_REQUEST
            )

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

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response(
                {"error": "Email y código son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                if rol_name == "SuperAdmin":
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
