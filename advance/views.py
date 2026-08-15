from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Advance
from .serializers import AdvanceSerializer
from .pagination import StandardPagination

from notifications.services.audit_service import log_activity
from users.permissions import IsAdmin, IsAdminOrStaff


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

    def get_queryset(self):

        queryset = (
            Advance.objects
            .select_related(
                "employee",
                "requested_by",
                "approved_by",
            )
            .order_by("-date")
        )

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
                date__range=[
                    start_date,
                    end_date,
                ]
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

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdmin],
    )
    @transaction.atomic
    def approve(self, request, pk=None):

        advance = (
            Advance.objects
            .select_for_update()
            .select_related("employee")
            .get(pk=pk)
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

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdmin],
    )
    @transaction.atomic
    def reject(self, request, pk=None):

        advance = (
            Advance.objects
            .select_for_update()
            .select_related("employee")
            .get(pk=pk)
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