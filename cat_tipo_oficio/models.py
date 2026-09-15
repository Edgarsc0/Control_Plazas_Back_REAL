from django.core.validators import FileExtensionValidator  # 1. Importar el validador
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

# Create your models here.


# Catalogo de tipos de asunto referentes a el tipo de movimiento de personal
class CatTipoAsunto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


# Relacionamos los asuntos con los tipos de asuntos que tenemos en el catalogo.
class RelacionAsuntoConTipoOficio(models.Model):
    id = models.AutoField(primary_key=True)
    idAsuntoSCG = models.IntegerField(null=True, blank=True)
    idTipoAsunto = models.ForeignKey(CatTipoAsunto, on_delete=models.CASCADE)

    def __str__(self):
        return f"AsuntoSCG: {self.idAsuntoSCG} - TipoOficio: {self.idTipoAsunto.nombre}"


# En este modelo guardamos particularmente todos los idAsuntoSCG que fueron
class AsuntoValuacion(models.Model):
    id = models.AutoField(primary_key=True)
    idAsuntoSCG = models.IntegerField(null=True, blank=True)
    valuacion = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default="Pendiente",
        choices=[
            ("Procedente", "Procedente"),
            ("Improcedente", "Improcedente"),
            ("Pendiente", "Pendiente"),
        ],
    )

    # Este campo guardara el oficio de improcedencia o procedencia, dependiendo del resultado de la valuación. Solo se aceptarán archivos PDF.
    oficio_resolucion = models.FileField(
        upload_to="oficios/valuacion/%Y/%m/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        verbose_name="Oficio de Resolución (PDF)",
    )

    # Sólo aplica a asuntos dictaminados como Procedente: el oficio con el que
    # se notifica la ocupación de la plaza. Solo se aceptarán archivos PDF.
    oficio_notificacion_ocupacion = models.FileField(
        upload_to="oficios/notificacion_ocupacion/%Y/%m/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        verbose_name="Oficio de Notificación de Ocupación (PDF)",
    )

    def __str__(self):
        return f"AsuntoSCG: {self.idAsuntoSCG} - Valoracion: {self.valuacion}"


@receiver(post_save, sender=RelacionAsuntoConTipoOficio)
def create_asunto_valuacion(sender, instance, created, **kwargs):
    if created and instance.idAsuntoSCG is not None and instance.idTipoAsunto.id == 1:
        AsuntoValuacion.objects.get_or_create(idAsuntoSCG=instance.idAsuntoSCG)


@receiver(post_delete, sender=RelacionAsuntoConTipoOficio)
def delete_asunto_valuacion(sender, instance, **kwargs):
    if instance.idAsuntoSCG is not None and instance.idTipoAsunto.id == 1:
        AsuntoValuacion.objects.filter(idAsuntoSCG=instance.idAsuntoSCG).delete()
