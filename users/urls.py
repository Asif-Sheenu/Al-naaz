from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import LogoutView,RefreshView,LoginView,ProfileView,StaffCreateView,StaffListView,StaffDeactivateView,StaffUpdateView,UserManagementViewSet

router = DefaultRouter()


router.register(
    "users",
    UserManagementViewSet,
    basename="user-management",
)

urlpatterns = [
    path(
    "refresh/",
    RefreshView.as_view()
),
    path(
        "",
        include(router.urls),),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("staff/", StaffCreateView.as_view()),
    path("staff/list/", StaffListView.as_view()),
    path("staff/<int:pk>/update/", StaffUpdateView.as_view()),
    path(
    "staff/<int:pk>/deactivate/",
    StaffDeactivateView.as_view()
),
]