from rest_framework.routers import DefaultRouter
from .views import AdvanceViewSet

router = DefaultRouter()
router.register("advance", AdvanceViewSet, basename="advance")

urlpatterns = router.urls