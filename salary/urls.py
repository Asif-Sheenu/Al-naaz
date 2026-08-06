from rest_framework.routers import DefaultRouter
from .views import SalaryViewSet

router = DefaultRouter()

router.register("salary", SalaryViewSet,basename="salary")

urlpatterns = router.urls