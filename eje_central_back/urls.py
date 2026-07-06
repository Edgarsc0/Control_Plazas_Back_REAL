from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from eje_central_back.views_system import SystemLastUpdateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("authentication.urls")),
    path("api/ua/", include("ua.urls")),
    path("api/plantilla/", include("plantilla.urls")),
    path("api/presupuesto/", include("presupuesto.urls")),
    path("api/control-gestion/", include("control_gestion.urls")),
    path("api/cat-tipo-oficio/", include("cat_tipo_oficio.urls")),
    path("api/ai/", include("ai_app.urls")),
    path("api/system/last-update/", SystemLastUpdateView.as_view(), name="system-last-update"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
