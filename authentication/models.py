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


# Versión vigente del aviso de confidencialidad (el texto vive en el front,
# components/system/TerminosGate.jsx). Cambiarla obliga a todos a aceptarlo de nuevo.
TERMINOS_VERSION = "2026-10"


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
    # Aviso de confidencialidad y términos de uso: se muestra al entrar y no
    # se puede usar el sistema sin aceptarlo. Se guarda la versión aceptada
    # para poder volver a pedirlo si el texto cambia (ver TERMINOS_VERSION).
    terminos_aceptados_at = models.DateTimeField(null=True, blank=True)
    # null=True (no default ""): la BD es compartida con otra máquina cuyo código
    # aún no conoce estas columnas y debe poder insertar usuarios sin ellas.
    terminos_version = models.CharField(max_length=20, blank=True, null=True)
    terminos_ip = models.CharField(max_length=64, blank=True, null=True)

    @property
    def terminos_vigentes_aceptados(self):
        return bool(self.terminos_aceptados_at) and self.terminos_version == TERMINOS_VERSION

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


class RolUaScope(models.Model):
    """Restringe un rol a ver solo registros de ciertas Unidades
    Administrativas (columna `Cd UA`, 3 dígitos — ver authentication/ua_catalog.py).

    Mismo contrato que RolUnScope: sin fila = sin restricción por UA; lista no
    vacía = solo esas UAs; lista vacía = ningún registro.

    Se suma al alcance por UN, no lo reemplaza: el rol de una aduana lleva
    RolUnScope=[00100] Y RolUaScope=[su UA]. Como cada UA pertenece a una sola
    UN, las dos restricciones nunca se contradicen.

    Cierre por defecto: una vista que no declare `ua_scope` se niega a los
    roles con este alcance (ver HasModulePermission) — una vista que solo sabe
    recortar por UN le mostraría a una aduana toda su Dirección General.
    """

    rol = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="ua_scope_config")
    cd_ua_codes = models.JSONField(default=list, encoder=DjangoJSONEncoder)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"{self.rol.name}: {self.cd_ua_codes}"


class RolPerfil(models.Model):
    """Lugar de un rol (Group) dentro del árbol de roles.

    Tipos:
      - TITULAR: uno por unidad (13 Unidades de Negocio + sus UAs adscritas =
        65). Los crea el sistema (`manage.py crear_roles_unidades`), no se
        renombran ni se borran, y admiten UNA sola persona: el titular de la
        unidad. El de una UA adscrita cuelga del titular de su UN.
      - TRANSVERSAL: rol raíz sin unidad propia (ej. "Recursos Humanos"), para
        áreas que ven toda la ANAM. Sin cupo de usuarios.
      - SUBROL: cuelga de cualquier otro rol; varias personas comparten sus
        permisos.

    REGLA DEL ÁRBOL (única, vale para todo hijo): un rol nunca tiene más que
    su padre — ni permisos (se valida al guardar, y quitarle uno al padre se
    lo quita a toda su descendencia: GroupSerializer) ni alcance de datos (se
    resuelve en vivo intersectando con los ancestros: authentication.scoping).

    Un Group sin RolPerfil es un rol anterior a este modelo y se trata como
    TRANSVERSAL raíz.
    """

    TITULAR = "titular"
    TRANSVERSAL = "transversal"
    SUBROL = "subrol"
    TIPO_CHOICES = [(TITULAR, "Titular de unidad"), (TRANSVERSAL, "Transversal"), (SUBROL, "Subrol")]

    rol = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="perfil_rol")
    # PROTECT: borrar un padre con hijos dejaría a los hijos sin el techo de
    # permisos/alcance que los limitaba. Hay que reubicarlos o borrarlos antes.
    padre = models.ForeignKey(
        Group, on_delete=models.PROTECT, null=True, blank=True, related_name="perfiles_hijos"
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default=TRANSVERSAL)
    # Unidad que representa un TITULAR (llave de idempotencia del comando que
    # los crea; el recorte real son RolUnScope/RolUaScope). El titular de una
    # UN completa lleva cd_ua="" y el de una UA adscrita su código. Los demás
    # tipos dejan ambos en NULL, que no chocan con la restricción de abajo.
    cd_un = models.CharField(max_length=5, blank=True, null=True)
    cd_ua = models.CharField(max_length=3, blank=True, null=True)
    # None = sin límite. Los TITULAR llevan 1.
    max_usuarios = models.PositiveSmallIntegerField(null=True, blank=True)
    es_sistema = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cd_un", "cd_ua"], name="rolperfil_unidad_unica")
        ]

    def __str__(self):
        return f"{self.rol.name} ({self.tipo})"


def ancestros_de_rol(rol):
    """Lista [padre, abuelo, ...] del rol. Corta ante un ciclo (no debería
    existir: GroupSerializer lo impide) en vez de girar para siempre."""
    ancestros = []
    vistos = {rol.pk}
    actual = rol
    while True:
        perfil = RolPerfil.objects.filter(rol=actual).select_related("padre").first()
        padre = perfil.padre if perfil else None
        if padre is None or padre.pk in vistos:
            return ancestros
        ancestros.append(padre)
        vistos.add(padre.pk)
        actual = padre


