from rest_framework import serializers
from .models import (
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
