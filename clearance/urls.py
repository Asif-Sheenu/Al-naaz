from django.urls import path

from .views import (
    ClearanceItemListCreateView,
    ClearanceItemDetailView,
    ManagerApproveClearanceView,
    AdminApproveClearanceView,
    RejectClearanceItemView,
    ClearancePaymentListCreateView,
)

urlpatterns = [
    path(
        "items/",
        ClearanceItemListCreateView.as_view(),
        name="clearance-item-list-create",
    ),
    path(
        "items/<int:pk>/",
        ClearanceItemDetailView.as_view(),
        name="clearance-item-detail",
    ),
    path(
        "items/<int:pk>/approve-manager/",
        ManagerApproveClearanceView.as_view(),
        name="clearance-approve-manager",
    ),
    path(
        "items/<int:pk>/approve-admin/",
        AdminApproveClearanceView.as_view(),
        name="clearance-approve-admin",
    ),
    path(
        "items/<int:pk>/reject/",
        RejectClearanceItemView.as_view(),
        name="clearance-reject",
    ),
    path(
        "payments/",
        ClearancePaymentListCreateView.as_view(),
        name="clearance-payment-list-create",
    ),
]