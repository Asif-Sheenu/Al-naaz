from rest_framework import serializers

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