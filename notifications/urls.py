from rest_framework.routers import DefaultRouter

from .views import (
    ActivityLogViewSet,
    NotificationViewSet,
)

router = DefaultRouter()

router.register(
    "activity-logs",
    ActivityLogViewSet,
    basename="activity-log",
)

router.register(
    "notifications",
    NotificationViewSet,
    basename="notification",
)

urlpatterns = router.urls