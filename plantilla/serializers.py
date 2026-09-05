from rest_framework import serializers
from .models import (
    AnuenciaAnexo,
    AnuenciaAnexo3Version,
    AnuenciaAnexoCambio,
    AnuenciaJustificacionCatalogo,
    CatAcciones,
    CatAccionesMotivos,
    CatNivelJerarquicoPlaza,
    CatPtoFunc,
    CpTblMovCompleto290526,
    OrganigramaAnam,
    RcCatCodPresupuestal,
)

class CpTblMovCompleto290526Serializer(serializers.ModelSerializer):
    class Meta:
        model = CpTblMovCompleto290526
        # Dynamically exclude specified columns to prevent DRF errors if they do not exist
        exclude = [
            f for f in ['columna_c', 'columna_d', 'fecha_descarga']
            if f in [field.name for field in CpTblMovCompleto290526._meta.get_fields()]
        ]


# Nombres de campo exactos que emite CpTblMovCompleto290526Serializer — fuente
# única de verdad para MovimientosPersonalListView, que sirve estas filas vía
# queryset.values(*CP_TBL_MOV_COMPLETO_FIELDS) en vez de instanciar el
# serializer (155k+ filas en la tabla; ~2.7x más lento con ModelSerializer,
# medido con datos reales — ver arquitectura-serializers-listas.md).
CP_TBL_MOV_COMPLETO_FIELDS = list(CpTblMovCompleto290526Serializer().fields)


class CatAccionesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatAcciones
        fields = "__all__"
        read_only_fields = ["modificado_por", "fecha_modificacion"]


class CatAccionesMotivosSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatAccionesMotivos
        fields = "__all__"
        read_only_fields = ["modificado_por", "fecha_modificacion"]


class CatPtoFuncSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatPtoFunc
        fields = "__all__"
        read_only_fields = ["modificado_por", "fecha_modificacion"]


class RcCatCodPresupuestalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RcCatCodPresupuestal
        # Se excluye "pk" (el CompositePrimaryKey de Django): ya se expone
        # como codigo_presupuestal + escala, no hace falta duplicarlo.
        fields = [
            "codigo_presupuestal", "escala", "nivel", "smb", "smn",
            "nivel_jerarquico", "modificado_por", "fecha_modificacion",
        ]
        read_only_fields = ["modificado_por", "fecha_modificacion"]


class OrganigramaAnamSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganigramaAnam
        fields = "__all__"
        read_only_fields = ["modificado_por", "fecha_modificacion"]


class CatNivelJerarquicoPlazaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatNivelJerarquicoPlaza
        fields = [
            "plaza", "nivel_jerarquico", "descripcion_nivel_jerarquico",
            "nvl_direc_origen", "modificado_por", "fecha_modificacion",
        ]
        # nivel_jerarquico se deriva de descripcion_nivel_jerarquico en el modelo;
        # nvl_direc_origen sólo lo escribe la sincronización automática de ZAFIRO.
        read_only_fields = ["nivel_jerarquico", "nvl_direc_origen", "modificado_por", "fecha_modificacion"]


# Campos de "quién" en vez del FK crudo — un historial que sólo mostrara el
# id de usuario no serviría de mucho en pantalla (ver AnuenciaHistorialModal.jsx).
class _UsuarioAuditoriaMixin(serializers.ModelSerializer):
    creado_por_email = serializers.ReadOnlyField(source="creado_por.email")
    actualizado_por_email = serializers.ReadOnlyField(source="actualizado_por.email")
    generado_por_email = serializers.ReadOnlyField(source="generado_por.email")
    eliminado_por_email = serializers.ReadOnlyField(source="eliminado_por.email")


class AnuenciaAnexoListSerializer(_UsuarioAuditoriaMixin):
    """Fila del historial (sub-tab Anuencia) — sólo el resumen del libro, sin
    el contenido de sus hojas, para que listar el historial no transfiera el
    cuadro entero de cada anexo (ver AnuenciaAnexoDetailSerializer para eso)."""

    total_hojas = serializers.SerializerMethodField()
    total_filas = serializers.SerializerMethodField()
    unidades_administrativas = serializers.SerializerMethodField()

    class Meta:
        model = AnuenciaAnexo
        fields = [
            "id", "nombre_archivo", "total_hojas", "total_filas", "unidades_administrativas",
            "creado_por_email", "creado_en",
            "actualizado_por_email", "actualizado_en",
            "generado_por_email", "generado_en", "veces_generado",
            "eliminado", "eliminado_en", "eliminado_por_email",
        ]

    def get_total_hojas(self, obj):
        return len(obj.hojas or [])

    def get_total_filas(self, obj):
        """Plazas de TODO el libro, sumando las de cada hoja."""
        return sum(len(hoja.get("filas") or []) for hoja in (obj.hojas or []))

    def get_unidades_administrativas(self, obj):
        """UAs distintas del libro, en orden de aparición — es lo que
        identifica al anexo de un vistazo en el historial."""
        vistas = []
        for hoja in obj.hojas or []:
            ua = (hoja.get("unidad_administrativa") or "").strip()
            if ua and ua not in vistas:
                vistas.append(ua)
        return vistas


