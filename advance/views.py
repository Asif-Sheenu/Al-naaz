from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Advance
from .serializers import AdvanceSerializer

from users.permissions import IsAdmin, IsAdminOrStaff


class AdvanceViewSet(viewsets.ModelViewSet):

    serializer_class = AdvanceSerializer
    permission_classes = [IsAdminOrStaff]

    def get_queryset(self):

        queryset = Advance.objects.select_related(
            "employee",
            "requested_by",
            "approved_by"
        ).order_by("-date")

        employee = self.request.query_params.get("employee")
        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")

        if employee:
            queryset = queryset.filter(employee_id=employee)

        if month:
            queryset = queryset.filter(date__month=month)

        if year:
            queryset = queryset.filter(date__year=year)

        if start_date and end_date:
            queryset = queryset.filter(
                date__range=[start_date, end_date]
            )

        if search:
            queryset = queryset.filter(
                employee__name__icontains=search
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def perform_create(self, serializer):

        serializer.save(
            requested_by=self.request.user
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdmin]
    )
    def approve(self, request, pk=None):

        advance = self.get_object()

        if advance.status != Advance.Status.PENDING:
            return Response(
            {"message": "This request has already been processed."},
            status=status.HTTP_400_BAD_REQUEST
        )

        advance.status = Advance.Status.APPROVED
        advance.approved_by = request.user
        advance.approved_at = timezone.now()
        advance.save()

        return Response(
            {"message": "Advance approved successfully."},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdmin]
    )
    def reject(self, request, pk=None):

        advance = self.get_object()

        if advance.status != Advance.Status.PENDING:
            return Response(
                {"message": "This request has already been processed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        advance.status = Advance.Status.REJECTED
        advance.approved_by = request.user
        advance.approved_at = timezone.now()
        advance.save()

        return Response(
            {"message": "Advance rejected successfully."},
            status=status.HTTP_200_OK
        )