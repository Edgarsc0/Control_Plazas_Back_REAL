from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CheckEmailView,
    MePermissionsView,
    PermissionListView,
    PresenceHeartbeatView,
    PresenceListView,
    RoleViewSet,
    VerifyCodeView,
    WhitelistViewSet,
)

router = DefaultRouter()
router.register(r'whitelist', WhitelistViewSet)
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path('me/permissions/', MePermissionsView.as_view(), name='me-permissions'),
    path('presence/heartbeat/', PresenceHeartbeatView.as_view(), name='presence-heartbeat'),
    path('presence/active/', PresenceListView.as_view(), name='presence-active'),
]
