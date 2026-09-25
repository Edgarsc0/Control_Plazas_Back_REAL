from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChangePasswordView,
    LoginView,
    MantenimientoView,
    MePermissionsView,
    PermissionListView,
    PresenceHeartbeatView,
    PresenceListView,
    RoleViewSet,
    TableroLayoutUsuarioView,
    TableroLayoutView,
    UserVisitsView,
    WhitelistViewSet,
)

router = DefaultRouter()
router.register(r'whitelist', WhitelistViewSet)
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path('me/permissions/', MePermissionsView.as_view(), name='me-permissions'),
    path('presence/heartbeat/', PresenceHeartbeatView.as_view(), name='presence-heartbeat'),
    path('presence/active/', PresenceListView.as_view(), name='presence-active'),
    path('visits/', UserVisitsView.as_view(), name='user-visits'),
    path('maintenance/', MantenimientoView.as_view(), name='maintenance'),
    path('tablero-layout/', TableroLayoutView.as_view(), name='tablero-layout'),
    path('tablero-layout/usuario/<int:whitelist_id>/', TableroLayoutUsuarioView.as_view(), name='tablero-layout-usuario'),
]
