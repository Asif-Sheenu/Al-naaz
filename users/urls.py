from django.contrib import admin
from django.urls import path


from .views import LogoutView,RefreshView,LoginView,ProfileView,StaffCreateView,StaffListView,StaffDeactivateView,StaffUpdateView

urlpatterns = [
    path(
    "refresh/",
    RefreshView.as_view()
),
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