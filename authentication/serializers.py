from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .columnas_detalle_catalog import normalizar_columna_detalle
from .models import (
    ModulePermission,
    RolColumnScope,
    RolPerfil,
    RolUaScope,
    RolUnScope,
    Whitelist,
    descendientes_de_rol,
    sincronizar_usuario_django,
)
from .scoping import alcance_efectivo_de_rol
from .ua_catalog import normalizar_cd_ua, titular_con_alcance_libre, un_de_ua
from .un_catalog import normalizar_cd_un


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.ReadOnlyField(source='content_type.app_label')
    full_codename = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'app_label', 'full_codename']

    def get_full_codename(self, obj):
        return f"{obj.content_type.app_label}.{obj.codename}"


class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    # Solo permisos del catálogo de negocio (ModulePermission) son asignables desde
    # esta API — evita otorgar por accidente permisos internos de Django (admin,
    # sessions, contenttypes, etc). El queryset real se resuelve en __init__ (a
    # nivel de módulo, en tiempo de import, la tabla auth_permission puede no
    # estar lista todavía).
    permission_ids = serializers.PrimaryKeyRelatedField(
        source='permissions',
        queryset=Permission.objects.none(),
        many=True,
        write_only=True,
        required=False,
    )
    user_count = serializers.SerializerMethodField()
    # Alcance de datos por Unidad de Negocio (ver RolUnScope). No es un campo
    # real de Group (vive en una tabla aparte, OneToOne) — se resuelve a mano
    # en to_representation/create/update, nunca vía `source=`.
    # null = sin restricción (ve todo, comportamiento de hoy); lista
    # (incluida vacía) = restringido a esos códigos, ver RolUnScope.
    # write_only=True a propósito: no es un atributo real de Group (Group no
    # tiene `.un_scope`, vive en RolUnScope vía `un_scope_config`), así que
    # dejar que el ModelSerializer intente leerlo solo en to_representation
    # lanzaría AttributeError. En su lugar, to_representation lo agrega a
    # mano después de llamar a super().
    un_scope = serializers.ListField(
        child=serializers.CharField(), allow_null=True, required=False, write_only=True
    )
    # Alcance por columnas de Plantilla Detalle (ver RolColumnScope) — mismo
    # patrón exacto que un_scope, solo que recorta CAMPOS dentro de cada fila
    # en vez de filas completas. null = sin restricción (ve todas las
    # columnas); lista (incluida vacía) = solo esas columnas + el set fijo
    # de identificadores que la UI necesita para operar (ver
    # COLUMNAS_DETALLE_SIEMPRE_INCLUIDAS).
    columnas_detalle = serializers.ListField(
        child=serializers.CharField(), allow_null=True, required=False, write_only=True
    )
    # Alcance por Unidad Administrativa (ver RolUaScope) — mismo patrón que
    # un_scope. Se aplica además del de UN.
    ua_scope = serializers.ListField(
        child=serializers.CharField(), allow_null=True, required=False, write_only=True
    )
    # Rol padre en el árbol (ver RolPerfil). Solo se acepta al CREAR: mover un
    # rol de padre cambiaría de golpe su techo de permisos y de alcance.
    padre = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), allow_null=True, required=False, write_only=True
    )

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'permissions', 'permission_ids', 'user_count',
            'un_scope', 'columnas_detalle', 'ua_scope', 'padre',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # many=True envuelve el campo en ManyRelatedField; la validación real
        # de cada id ocurre en child_relation, no en el wrapper.
        self.fields['permission_ids'].child_relation.queryset = ModulePermission.catalog_queryset()

    def get_user_count(self, obj):
        return obj.user_set.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        scope = getattr(instance, 'un_scope_config', None)
        data['un_scope'] = sorted(scope.cd_un_codes) if scope else None
        columnas_scope = getattr(instance, 'columnas_scope_config', None)
        data['columnas_detalle'] = sorted(columnas_scope.columnas_permitidas) if columnas_scope else None
        ua_scope = getattr(instance, 'ua_scope_config', None)
        data['ua_scope'] = sorted(ua_scope.cd_ua_codes) if ua_scope else None
        # Un rol sin RolPerfil es anterior al árbol: transversal raíz.
        perfil = getattr(instance, 'perfil_rol', None)
        data['padre'] = perfil.padre_id if perfil else None
        data['tipo'] = perfil.tipo if perfil else RolPerfil.TRANSVERSAL
        data['cd_un'] = perfil.cd_un if perfil else None
        data['cd_ua'] = perfil.cd_ua if perfil else None
        data['max_usuarios'] = perfil.max_usuarios if perfil else None
        data['es_sistema'] = bool(perfil and perfil.es_sistema)
        # Titular al que sí se le puede cambiar el alcance por UN (ver
        # UN_TITULAR_ALCANCE_LIBRE): hoy, solo el de la oficina del titular de la ANAM.
        data['alcance_editable'] = bool(
            perfil and perfil.es_sistema and titular_con_alcance_libre(perfil.cd_un, perfil.cd_ua)
        )
        return data

    # ------------------------------------------------------------------
    # Reglas del árbol de roles (ver RolPerfil)
    # ------------------------------------------------------------------
    def _perfil(self, rol):
        return RolPerfil.objects.filter(rol=rol).select_related('padre').first() if rol else None

    def validate_padre(self, value):
        if value is not None and value.name.lower() == 'superadmin':
            raise serializers.ValidationError('El rol superadmin no puede tener subroles.')
        return value

    def validate_ua_scope(self, value):
        if value is None:
            return None
        if self.instance is not None and self.instance.name.lower() == 'superadmin':
            raise serializers.ValidationError(
                'No se puede restringir por Unidad Administrativa al rol superadmin.'
            )
        codigos = []
        for crudo in value:
            codigo = normalizar_cd_ua(crudo)
            if codigo is None:
                raise serializers.ValidationError(
                    f"'{crudo}' no es un código de Unidad Administrativa reconocido."
                )
            codigos.append(codigo)
        return sorted(set(codigos))

    def validate(self, attrs):
        instance = self.instance
        perfil = self._perfil(instance)

        if instance is not None:
            # El padre se fija al crear (ver el campo `padre`).
            if 'padre' in attrs and attrs['padre'] != (perfil.padre if perfil else None):
                raise serializers.ValidationError(
                    {'padre': 'No se puede cambiar el rol padre de un rol existente.'}
                )
            attrs.pop('padre', None)
            padre = perfil.padre if perfil else None
        else:
            padre = attrs.get('padre')

        if perfil and perfil.es_sistema:
            # Los titulares de unidad los define el sistema: nombre y alcance
            # fijos. Sus permisos y columnas sí se personalizan.
            if 'name' in attrs and attrs['name'] != instance.name:
                raise serializers.ValidationError(
                    {'name': 'El nombre de un rol titular de unidad no se puede cambiar.'}
                )
            un_actual = getattr(instance, 'un_scope_config', None)
            ua_actual = getattr(instance, 'ua_scope_config', None)
            if (
                'un_scope' in attrs
                and not titular_con_alcance_libre(perfil.cd_un, perfil.cd_ua)
                and attrs['un_scope'] != (sorted(un_actual.cd_un_codes) if un_actual else None)
            ):
                raise serializers.ValidationError(
                    {'un_scope': 'El alcance de un rol titular lo define su unidad y no se puede cambiar.'}
                )
            if 'ua_scope' in attrs and attrs['ua_scope'] != (
                sorted(ua_actual.cd_ua_codes) if ua_actual else None
            ):
                raise serializers.ValidationError(
                    {'ua_scope': 'El alcance de un rol titular lo define su unidad y no se puede cambiar.'}
                )

        if padre is not None:
            self._validar_contra_padre(attrs, padre)

        self._validar_ua_dentro_de_un(attrs, instance, padre)
        return attrs

    def _validar_contra_padre(self, attrs, padre):
        """Un hijo nunca tiene más que su padre (permisos ni alcance)."""
        if 'permissions' in attrs:
            del_padre = set(padre.permissions.values_list('id', flat=True))
            sobrantes = [p.name for p in attrs['permissions'] if p.id not in del_padre]
            if sobrantes:
                raise serializers.ValidationError(
                    {
                        'permission_ids': (
                            f'Un subrol solo puede tener permisos de su rol padre ("{padre.name}"). '
                            f'No los tiene: {", ".join(sorted(sobrantes))}.'
                        )
                    }
                )

        for campo, modelo, columna, etiqueta in (
            ('un_scope', RolUnScope, 'cd_un_codes', 'Unidades de Negocio'),
            ('ua_scope', RolUaScope, 'cd_ua_codes', 'Unidades Administrativas'),
            ('columnas_detalle', RolColumnScope, 'columnas_permitidas', 'columnas'),
        ):
            propio = attrs.get(campo)
            if propio is None:
                continue  # sin restricción propia: hereda la del padre en vivo
            techo = alcance_efectivo_de_rol(padre, modelo, columna)
            if techo is not None and not set(propio) <= techo:
                fuera = ", ".join(sorted(set(propio) - techo))
                raise serializers.ValidationError(
                    {campo: f'Fuera del alcance del rol padre ("{padre.name}"): {etiqueta} {fuera}.'}
                )

    def _validar_ua_dentro_de_un(self, attrs, instance, padre):
        """Cada UA elegida debe pertenecer a una UN que el rol sí puede ver —
        si no, las dos restricciones se anularían entre sí y el rol quedaría
        sin ver nada sin que nadie entienda por qué."""
        ua_scope = attrs.get('ua_scope')
        if not ua_scope:
            return
        if 'un_scope' in attrs:
            un_propio = attrs['un_scope']
        else:
            actual = getattr(instance, 'un_scope_config', None) if instance else None
            un_propio = sorted(actual.cd_un_codes) if actual else None
        un_efectivo = None if un_propio is None else set(un_propio)
        if padre is not None:
            del_padre = alcance_efectivo_de_rol(padre, RolUnScope, 'cd_un_codes')
            if del_padre is not None:
                un_efectivo = del_padre if un_efectivo is None else un_efectivo & del_padre
        if un_efectivo is None:
            return
        fuera = [ua for ua in ua_scope if un_de_ua(ua) not in un_efectivo]
        if fuera:
            raise serializers.ValidationError(
                {
                    'ua_scope': (
                        'Estas Unidades Administrativas no pertenecen a las Unidades de Negocio '
                        f'que el rol puede ver: {", ".join(fuera)}.'
                    )
                }
            )

    def validate_un_scope(self, value):
        if value is None:
            return None
        # El resolver de scope (authentication.scoping) ya ignora cualquier
        # scope guardado en el rol superadmin (is_superuser corta primero),
        # así que guardarle uno aquí sería config muerta que engaña al
        # administrador haciéndole creer que sí restringe algo.
        if self.instance is not None and self.instance.name.lower() == 'superadmin':
            raise serializers.ValidationError(
                'No se puede restringir por Unidad de Negocio al rol superadmin.'
            )
        codigos = []
        for crudo in value:
            codigo = normalizar_cd_un(crudo)
            if codigo is None:
                raise serializers.ValidationError(
                    f"'{crudo}' no es un código de Unidad de Negocio reconocido."
                )
            codigos.append(codigo)
        return sorted(set(codigos))

    def validate_columnas_detalle(self, value):
        if value is None:
            return None
        if self.instance is not None and self.instance.name.lower() == 'superadmin':
            raise serializers.ValidationError(
                'No se puede restringir columnas de Plantilla Detalle al rol superadmin.'
            )
        columnas = []
        for cruda in value:
            columna = normalizar_columna_detalle(cruda)
            if columna is None:
                raise serializers.ValidationError(f"'{cruda}' no es una columna reconocida.")
            columnas.append(columna)
        return sorted(set(columnas))

    @transaction.atomic
    def create(self, validated_data):
        un_scope = validated_data.pop('un_scope', serializers.empty)
        columnas_detalle = validated_data.pop('columnas_detalle', serializers.empty)
        ua_scope = validated_data.pop('ua_scope', serializers.empty)
        padre = validated_data.pop('padre', None)
        instance = super().create(validated_data)
        # Desde la API solo nacen subroles (con padre) o transversales (sin
        # él); los titulares de unidad los crea `crear_roles_unidades`.
        RolPerfil.objects.create(
            rol=instance,
            padre=padre,
            tipo=RolPerfil.SUBROL if padre else RolPerfil.TRANSVERSAL,
        )
        self._aplicar_un_scope(instance, un_scope)
        self._aplicar_columnas_scope(instance, columnas_detalle)
        self._aplicar_ua_scope(instance, ua_scope)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        un_scope = validated_data.pop('un_scope', serializers.empty)
        columnas_detalle = validated_data.pop('columnas_detalle', serializers.empty)
        ua_scope = validated_data.pop('ua_scope', serializers.empty)
        cambian_permisos = 'permissions' in validated_data
        instance = super().update(instance, validated_data)
        self._aplicar_un_scope(instance, un_scope)
        self._aplicar_columnas_scope(instance, columnas_detalle)
        self._aplicar_ua_scope(instance, ua_scope)
        if cambian_permisos:
            self._podar_descendencia(instance)
        return instance

    def _podar_descendencia(self, instance):
        """Quitarle un permiso a un rol se lo quita a toda su descendencia:
        ningún hijo puede conservar algo que su padre ya no tiene. (Agregarle
        uno al padre NO se lo da a los hijos — eso se decide rol por rol.)"""
        permitidos = set(instance.permissions.values_list('id', flat=True))
        for hijo in descendientes_de_rol(instance):
            sobrantes = list(hijo.permissions.exclude(id__in=permitidos))
            if sobrantes:
                hijo.permissions.remove(*sobrantes)

    def _aplicar_ua_scope(self, instance, ua_scope):
        """Mismo contrato que _aplicar_un_scope, para RolUaScope."""
        if ua_scope is serializers.empty:
            return
        request = self.context.get('request')
        usuario = getattr(request, 'user', None) if request else None
        if ua_scope is None:
            RolUaScope.objects.filter(rol=instance).delete()
        else:
            RolUaScope.objects.update_or_create(
                rol=instance,
                defaults={'cd_ua_codes': ua_scope, 'actualizado_por': usuario},
            )

    def _aplicar_un_scope(self, instance, un_scope):
        """`un_scope` ausente del payload -> no se toca el scope existente
        (para que un PATCH parcial, ej. solo el nombre, no borre uno ya
        configurado). `None` explícito -> borra el scope (rol sin
        restricción). Lista (incluida vacía) -> la guarda tal cual."""
        if un_scope is serializers.empty:
            return
        request = self.context.get('request')
        usuario = getattr(request, 'user', None) if request else None
        with transaction.atomic():
            if un_scope is None:
                RolUnScope.objects.filter(rol=instance).delete()
                # Que la respuesta de este mismo guardado ya diga "sin
                # restricción" (la relación quedó cacheada en la instancia).
                instance._state.fields_cache.pop('un_scope_config', None)
            else:
                RolUnScope.objects.update_or_create(
                    rol=instance,
                    defaults={'cd_un_codes': un_scope, 'actualizado_por': usuario},
                )

    def _aplicar_columnas_scope(self, instance, columnas_detalle):
        """Mismo contrato que _aplicar_un_scope, para RolColumnScope."""
        if columnas_detalle is serializers.empty:
            return
        request = self.context.get('request')
        usuario = getattr(request, 'user', None) if request else None
        with transaction.atomic():
            if columnas_detalle is None:
                RolColumnScope.objects.filter(rol=instance).delete()
            else:
                RolColumnScope.objects.update_or_create(
                    rol=instance,
                    defaults={'columnas_permitidas': columnas_detalle, 'actualizado_por': usuario},
                )


