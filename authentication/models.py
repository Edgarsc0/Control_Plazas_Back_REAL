from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.contrib.auth.models import Group, User
from ua.models import UnidadAdministrativa

# Tableros ejecutivos de una sola página (sin redirecciones) para perfiles que
# necesitan una vista muy concisa en vez del sistema completo — ej. la
# Dirección de Recursos Humanos. Se asigna por usuario (ver Whitelist.tablero,
# igual que el rol) y decide qué ve esa persona al iniciar sesión (ver
# LoginView/MePermissionsView, que exponen el valor, y /dashboard/page.jsx en
# el front, que lo lee y renderiza el tablero en vez del dashboard normal).
TABLERO_CHOICES = [
    ("rh", "Tablero RH"),
    ("personalizable", "Tablero Personalizable"),
]


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
    # Vacío/None = sin tablero asignado, entra al dashboard normal.
    tablero = models.CharField(max_length=50, blank=True, null=True, choices=TABLERO_CHOICES)

    def __str__(self):
        return f"{self.email} - {self.rol.name}"


class RolUnScope(models.Model):
    """Restringe un rol a ver solo registros de ciertas Unidades de Negocio
    (columna `Cd UN` en las tablas de plantilla, ver `plantilla/models.py`).

    Contrato de seguridad (no cambiar esta semántica sin revisar todos los
    puntos de enforcement en `plantilla/views.py`):
      - Sin fila para un rol -> SIN restricción, ve todo (comportamiento de
        todos los roles existentes antes de este modelo).
      - Fila con `cd_un_codes` no vacío -> ve solo filas cuyo `cd_un` (con
        Trim()) esté en la lista.
      - Fila con `cd_un_codes == []` -> no ve NINGÚN registro. No se trata
        como "sin restricción": borrar el scope requiere borrar la fila
        (ver GroupSerializer.un_scope: null), no vaciar la lista.

    Se ancla a `cd_un` (código, 5 dígitos) y nunca al nombre de la UN: el
    nombre es texto libre de una tabla externa (ZAFIRO) con inconsistencias
    de redacción para un mismo código (ver authentication/un_catalog.py).
    """

    rol = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="un_scope_config")
    cd_un_codes = models.JSONField(default=list, encoder=DjangoJSONEncoder)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"{self.rol.name}: {self.cd_un_codes}"


class RolColumnScope(models.Model):
    """Restringe un rol a ver solo ciertas columnas de la tabla Plantilla
    Detalle (catálogo en `authentication/columnas_detalle_catalog.py`, mismo
    que `plantillaDetalleColumns.js` en el frontend).

    Mismo contrato que RolUnScope (no cambiar sin revisar el enforcement en
    `plantilla/views.py` — `_strip_columnas_filas`):
      - Sin fila para un rol -> SIN restricción, ve todas las columnas.
      - Fila con `columnas_permitidas` no vacío -> solo esas columnas MÁS el
        set fijo `COLUMNAS_DETALLE_SIEMPRE_INCLUIDAS` (identificadores/status
        que varias funciones de la UI necesitan para operar — no son
        configurables, se agregan siempre).
      - Fila con `columnas_permitidas == []` -> solo ve las columnas del set
        fijo de arriba, ninguna más.

    A diferencia del scope de UN (que filtra FILAS), esto recorta CAMPOS
    dentro de cada fila que el usuario sí puede ver — las columnas no
    permitidas ni siquiera viajan en la respuesta del servidor (no es un
    ocultamiento solo de interfaz).
    """

    rol = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="columnas_scope_config")
    columnas_permitidas = models.JSONField(default=list, encoder=DjangoJSONEncoder)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"{self.rol.name}: {self.columnas_permitidas}"


