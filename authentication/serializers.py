from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import ModulePermission, Whitelist, sincronizar_usuario_django


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

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'permission_ids', 'user_count']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # many=True envuelve el campo en ManyRelatedField; la validación real
        # de cada id ocurre en child_relation, no en el wrapper.
        self.fields['permission_ids'].child_relation.queryset = ModulePermission.catalog_queryset()

    def get_user_count(self, obj):
        return obj.user_set.count()


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
            'password', 'tiene_password', 'debe_cambiar_password',
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
