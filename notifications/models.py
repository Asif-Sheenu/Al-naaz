from django.conf import settings
from django.db import models


class ActivityLog(models.Model):

    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    module = models.CharField(
        max_length=50,
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    description = models.TextField()

    old_data = models.JSONField(
        null=True,
        blank=True,
    )

    new_data = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        username = self.user.username if self.user else "Unknown User"

        return (
            f"{username} - "
            f"{self.module} - "
            f"{self.action}"
        )


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Warning"
        APPROVAL = "APPROVAL", "Approval Required"
        ALERT = "ALERT", "Alert"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    module = models.CharField(
        max_length=50,
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["recipient", "is_read"],
            ),
            models.Index(
                fields=["recipient", "created_at"],
            ),
        ]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"    