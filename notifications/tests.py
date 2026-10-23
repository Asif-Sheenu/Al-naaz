from django.test import TestCase
from django.contrib.auth import get_user_model

from organization.models import Company, Branch
from notifications.models import Notification
from notifications.services.notification_service import (
    notify_clearance_approvers,
    notify_admins_and_managers,
    notify_user,
)


User = get_user_model()


class ClearanceNotificationServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Test Company",
            code="TEST",
        )

        self.branch_a = Branch.objects.create(
            company=self.company,
            name="Branch A",
            code="BR-A",
        )

        self.branch_b = Branch.objects.create(
            company=self.company,
            name="Branch B",
            code="BR-B",
        )

        self.admin = User.objects.create_user(
            username="admin_test",
            password="test-password",
            role="ADMIN",
            is_active=True,
        )

        self.manager_a = User.objects.create_user(
            username="manager_a",
            password="test-password",
            role="MANAGER",
            is_active=True,
        )

        self.manager_b = User.objects.create_user(
            username="manager_b",
            password="test-password",
            role="MANAGER",
            is_active=True,
        )

        self.staff = User.objects.create_user(
            username="staff_test",
            password="test-password",
            role="STAFF",
            is_active=True,
        )

        self.inactive_manager = User.objects.create_user(
            username="inactive_manager",
            password="test-password",
            role="MANAGER",
            is_active=False,
        )

        self.branch_a.users.add(
            self.manager_a,
            self.inactive_manager,
        )

        self.branch_b.users.add(
            self.manager_b,
        )

    def test_manager_stage_notifies_only_active_managers_in_branch(self):
        notifications = notify_clearance_approvers(
            approval_stage="MANAGER",
            title="Manager Approval Required",
            message="A clearance item requires manager approval.",
            object_id=101,
            branch=self.branch_a,
        )

        recipient_ids = {
            notification.recipient_id
            for notification in notifications
        }

        self.assertEqual(
            recipient_ids,
            {self.manager_a.pk},
        )

        self.assertEqual(
            len(notifications),
            1,
        )

        notification = notifications[0]

        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.APPROVAL,
        )

        self.assertEqual(
            notification.module,
            "CLEARANCE",
        )

        self.assertEqual(
            notification.object_id,
            101,
        )

    def test_admin_stage_notifies_active_admins_only(self):
        notifications = notify_clearance_approvers(
            approval_stage="ADMIN",
            title="Admin Approval Required",
            message="A clearance item requires admin approval.",
            object_id=102,
            branch=self.branch_a,
        )

        recipient_ids = {
            notification.recipient_id
            for notification in notifications
        }

        self.assertEqual(
            recipient_ids,
            {self.admin.pk},
        )

        self.assertEqual(
            len(notifications),
            1,
        )

    def test_invalid_approval_stage_raises_error(self):
        with self.assertRaises(ValueError):
            notify_clearance_approvers(
                approval_stage="INVALID",
                title="Test",
                message="Test message",
                object_id=103,
                branch=self.branch_a,
            )

    def test_inactive_user_does_not_receive_direct_notification(self):
        notification_count_before = Notification.objects.count()

        result = notify_user(
            user=self.inactive_manager,
            notification_type=Notification.NotificationType.INFO,
            title="Test Notification",
            message="This notification should not be created.",
            module="CLEARANCE",
            object_id=104,
        )

        self.assertIsNone(result)

        self.assertEqual(
            Notification.objects.count(),
            notification_count_before,
        )

    def test_none_user_does_not_receive_direct_notification(self):
        notification_count_before = Notification.objects.count()

        result = notify_user(
            user=None,
            notification_type=Notification.NotificationType.INFO,
            title="Test Notification",
            message="No recipient was provided.",
            module="CLEARANCE",
            object_id=105,
        )

        self.assertIsNone(result)

        self.assertEqual(
            Notification.objects.count(),
            notification_count_before,
        )

    def test_admins_and_managers_notification_is_branch_filtered(self):
        notifications = notify_admins_and_managers(
            notification_type=Notification.NotificationType.INFO,
            title="Payment Recorded",
            message="A clearance payment was recorded.",
            module="CLEARANCE",
            object_id=106,
            branch=self.branch_a,
        )

        recipient_ids = {
            notification.recipient_id
            for notification in notifications
        }

        self.assertEqual(
            recipient_ids,
            {
                self.admin.pk,
                self.manager_a.pk,
            },
        )

    def test_duplicate_recipients_receive_only_one_notification(self):
        notifications = notify_admins_and_managers(
            notification_type=Notification.NotificationType.INFO,
            title="Payment Recorded",
            message="A clearance payment was recorded.",
            module="CLEARANCE",
            object_id=107,
            branch=self.branch_a,
        )

        recipient_ids = [
            notification.recipient_id
            for notification in notifications
        ]

        self.assertEqual(
            len(recipient_ids),
            len(set(recipient_ids)),
        )

    def test_direct_notification_is_created_for_active_user(self):
        notification = notify_user(
            user=self.staff,
            notification_type=Notification.NotificationType.INFO,
            title="Clearance Approved",
            message="Your clearance item was approved.",
            module="CLEARANCE",
            object_id=108,
        )

        self.assertIsNotNone(notification)

        self.assertEqual(
            notification.recipient_id,
            self.staff.pk,
        )

        self.assertEqual(
            notification.title,
            "Clearance Approved",
        )

        self.assertEqual(
            notification.module,
            "CLEARANCE",
        )

        self.assertEqual(
            notification.object_id,
            108,
        )