class ModoMantenimiento(models.Model):
    """Interruptor global de "modo mantenimiento" (singleton, pk=1).

    Con ``activo`` encendido, todo usuario de la whitelist que NO esté en
    ``exentos`` recibe 503 en la API (ver
    ``authentication.mantenimiento`` y ``permissions.SinMantenimiento``) y el
    front le muestra la pantalla de mantenimiento en cualquier ruta salvo la
    landing ``/``. Los superadmins también se bloquean si no se marcan; quien lo activa
    queda siempre exento para poder apagarlo.
    """

    activo = models.BooleanField(default=False)
    mensaje = models.CharField(max_length=300, blank=True, default="")
    exentos = models.ManyToManyField(Whitelist, blank=True, related_name="+")
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"Mantenimiento {'ACTIVO' if self.activo else 'apagado'}"


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
            # Sub-pestañas de Distribución Geográfica. El permiso de arriba
            # abre el tab; estos dos deciden cuál de sus dos vistas se ve, y
            # se exigen ADEMÁS del anterior (ver `extra_permission` en
            # HasModulePermission). Un rol puede tener una, la otra o ambas.
            ("view_plantilla_geografia_mapa", "Plantilla de Empleados: ver sub-tab Mapa Nacional (Distribución Geográfica)"),
            ("view_plantilla_geografia_torre", "Plantilla de Empleados: ver sub-tab Torre Caballito (Distribución Geográfica)"),
            ("view_plantilla_catalogos", "Plantilla de Empleados: ver tab Catálogos"),
            ("edit_plantilla_detalle", "Plantilla de Empleados: editar celdas en tab Detalle"),
            ("edit_datos_personales", "Plantilla de Empleados: editar Escolaridad/Contacto/Domicilio en Datos Personales"),
            ("view_plantilla_historico", "Plantilla de Empleados: consultar plantillas históricas (tab Detalle)"),
            ("view_anuencia_eliminados", "Plantilla de Empleados: ver y reactivar Anexos 2 eliminados (Anuencia)"),
            # Fotografía de empleado — permiso independiente por tab/componente
            # (un rol puede ver el tab pero no la fotografía dentro de él).
            ("view_plantilla_detalle_foto", "Plantilla de Empleados: ver fotografía en tab Detalle"),
            ("view_plantilla_estatus_nomina_foto", "Plantilla de Empleados: ver fotografía en tab Estatus Nómina"),
            ("view_plantilla_mov_posiciones_foto", "Plantilla de Empleados: ver fotografía en tab Mov. Posiciones"),
            ("view_plantilla_movimientos_foto", "Plantilla de Empleados: ver fotografía en tab Movimientos"),
            ("view_plantilla_bajas_foto", "Plantilla de Empleados: ver fotografía en tab Empleados Bajas"),
            ("view_plantilla_geografia_foto", "Plantilla de Empleados: ver fotografía en tab Distribución Geográfica"),
            # Expediente del personal — el modal de expediente (EmployeesModal)
            # se reutiliza en TODO el sistema: lo abre cualquier fila de
            # empleado, sin importar desde qué módulo. Un permiso por pestaña
            # permite recortar qué ve cada rol al abrirlo, en vez de que el
            # contenido dependa del módulo por el que entró.
            ("view_expediente_plaza", "Expediente del personal: ver pestaña Expediente"),
            ("view_expediente_datos_personales", "Expediente del personal: ver pestaña Datos Personales"),
            ("view_expediente_historial_movimientos", "Expediente del personal: ver pestaña Historial de Movimientos"),
            ("view_expediente_historial_posicion", "Expediente del personal: ver pestaña Historial de Posición"),
            # Ocupación de Plazas por Oficio
            ("view_ocupacion_sankey", "Ocupación de Plazas: ver tab Sankey"),
            ("view_ocupacion_tabla", "Ocupación de Plazas: ver tab Tabla"),
            ("view_ocupacion_estadisticas", "Ocupación de Plazas: ver tab Estadísticas"),
            ("edit_ocupacion_plazas", "Ocupación de Plazas: editar asignación de plazas"),
            # Rediseño 2026-09: reemplaza sankey/tabla/estadisticas (vista pasó
            # a listar solicitudes de nueva creación con Resolución/Notificación).
            ("view_ocupacion_solicitudes", "Ocupación de Plazas: ver tabla de Solicitudes de Nueva Creación"),
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


class TableroLayout(models.Model):
    """Layout guardado del tablero personalizable (ver Whitelist.tablero ==
    'personalizable' y TableroLayoutView). A diferencia de FiltroGuardado
    (plantilla/models.py, N filtros por usuario), aquí solo existe "el" layout
    actual de cada quien, de ahí OneToOne en vez de ForeignKey.

    `widgets` guarda la misma forma que espera react-grid-layout
    (i/x/y/w/h) más un campo propio `type` que identifica qué widget montar:
    [{"i": "...", "type": "vacantes_por_nivel", "x": 0, "y": 0, "w": 4, "h": 4}, ...]
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tablero_layout"
    )
    widgets = models.JSONField(default=list, encoder=DjangoJSONEncoder)
    # Nombre de cada escritorio, por índice (el `page` de cada widget):
    # ["Vacancia", "", "Plantilla"]. "" = sin nombre propio (el front muestra
    # "Escritorio N"). Su longitud también conserva los escritorios vacíos
    # creados a mano, que no se pueden deducir de `widgets`.
    escritorios = models.JSONField(default=list)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario} - {len(self.widgets)} widgets"
