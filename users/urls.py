from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import ProfileView,StaffCreateView,StaffListView,StaffDeactivateView,StaffUpdateView

urlpatterns = [

    path("login/", TokenObtainPairView.as_view()),
    path("refresh/", TokenRefreshView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("staff/", StaffCreateView.as_view()),
    path("staff/list/", StaffListView.as_view()),
    path("staff/<int:pk>/update/", StaffUpdateView.as_view()),
    path(
    "staff/<int:pk>/deactivate/",
    StaffDeactivateView.as_view()
),
]