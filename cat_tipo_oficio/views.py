from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CatTipoAsunto, RelacionAsuntoConTipoOficio, AsuntoValuacion
from .serializers import CatTipoAsuntoSerializer, RelacionAsuntoConTipoOficioSerializer, AsuntoValuacionSerializer

class CatTipoAsuntoViewSet(viewsets.ModelViewSet):
    queryset = CatTipoAsunto.objects.all()
    serializer_class = CatTipoAsuntoSerializer

class RelacionAsuntoConTipoOficioViewSet(viewsets.ModelViewSet):
    queryset = RelacionAsuntoConTipoOficio.objects.all()
    serializer_class = RelacionAsuntoConTipoOficioSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        idAsuntoSCG = self.request.query_params.get('idAsuntoSCG')
        if idAsuntoSCG:
            queryset = queryset.filter(idAsuntoSCG=idAsuntoSCG)
        return queryset

    def create(self, request, *args, **kwargs):
        idAsuntoSCG = request.data.get('idAsuntoSCG')
        idTipoAsunto = request.data.get('idTipoAsunto')
        
        if not idAsuntoSCG or not idTipoAsunto:
            return Response(
                {"error": "idAsuntoSCG and idTipoAsunto are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Lógica de "upsert": Si ya existe una relación para este asunto, la actualizamos
        relacion, created = RelacionAsuntoConTipoOficio.objects.update_or_create(
            idAsuntoSCG=idAsuntoSCG,
            defaults={'idTipoAsunto_id': idTipoAsunto}
        )
        
        serializer = self.get_serializer(relacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class AsuntoValuacionViewSet(viewsets.ModelViewSet):
    queryset = AsuntoValuacion.objects.all()
    serializer_class = AsuntoValuacionSerializer

    @action(detail=True, methods=['patch'], url_path='guardar-valuacion')
    def guardar_valuacion(self, request, pk=None):
        """
        Persiste el resultado del simulador de valuación presupuestaria.

        Espera `{"valuacion": {...}}` con las dos tablas que produce el
        simulador dentro de `tablas`: `desglose_por_nivel` (tabla_2022) y
        `desglose_por_concepto` (tabla_q322_t348). La marca de tiempo se
        estampa aquí para no depender del reloj del navegador.
        """
        asunto = self.get_object()
        valuacion = request.data.get('valuacion')

        if not isinstance(valuacion, dict):
            return Response(
                {"error": "El campo 'valuacion' es requerido y debe ser un objeto."},
                status=status.HTTP_400_BAD_REQUEST
            )

        tablas = valuacion.get('tablas') or {}
        if not tablas.get('desglose_por_nivel') or not tablas.get('desglose_por_concepto'):
            return Response(
                {"error": "La valuación debe incluir 'tablas.desglose_por_nivel' y 'tablas.desglose_por_concepto'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        asunto.valuacion = {**valuacion, 'guardado_en': timezone.now().isoformat()}
        asunto.save(update_fields=['valuacion'])

        return Response(self.get_serializer(asunto).data, status=status.HTTP_200_OK)