def descendientes_de_rol(rol):
    """Todos los roles que cuelgan de `rol`, a cualquier profundidad."""
    descendientes = []
    frontera = [rol.pk]
    vistos = {rol.pk}
    while frontera:
        hijos = list(
            Group.objects.filter(perfil_rol__padre_id__in=frontera).exclude(pk__in=vistos)
        )
        frontera = [h.pk for h in hijos]
        vistos.update(frontera)
        descendientes.extend(hijos)
    return descendientes


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
            # Sub-pestañas de Mov. Posiciones: el permiso del tab solo lo abre;
            # estos deciden qué se ve dentro (el backend los exige con
            # `extra_permission`, igual que las de Distribución Geográfica).
            ("view_plantilla_mov_posiciones_tabla", "Plantilla de Empleados: ver sub-tab Tabla Principal (Mov. Posiciones)"),
            ("view_plantilla_mov_posiciones_cuadros", "Plantilla de Empleados: ver sub-tab Cuadros Vacancia (Mov. Posiciones)"),
            ("view_plantilla_mov_posiciones_alineacion", "Plantilla de Empleados: ver sub-tab Comprobar Alineación (Mov. Posiciones)"),
            ("view_plantilla_mov_posiciones_aduanas", "Plantilla de Empleados: ver sub-tab Aduanas Ocupación vs Vacantes (Mov. Posiciones)"),
            ("view_plantilla_mov_posiciones_anuencia", "Plantilla de Empleados: ver sub-tab Anuencia (Mov. Posiciones)"),
            ("edit_plantilla_detalle", "Plantilla de Empleados: editar celdas en tab Detalle"),
            ("edit_datos_personales", "Plantilla de Empleados: editar Escolaridad/Contacto/Domicilio en Datos Personales"),
            ("view_plantilla_historico", "Plantilla de Empleados: consultar plantillas históricas (tab Detalle)"),
            # Sin este permiso el rol ve SIEMPRE la plantilla oficial (sin Laudos,
            # 1039 ni PASEM) y no se le muestra el switch para apagarla.
            ("view_plantilla_switch_oficial", "Plantilla de Empleados: usar el switch Plantilla Oficial (tab Detalle)"),
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


class MemoriaColumnas(models.Model):
    """Hasta 3 "memorias" de columnas visibles por usuario y por tabla (botón Configurar
    columnas). `tabla` identifica la tabla (plantilla_detalle, bajas, mov_posiciones,
    movimientos, alineacion): cada una tiene su propio catálogo de columnas, así que una
    memoria de Plantilla Detalle se aplica a esa tabla dondequiera que aparezca (pestaña o
    modales del tablero).

    Para `plantilla_detalle` las columnas se recortan al guardar contra RolColumnScope (ver
    MemoriasColumnasView): una memoria nunca puede contener columnas que el rol no permite.
    """

    SLOTS = (1, 2, 3)

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memorias_columnas")
    tabla = models.CharField(max_length=40)
    slot = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=40, blank=True, default="")
    columnas = models.JSONField(default=list, encoder=DjangoJSONEncoder)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "tabla", "slot"], name="uniq_memoria_columnas_slot"),
        ]

    def __str__(self):
        return f"{self.usuario} · {self.tabla} · {self.slot}"


class DescargaExcelLog(models.Model):
    """Bitácora de archivos Excel generados por los usuarios (auditoría).

    Una fila por cada Excel generado. Además de QUIÉN y CUÁNDO, guarda lo
    necesario para reconstruir el archivo: columnas, filtros que tenía la
    tabla, si llevaba fotografías o datos personales y, en `snapshot`, la
    ruta (relativa a MEDIA_ROOT) de una copia comprimida de las filas tal
    como salieron — la plantilla cambia a diario, así que sin esa copia
    "regenerar" daría los datos de hoy, no los que el usuario se llevó.
    Ver plantilla.views (`_registrar_descarga_excel`, RegenerarDescargaExcelView).
    """

    MODO_ACTUAL = "actual"
    MODO_HISTORICO = "historico"

    email = models.EmailField(db_index=True)
    rol = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modulo = models.CharField(max_length=200, default="plantilla_detalle")
    modo = models.CharField(max_length=12, default=MODO_ACTUAL)
    # Fecha consultada cuando el Excel salió de "Consultar plantillas pasadas".
    fecha_historica = models.CharField(max_length=10, blank=True, default="")
    total_filas = models.PositiveIntegerField(default=0)
    columnas = models.JSONField(default=list)  # [{key, label}] en el orden del archivo
    filtros = models.JSONField(default=dict)   # descripción de los filtros activos (la manda el front)
    incluyo_fotos = models.BooleanField(default=False)
    incluyo_datos_personales = models.BooleanField(default=False)
    nombre_archivo = models.CharField(max_length=255, blank=True, default="")
    ip = models.CharField(max_length=64, blank=True, default="")
    snapshot = models.CharField(max_length=255, blank=True, default="")
    # Cuando un administrador vuelve a generar el archivo de otro usuario desde
    # el historial, esa generación también se registra y apunta a la original.
    regenerada_de = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="regeneraciones"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "created_at"])]

    def __str__(self):
        return f"{self.email} · {self.modulo} · {self.created_at:%Y-%m-%d %H:%M}"
