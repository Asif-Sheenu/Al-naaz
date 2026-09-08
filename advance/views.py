from django.db import transaction
from django.utils import timezone
from users.permissions import (
    IsAdminOrManager,
    IsAdminOrStaff,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from organization.services.access_service import (
    get_accessible_branches,
)
from drf_spectacular.utils import extend_schema
from .models import Advance
from .serializers import AdvanceSerializer
from .pagination import StandardPagination
from django.shortcuts import get_object_or_404
from notifications.services.audit_service import log_activity


class AdvanceViewSet(viewsets.ModelViewSet):

    serializer_class = AdvanceSerializer
    permission_classes = [IsAdminOrStaff]
    pagination_class = StandardPagination

    # Don't allow arbitrary PUT/PATCH/DELETE
    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def user_can_access_advance(self, user, advance):

        if user.is_superuser or user.role == "ADMIN":
            return True

        return get_accessible_branches(user).filter(
            pk=advance.employee.branch_id
        ).exists()

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Advance.objects
            .select_related(
                "employee",
                "employee__branch",
                "requested_by",
                "approved_by",
            )
            .order_by("-date")
        )

        # Branch access
        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list("id", flat=True)
            )

            queryset = queryset.filter(
                employee__branch_id__in=accessible_branch_ids
            )

        # Existing filters
        employee = self.request.query_params.get("employee")
        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")

        if employee:
            queryset = queryset.filter(
                employee_id=employee
            )

        if month:
            queryset = queryset.filter(
                date__month=month
            )

        if year:
            queryset = queryset.filter(
                date__year=year
            )

        if start_date and end_date:
            queryset = queryset.filter(
                date__range=[start_date, end_date]
            )

        if search:
            queryset = queryset.filter(
                employee__name__icontains=search
            )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        return queryset                                         

    # --------------------------------------------------
    # CREATE ADVANCE
    # --------------------------------------------------

    def perform_create(self, serializer):

        advance = serializer.save(
            requested_by=self.request.user
        )

        log_activity(
            user=self.request.user,
            action="CREATE",
            module="ADVANCE",
            object_id=advance.id,
            description=(
                f"Requested employee advance "
                f"of ₹{advance.amount}"
            ),
            new_data={
                "employee": advance.employee.name,
                "amount": str(advance.amount),
                "date": str(advance.date),
                "reason": advance.reason,
                "remarks": advance.remarks,
                "status": advance.status,
            },
        )

    # --------------------------------------------------
    # APPROVE ADVANCE
    # --------------------------------------------------

    @extend_schema(
        request=None,
        )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdminOrManager],
    )
    @transaction.atomic
    def approve(self, request, pk=None):

        advance = get_object_or_404(
            Advance.objects
            .select_for_update()
            .select_related("employee", "employee__branch"),
            pk=pk,
        )

        if not self.user_can_access_advance(
            request.user,
            advance,
        ):
            return Response(
                {
                    "message": (
                        "You do not have access to this "
                        "advance request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if advance.status != Advance.Status.PENDING:
            return Response(
                {
                    "message": (
                        "This request has already "
                        "been processed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        advance.status = Advance.Status.APPROVED
        advance.approved_by = request.user
        advance.approved_at = timezone.now()

        advance.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
            ]
        )

        log_activity(
            user=request.user,
            action="APPROVE",
            module="ADVANCE",
            object_id=advance.id,
            description=(
                f"Approved employee advance "
                f"of ₹{advance.amount}"
            ),
            new_data={
                "employee": advance.employee.name,
                "amount": str(advance.amount),
                "date": str(advance.date),
                "status": advance.status,
                "approved_by": request.user.username,
                "approved_at": str(
                    advance.approved_at
                ),
            },
        )

        return Response(
            {
                "message": (
                    "Advance approved successfully."
                )
            },
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # REJECT ADVANCE
    # --------------------------------------------------

    @extend_schema(
        request=None,
        )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdminOrManager],
    )
    @transaction.atomic
    def reject(self, request, pk=None):

        advance = get_object_or_404(
            Advance.objects
            .select_for_update()
            .select_related(
                "employee",
                "employee__branch",
            ),
            pk=pk,
        )

        if not self.user_can_access_advance(
            request.user,
            advance,
        ):
            return Response(
                {
                    "message": (
                        "You do not have access to this "
                        "advance request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )   

        if advance.status != Advance.Status.PENDING:
            return Response(
                {
                    "message": (
                        "This request has already "
                        "been processed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )        
        advance.status = Advance.Status.REJECTED
        advance.approved_by = request.user
        advance.approved_at = timezone.now()

        advance.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
            ]
        )

        log_activity(
            user=request.user,
            action="REJECT",
            module="ADVANCE",
            object_id=advance.id,
            description=(
                f"Rejected employee advance "
                f"of ₹{advance.amount}"
            ),
            new_data={
                "employee": advance.employee.name,
                "amount": str(advance.amount),
                "date": str(advance.date),
                "status": advance.status,
                "rejected_by": request.user.username,
                "rejected_at": str(
                    advance.approved_at
                ),
            },
        )

        return Response(
            {
                "message": (
                    "Advance rejected successfully."
                )
            },
            status=status.HTTP_200_OK,
        )