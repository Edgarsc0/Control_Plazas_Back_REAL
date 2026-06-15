from rest_framework import serializers
from .models import CpTblMovCompleto290526

class CpTblMovCompleto290526Serializer(serializers.ModelSerializer):
    class Meta:
        model = CpTblMovCompleto290526
        # Dynamically exclude specified columns to prevent DRF errors if they do not exist
        exclude = [
            f for f in ['columna_c', 'columna_d', 'fecha_descarga']
            if f in [field.name for field in CpTblMovCompleto290526._meta.get_fields()]
        ]