class AnuenciaAnexoDetailSerializer(_UsuarioAuditoriaMixin):
    """Anexo completo (todas sus hojas) — lo que se recupera al abrir uno del
    historial para seguir editándolo o volver a generar su .xlsx."""

    def validate_nombre_archivo(self, value):
        """No se permiten dos libros con el mismo nombre (sin distinguir
        mayúsculas ni espacios de sobra) — el nombre es lo único que
        identifica a un anexo de un vistazo en el historial (ver
        AnuenciaHistorialModal.jsx), así que un duplicado sería indistinguible
        del original ahí. Se valida en cada guardado, no sólo al crear: un
        anexo que cambia de nombre a uno ya usado debe rechazarse igual.

        Los eliminados (soft delete) quedan fuera de esta comprobación: ya no
        aparecen en ningún listado, así que bloquear su nombre para uno nuevo
        sería una restricción invisible e inexplicable para quien la sufre.
        """
        nombre = (value or "").strip()
        if nombre:
            en_uso = AnuenciaAnexo.objects.filter(nombre_archivo__iexact=nombre, eliminado=False)
            if self.instance is not None:
                en_uso = en_uso.exclude(pk=self.instance.pk)
            if en_uso.exists():
                raise serializers.ValidationError("Ya existe un anexo guardado con este nombre. Usa uno distinto.")
        return value

    class Meta:
        model = AnuenciaAnexo
        fields = [
            "id", "hojas",
            "firma_nombre", "firma_puesto", "nombre_archivo",
            "creado_por_email", "creado_en",
            "actualizado_por_email", "actualizado_en",
            "generado_por_email", "generado_en", "veces_generado",
            "eliminado", "eliminado_en", "eliminado_por_email",
        ]
        read_only_fields = [
            "creado_por_email", "creado_en", "actualizado_por_email", "actualizado_en",
            "generado_por_email", "generado_en", "veces_generado",
            "eliminado", "eliminado_en", "eliminado_por_email",
        ]


class AnuenciaAnexoCambioSerializer(serializers.ModelSerializer):
    """Una entrada del historial de cambios de un Anexo 2 (botón "Historial
    de cambios" de AnuenciaTab.jsx) — ver AnuenciaAnexoCambio."""

    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = AnuenciaAnexoCambio
        fields = ["id", "fecha", "usuario_nombre", "cambios"]

    def get_usuario_nombre(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.username


class AnuenciaAnexo3VersionListSerializer(serializers.ModelSerializer):
    """Fila del historial de versiones de un Anexo 3 (ver
    Anexo3VersionesModal.jsx) — resumen desde el snapshot `grupos`, sin
    mandar `overrides`/`reasignaciones`/`grupos` completos al listar."""

    creado_por_email = serializers.ReadOnlyField(source="creado_por.email")
    actualizado_por_email = serializers.ReadOnlyField(source="actualizado_por.email")
    total_hojas = serializers.SerializerMethodField()
    total_plazas = serializers.SerializerMethodField()

    class Meta:
        model = AnuenciaAnexo3Version
        fields = [
            "id", "anexo", "nombre", "total_hojas", "total_plazas",
            "creado_por_email", "creado_en", "actualizado_por_email", "actualizado_en",
        ]

    def get_total_hojas(self, obj):
        return len(obj.grupos or [])

    def get_total_plazas(self, obj):
        return sum(int(g.get("total_plazas") or 0) for g in (obj.grupos or []))


class AnuenciaAnexo3VersionDetailSerializer(serializers.ModelSerializer):
    """Versión completa — lo que se recupera al abrir una del historial para
    seguir editándola (ver Anexo3Editor.jsx)."""

    creado_por_email = serializers.ReadOnlyField(source="creado_por.email")
    actualizado_por_email = serializers.ReadOnlyField(source="actualizado_por.email")

    def validate_nombre(self, value):
        """Mismo criterio que `validate_nombre_archivo` en
        AnuenciaAnexoDetailSerializer, pero la unicidad es POR ANEXO: dos
        Anexo 2 distintos sí pueden tener cada uno una versión "v1"."""
        nombre = (value or "").strip()
        if nombre:
            anexo = self.instance.anexo if self.instance is not None else self.initial_data.get("anexo")
            en_uso = AnuenciaAnexo3Version.objects.filter(anexo=anexo, nombre__iexact=nombre)
            if self.instance is not None:
                en_uso = en_uso.exclude(pk=self.instance.pk)
            if en_uso.exists():
                raise serializers.ValidationError("Ya existe una versión con este nombre para este Anexo 2.")
        return value

    class Meta:
        model = AnuenciaAnexo3Version
        fields = [
            "id", "anexo", "nombre", "overrides", "reasignaciones", "grupos",
            "creado_por_email", "creado_en", "actualizado_por_email", "actualizado_en",
        ]
        read_only_fields = ["creado_por_email", "creado_en", "actualizado_por_email", "actualizado_en"]


class AnuenciaJustificacionCatalogoSerializer(serializers.ModelSerializer):
    creado_por_email = serializers.ReadOnlyField(source="creado_por.email")

    class Meta:
        model = AnuenciaJustificacionCatalogo
        fields = ["id", "nombre", "texto", "creado_por_email", "creado_en"]
        read_only_fields = ["creado_por_email", "creado_en"]
