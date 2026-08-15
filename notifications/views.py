from rest_framework import viewsets

from .models import ActivityLog
from .serializers import ActivityLogSerializer

from users.permissions import IsAdmin
from .pagination import StandardPagination


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ActivityLogSerializer

    permission_classes = [
        IsAdmin
    ]

    pagination_class = StandardPagination

    def get_queryset(self):

        queryset = (
            ActivityLog.objects
            .select_related("user")
            .order_by("-created_at")
        )

        # -----------------------------------------
        # Module filter
        # -----------------------------------------

        module = self.request.query_params.get("module")

        if module:
            queryset = queryset.filter(
                module=module.upper()
            )

        # -----------------------------------------
        # Action filter
        # -----------------------------------------

        action = self.request.query_params.get("action")

        if action:
            queryset = queryset.filter(
                action=action.upper()
            )

        # -----------------------------------------
        # Username filter
        # -----------------------------------------

        username = self.request.query_params.get("username")

        if username:
            queryset = queryset.filter(
                user__username__icontains=username
            )

        # -----------------------------------------
        # Start date
        # -----------------------------------------

        start_date = self.request.query_params.get(
            "start_date"
        )

        if start_date:
            queryset = queryset.filter(
                created_at__date__gte=start_date
            )

        # -----------------------------------------
        # End date
        # -----------------------------------------

        end_date = self.request.query_params.get(
            "end_date"
        )

        if end_date:
            queryset = queryset.filter(
                created_at__date__lte=end_date
            )

        return queryset