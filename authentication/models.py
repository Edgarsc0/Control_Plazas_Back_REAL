from django.db import models
from django.contrib.auth.models import Group, User
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
    # El alta y el restablecimiento de contraseña los hace un administrador
    # (no hay correo institucional disponible para mandar ligas de reseteo),
    # así que la contraseña inicial la conoce alguien más que el titular de la
    # cuenta: se le fuerza a cambiarla la primera vez que entra.
    debe_cambiar_password = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.email} - {self.rol.name}"


def sincronizar_usuario_django(entry):
    """Crea o vincula el ``User`` de Django de una entrada de whitelist y deja
    su grupo y flags de superusuario alineados con el rol asignado.

    La whitelist es la fuente de verdad del acceso; ``auth_user`` solo carga la
    credencial. Se llama tanto al administrar usuarios como al iniciar sesión,
    para que un cambio de rol se refleje sin esperar al siguiente login.

    Sincroniza ``is_staff``/``is_superuser`` en AMBOS sentidos a propósito: si
    un usuario deja de ser superadmin hay que revocarlos, no solo activarlos al
    asignar el rol (Django ignora los permisos del grupo si ``is_superuser``
    quedó pegado en True).
    """
    user = entry.user
    if user is None:
        user, creado = User.objects.get_or_create(
            username=entry.email, defaults={"email": entry.email}
        )
        if creado:
            # Sin esto el password queda en "" — que Django considera USABLE
            # (has_usable_password solo descarta los que empiezan con "!"), así
            # que la UI reportaría "ya tiene contraseña" para un alta que
            # todavía no puede entrar.
            user.set_unusable_password()
            user.save(update_fields=["password"])
        entry.user = user
        entry.save(update_fields=["user"])

    es_superadmin = entry.rol.name.lower() == "superadmin"
    if user.is_superuser != es_superadmin or user.is_staff != es_superadmin:
        user.is_staff = es_superadmin
        user.is_superuser = es_superadmin
        user.save(update_fields=["is_staff", "is_superuser"])

    user.groups.set([entry.rol])
    return user


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
            ("edit_plantilla_mov_posiciones", "Plantilla de Empleados: editar Fecha de Anuencia en tab Mov. Posiciones"),
            ("view_plantilla_movimientos", "Plantilla de Empleados: ver tab Movimientos"),
            ("view_plantilla_bajas", "Plantilla de Empleados: ver tab Empleados Bajas"),
            ("view_plantilla_geografia", "Plantilla de Empleados: ver tab Distribución Geográfica"),
            ("view_plantilla_catalogos", "Plantilla de Empleados: ver tab Catálogos"),
            ("edit_plantilla_detalle", "Plantilla de Empleados: editar celdas en tab Detalle"),
            ("edit_datos_personales", "Plantilla de Empleados: editar Escolaridad/Contacto/Domicilio en Datos Personales"),
            # Fotografía de empleado — permiso independiente por tab/componente
            # (un rol puede ver el tab pero no la fotografía dentro de él).
            ("view_plantilla_detalle_foto", "Plantilla de Empleados: ver fotografía en tab Detalle"),
            ("view_plantilla_estatus_nomina_foto", "Plantilla de Empleados: ver fotografía en tab Estatus Nómina"),
            ("view_plantilla_mov_posiciones_foto", "Plantilla de Empleados: ver fotografía en tab Mov. Posiciones"),
            ("view_plantilla_movimientos_foto", "Plantilla de Empleados: ver fotografía en tab Movimientos"),
            ("view_plantilla_bajas_foto", "Plantilla de Empleados: ver fotografía en tab Empleados Bajas"),
            ("view_plantilla_geografia_foto", "Plantilla de Empleados: ver fotografía en tab Distribución Geográfica"),
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
            ("view_organigrama_institucional", "Organigrama ANAM: ver Vista Institucional"),
            ("view_organigrama_alineacion", "Organigrama ANAM: ver Vista Alineación"),
            ("view_organigrama_sig", "Organigrama ANAM: ver Vista SIG"),
            ("edit_organigrama", "Organigrama ANAM: crear/editar/eliminar nodos (departamentos)"),
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


class PresenceLog(models.Model):
    """Una fila por cada heartbeat de presencia (ver PresenceHeartbeatView /
    PresenceHeartbeat.jsx en el front, que ya resuelve página + subtab).
    A diferencia de presence.py (que solo vive en Redis con TTL de 45s), esto
    persiste el histórico para alimentar el histograma de actividad del tab
    Roles > Usuarios: sesiones, tiempo activo y vista más visitada."""

    email = models.EmailField(db_index=True)
    path = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    subtab = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["email", "created_at"])]
