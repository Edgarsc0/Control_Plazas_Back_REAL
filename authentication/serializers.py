from django.contrib.auth.models import Group, Permission
from rest_framework import serializers
from .models import ModulePermission, Whitelist, VerificationCode


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

    class Meta:
        model = Whitelist
        fields = ['id', 'email', 'rol', 'rol_nombre', 'ua', 'ua_nombre', 'activo']

class VerificationCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationCode
        fields = ['email', 'code']
