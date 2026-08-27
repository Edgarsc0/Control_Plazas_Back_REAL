from django.contrib import admin

from .models import SuscripcionApiControlPlazas


@admin.register(SuscripcionApiControlPlazas)
class SuscripcionApiControlPlazasAdmin(admin.ModelAdmin):
    list_display = ("nombre", "url", "activo", "creado_en")
    list_filter = ("activo",)
    search_fields = ("nombre", "url")
