from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notifications.services.notification_service import (
    notify_admins_and_managers,
    notify_user,
)
from .models import ActivityLog, Notification
from .serializers import (
    ActivityLogSerializer,
    NotificationSerializer,
)
from .pagination import StandardPagination

from users.permissions import IsAdmin


# ============================================================
# ACTIVITY LOG
# ============================================================

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


# ============================================================
# NOTIFICATIONS
# ============================================================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = NotificationSerializer

    permission_classes = [
        IsAuthenticated
    ]

    pagination_class = StandardPagination

    def get_queryset(self) -> QuerySet:

        queryset = (
            Notification.objects
            .filter(
                recipient=self.request.user
            )
            .order_by("-created_at")
        )

        # -----------------------------------------
        # Read / unread filter
        # -----------------------------------------

        is_read = self.request.query_params.get(
            "is_read"
        )

        if is_read is not None:

            if is_read.lower() == "true":
                queryset = queryset.filter(
                    is_read=True
                )

            elif is_read.lower() == "false":
                queryset = queryset.filter(
                    is_read=False
                )

        # -----------------------------------------
        # Module filter
        # -----------------------------------------

        module = self.request.query_params.get(
            "module"
        )

        if module:
            queryset = queryset.filter(
                module=module.upper()
            )

        # -----------------------------------------
        # Notification type filter
        # -----------------------------------------

        notification_type = self.request.query_params.get(
            "notification_type"
        )

        if notification_type:
            queryset = queryset.filter(
                notification_type=notification_type.upper()
            )

        return queryset

    # -----------------------------------------
    # Mark single notification as read
    # -----------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="mark-read",
    )
    def mark_read(self, request, pk=None):

        notification = self.get_object()

        if not notification.is_read:

            notification.is_read = True
            notification.read_at = timezone.now()

            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        return Response(
            {
                "message": "Notification marked as read."
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------------------
    # Mark all notifications as read
    # -----------------------------------------

    @action(
        detail=False,
        methods=["post"],
        url_path="mark-all-read",
    )
    def mark_all_read(self, request):

        updated_count = (
            Notification.objects
            .filter(
                recipient=request.user,
                is_read=False,
            )
            .update(
                is_read=True,
                read_at=timezone.now(),
            )
        )

        return Response(
            {
                "message": "All notifications marked as read.",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------------------
    # Unread notification count
    # -----------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="unread-count",
    )
    def unread_count(self, request):

        count = (
            Notification.objects
            .filter(
                recipient=request.user,
                is_read=False,
            )
            .count()
        )

        return Response(
            {
                "unread_count": count
            },
            status=status.HTTP_200_OK,
        )