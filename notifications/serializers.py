from rest_framework import serializers
from .models import Notification

from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    class Meta:
        model = ActivityLog

        fields = [
            "id",
            "username",
            "action",
            "module",
            "object_id",
            "description",
            "old_data",
            "new_data",
            "created_at",
        ]

        read_only_fields = fields






class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification

        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "module",
            "object_id",
            "is_read",
            "read_at",

            "created_at",
        ]

        read_only_fields = fields        