class WhitelistSerializer(serializers.ModelSerializer):
    ua_nombre = serializers.ReadOnlyField(source='ua.nombre')
    rol_nombre = serializers.ReadOnlyField(source='rol.name')
    # El alta y el restablecimiento de contraseña son administrados: no hay
    # correo institucional disponible para mandar ligas de reseteo, así que
    # quien tiene manage_usuarios la define aquí y se la comunica al titular
    # por un canal interno. Nunca se lee de vuelta (write_only).
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={'input_type': 'password'}
    )
    tiene_password = serializers.SerializerMethodField()

    class Meta:
        model = Whitelist
        fields = [
            'id', 'email', 'rol', 'rol_nombre', 'ua', 'ua_nombre', 'activo',
            'password', 'tiene_password', 'debe_cambiar_password', 'tablero',
            'terminos_aceptados_at',
        ]
        read_only_fields = ['debe_cambiar_password', 'terminos_aceptados_at']

    def get_tiene_password(self, obj):
        return bool(obj.user and obj.user.has_usable_password())

    def validate_rol(self, rol):
        """Cupo de usuarios del rol (RolPerfil.max_usuarios): los titulares de
        unidad admiten una sola persona. Cuentan también los inactivos — para
        relevar al titular hay que reasignar o dar de baja al anterior, no
        basta con desactivarlo, o el rol acumularía dueños en silencio."""
        perfil = RolPerfil.objects.filter(rol=rol).first()
        if not perfil or perfil.max_usuarios is None:
            return rol
        ocupantes = Whitelist.objects.filter(rol=rol)
        if self.instance is not None:
            ocupantes = ocupantes.exclude(pk=self.instance.pk)
        if ocupantes.count() >= perfil.max_usuarios:
            actuales = ", ".join(ocupantes.values_list('email', flat=True))
            raise serializers.ValidationError(
                f'El rol "{rol.name}" admite {perfil.max_usuarios} usuario(s) y ya lo ocupa: {actuales}. '
                'Reasigna primero a esa persona, o crea un subrol para compartir sus permisos.'
            )
        return rol

    def validate_password(self, value):
        if value:
            try:
                django_validate_password(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', '')
        entry = super().create(validated_data)
        self._aplicar_password(entry, password)
        return entry

    def update(self, instance, validated_data):
        password = validated_data.pop('password', '')
        entry = super().update(instance, validated_data)
        self._aplicar_password(entry, password)
        return entry

    def _aplicar_password(self, entry, password):
        """Deja el ``User`` de Django alineado con la entrada de whitelist y,
        si el admin mandó contraseña, la establece.

        Se llama siempre (aunque no venga contraseña) porque también es lo que
        propaga un cambio de rol a los permisos de un usuario con sesión
        abierta, sin esperar a que vuelva a loguearse."""
        user = sincronizar_usuario_django(entry)

        if not password:
            return

        user.set_password(password)
        user.save(update_fields=['password'])

        # Toda contraseña puesta por un administrador nace "prestada": la
        # conoce alguien más que el titular, así que se le exige cambiarla al
        # entrar. ChangePasswordView es quien apaga esta bandera.
        entry.debe_cambiar_password = True
        entry.save(update_fields=['debe_cambiar_password'])

        # Un restablecimiento debe cortar las sesiones que siguieran vivas con
        # la contraseña anterior; el token de DRF no caduca solo.
        Token.objects.filter(user=user).delete()
