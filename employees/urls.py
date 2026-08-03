from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet

router = DefaultRouter()

router.register("employees", EmployeeViewSet, basename="employees")

urlpatterns = router.urls