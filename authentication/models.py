from django.db import models
from django.contrib.auth.models import Group, User
import random
import string
from django.utils import timezone
from datetime import timedelta
from ua.models import UnidadAdministrativa


class Whitelist(models.Model):
    email = models.EmailField(unique=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="perfil"
    )
    rol = models.ForeignKey(Group, on_delete=models.CASCADE)
    ua = models.ForeignKey(
        UnidadAdministrativa, on_delete=models.SET_NULL, null=True, blank=True
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.email} - {self.rol.name}"


class ModulePermission(models.Model):
    # Sin tabla real (managed=False): existe solo para que Django registre estos
    # codenames en auth_permission via el signal post_migrate, sin migrar datos reales.
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            # Plantilla de Empleados — un permiso por tab (datos con distinta
            # sensibilidad: bajas/nómina no deberían verlos los mismos roles
            # que ven el detalle general).
            ("view_plantilla_detalle", "Plantilla de Empleados: ver tab Detalle"),
            ("view_plantilla_estatus_nomina", "Plantilla de Empleados: ver tab Estatus Nómina"),
            ("view_plantilla_mov_posiciones", "Plantilla de Empleados: ver tab Mov. Posiciones"),
            ("view_plantilla_movimientos", "Plantilla de Empleados: ver tab Movimientos"),
            ("view_plantilla_bajas", "Plantilla de Empleados: ver tab Empleados Bajas"),
            ("view_plantilla_geografia", "Plantilla de Empleados: ver tab Distribución Geográfica"),
            ("view_plantilla_catalogos", "Plantilla de Empleados: ver tab Catálogos"),
            ("edit_plantilla_detalle", "Plantilla de Empleados: editar celdas en tab Detalle"),
            # Ocupación de Plazas por Oficio
            ("view_ocupacion_sankey", "Ocupación de Plazas: ver tab Sankey"),
            ("view_ocupacion_tabla", "Ocupación de Plazas: ver tab Tabla"),
            ("view_ocupacion_estadisticas", "Ocupación de Plazas: ver tab Estadísticas"),
            ("edit_ocupacion_plazas", "Ocupación de Plazas: editar asignación de plazas"),
            # Valuación Presupuestaria
            ("view_valuacion_presupuestaria", "Valuación Presupuestaria: ver Simulador y Asuntos"),
            ("edit_valuacion_parametros", "Valuación Presupuestaria: editar Parámetros (catálogo/conceptos/constantes)"),
            # Resto de módulos (sin tabs)
            ("view_oficios_turnados", "Puede ver Oficios Turnados DO"),
            ("view_organigrama", "Puede ver Organigrama ANAM"),
            ("view_monitoreo_zafiro", "Puede ver Monitoreo ZAFIRO"),
            # Administración del propio sistema de roles
            ("manage_roles", "Puede administrar roles y permisos"),
            ("manage_usuarios", "Puede administrar usuarios (whitelist)"),
        ]

    @classmethod
    def catalog_queryset(cls):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        return Permission.objects.filter(content_type=ContentType.objects.get_for_model(cls))


class VerificationCode(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code():
        return "".join(random.choices(string.digits, k=6))

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
