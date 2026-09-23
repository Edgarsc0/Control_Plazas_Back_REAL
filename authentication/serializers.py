from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .columnas_detalle_catalog import normalizar_columna_detalle
from .models import ModulePermission, RolColumnScope, RolUnScope, Whitelist, sincronizar_usuario_django
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

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'permissions', 'permission_ids', 'user_count',
            'un_scope', 'columnas_detalle',
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
        return data

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

    def create(self, validated_data):
        un_scope = validated_data.pop('un_scope', serializers.empty)
        columnas_detalle = validated_data.pop('columnas_detalle', serializers.empty)
        instance = super().create(validated_data)
        self._aplicar_un_scope(instance, un_scope)
        self._aplicar_columnas_scope(instance, columnas_detalle)
        return instance

    def update(self, instance, validated_data):
        un_scope = validated_data.pop('un_scope', serializers.empty)
        columnas_detalle = validated_data.pop('columnas_detalle', serializers.empty)
        instance = super().update(instance, validated_data)
        self._aplicar_un_scope(instance, un_scope)
        self._aplicar_columnas_scope(instance, columnas_detalle)
        return instance

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
        ]
        read_only_fields = ['debe_cambiar_password']

    def get_tiene_password(self, obj):
        return bool(obj.user and obj.user.has_usable_password())

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
