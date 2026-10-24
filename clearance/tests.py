from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from users.models import User
from organization.models import Company, Branch
from employees.models import Employee

from clearance.models import IssuedItem, ClearancePayment
from clearance.services import (
    issue_item,
    approve_by_manager,
    approve_by_admin,
    record_clearance_payment,
)
from rest_framework.test import APITestCase
from rest_framework import status

from notifications.models import Notification

class ClearanceApprovalWorkflowTests(TestCase):
    """
    Test clearance item creation and approval workflows.
    """

    @classmethod
    def setUpTestData(cls):
        # Create a company and branch.
        cls.company = Company.objects.create(
            name="Test Company",
            code="TEST",
        )

        cls.branch = Branch.objects.create(
            company=cls.company,
            name="Test Branch",
            code="TEST-BRANCH",
        )

        # Create users with different roles.
        cls.staff = User.objects.create_user(
            username="test_staff",
            password="test-password",
            role="STAFF",
        )

        cls.manager = User.objects.create_user(
            username="test_manager",
            password="test-password",
            role="MANAGER",
        )

        cls.admin = User.objects.create_user(
            username="test_admin",
            password="test-password",
            role="ADMIN",
        )

        # Give users access to the test branch.
        cls.branch.users.add(
            cls.staff,
            cls.manager,
            cls.admin,
        )

        # Create an employee who receives clearance items.
        cls.employee = Employee.objects.create(
            branch=cls.branch,
            name="Test Employee",
            phone="9876543210",
            designation="Worker",
            joining_date=date(2025, 1, 1),
        )

    def create_item(self, issued_by):
        """
        Helper method to create a clearance item.
        """
        return issue_item(
            employee=self.employee,
            item_name="Safety Shoes",
            quantity=1,
            unit_value=Decimal("1000.00"),
            employee_payable=Decimal("800.00"),
            issued_by=issued_by,
        )

    def test_staff_created_item_requires_manager_approval(self):
        item = self.create_item(self.staff)

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.PENDING_MANAGER,
        )

        self.assertIsNone(item.manager_approved_by)
        self.assertIsNone(item.admin_approved_by)

    def test_manager_created_item_requires_admin_approval(self):
        item = self.create_item(self.manager)

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.PENDING_ADMIN,
        )

        self.assertEqual(
            item.manager_approved_by,
            self.manager,
        )

        self.assertIsNotNone(item.manager_approved_at)
        self.assertIsNone(item.admin_approved_by)

    def test_admin_created_item_requires_manager_approval(self):
        item = self.create_item(self.admin)

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.PENDING_MANAGER,
        )

        self.assertEqual(
            item.admin_approved_by,
            self.admin,
        )

        self.assertIsNotNone(item.admin_approved_at)
        self.assertIsNone(item.manager_approved_by)

    def test_manager_approval_completes_admin_created_item(self):
        item = self.create_item(self.admin)

        item = approve_by_manager(
            issued_item_id=item.pk,
            approved_by=self.manager,
    )

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.APPROVED
        )

        self.assertEqual(item.manager_approved_by, self.manager)
        self.assertEqual(item.admin_approved_by, self.admin)

        self.assertIsNotNone(item.manager_approved_at)
        self.assertIsNotNone(item.admin_approved_at)

    def test_admin_approval_completes_manager_created_item(self):
        item = self.create_item(self.manager)

        item = approve_by_admin(
            issued_item_id=item.pk,
            approved_by=self.admin,
        )

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.APPROVED,
        )

        self.assertEqual(item.manager_approved_by, self.manager)
        self.assertEqual(item.admin_approved_by, self.admin)

        self.assertIsNotNone(item.manager_approved_at)
        self.assertIsNotNone(item.admin_approved_at)

    def test_staff_item_requires_both_approval_stages(self):
        item = self.create_item(self.staff)

        # First stage: manager approval.
        item = approve_by_manager(
            issued_item_id=item.pk,
            approved_by=self.manager,
        )

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.PENDING_ADMIN,
        )

        # Second stage: admin approval.
        item = approve_by_admin(
            issued_item_id=item.pk,
            approved_by=self.admin,
        )

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.APPROVED,
        )

        self.assertEqual(item.manager_approved_by, self.manager)
        self.assertEqual(item.admin_approved_by, self.admin)

    def test_creator_cannot_approve_own_item(self):
        item = self.create_item(self.staff)

        with self.assertRaises(ValidationError):
            approve_by_manager(
                issued_item_id=item.pk,
                approved_by=self.staff,
            )

        item.refresh_from_db()

        self.assertEqual(
            item.approval_status,
            IssuedItem.ApprovalStatus.PENDING_MANAGER,
        )

    def test_manager_cannot_approve_item_twice(self):
        item = self.create_item(self.staff)

        approve_by_manager(
            issued_item_id=item.pk,
            approved_by=self.manager,
        )

        with self.assertRaises(ValidationError):
            approve_by_manager(
                issued_item_id=item.pk,
                approved_by=self.manager,
            )

    def test_payment_is_rejected_before_final_approval(self):
        item = self.create_item(self.staff)

        with self.assertRaises(ValidationError):
            record_clearance_payment(
                issued_item_id=item.pk,
                amount=Decimal("100.00"),
                payment_method=ClearancePayment.PaymentMethod.CASH,
                recorded_by=self.admin,
            )

        self.assertEqual(item.payments.count(), 0)

    def test_payment_is_allowed_after_final_approval(self):
        item = self.create_item(self.staff)

        approve_by_manager(
            issued_item_id=item.pk,
            approved_by=self.manager,
        )

        approve_by_admin(
            issued_item_id=item.pk,
            approved_by=self.admin,
        )

        payment = record_clearance_payment(
            issued_item_id=item.pk,
            amount=Decimal("200.00"),
            payment_method=ClearancePayment.PaymentMethod.CASH,
            recorded_by=self.admin,
        )

        self.assertEqual(
            payment.amount,
            Decimal("200.00"),
        )

        self.assertEqual(
            item.employee_payable,
            Decimal("800.00"),
        )

    def test_payment_cannot_exceed_outstanding_balance(self):
        item = self.create_item(self.staff)

        approve_by_manager(
            issued_item_id=item.pk,
            approved_by=self.manager,
        )

        approve_by_admin(
            issued_item_id=item.pk,
            approved_by=self.admin,
        )

        with self.assertRaises(ValidationError):
            record_clearance_payment(
                issued_item_id=item.pk,
                amount=Decimal("801.00"),
                payment_method=ClearancePayment.PaymentMethod.CASH,
                recorded_by=self.admin,
            )

        self.assertEqual(item.payments.count(), 0)


class ClearanceNotificationAPITests(APITestCase):
    """
    Verify that clearance API endpoints create the correct notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            name="Notification Test Company",
            code="NOTIFY",
        )

        cls.branch_a = Branch.objects.create(
            company=cls.company,
            name="Notification Branch A",
            code="NOTIFY-A",
        )

        cls.branch_b = Branch.objects.create(
            company=cls.company,
            name="Notification Branch B",
            code="NOTIFY-B",
        )

        cls.staff = User.objects.create_user(
            username="notification_staff",
            password="test-password",
            role="STAFF",
        )

        cls.manager_a = User.objects.create_user(
            username="notification_manager_a",
            password="test-password",
            role="MANAGER",
        )

        cls.manager_b = User.objects.create_user(
            username="notification_manager_b",
            password="test-password",
            role="MANAGER",
        )

        cls.admin = User.objects.create_user(
            username="notification_admin",
            password="test-password",
            role="ADMIN",
        )

        cls.branch_a.users.add(
            cls.staff,
            cls.manager_a,
            cls.admin,
        )

        cls.branch_b.users.add(cls.manager_b)

        cls.employee = Employee.objects.create(
            branch=cls.branch_a,
            name="Notification Test Employee",
            phone="9876501234",
            designation="Worker",
            joining_date=date(2025, 1, 1),
        )

    def setUp(self):
        self.client.force_authenticate(user=self.staff)

    def create_item_through_api(self):
        return self.client.post(
            "/api/clearance/items/",
            {
                "employee": self.employee.pk,
                "item_name": "Safety Shoes",
                "quantity": 1,
                "unit_value": "1000.00",
                "employee_payable": "800.00",
                "notes": "Notification integration test",
            },
            format="json",
        )

    def test_creating_item_notifies_only_branch_managers(self):
        response = self.create_item_through_api()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.assertEqual(
            response.data["approval_status"],
            IssuedItem.ApprovalStatus.PENDING_MANAGER,
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.manager_a,
                module="CLEARANCE",
                object_id=response.data["id"],
                title="Clearance Item Requires Manager Approval",
            ).exists()
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.manager_b,
                module="CLEARANCE",
                object_id=response.data["id"],
            ).exists()
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.staff,
                module="CLEARANCE",
                object_id=response.data["id"],
            ).exists()
        )

    def test_manager_approval_notifies_admin(self):
        response = self.create_item_through_api()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/approve-manager/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.assertEqual(
            response.data["approval_status"],
            IssuedItem.ApprovalStatus.PENDING_ADMIN,
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                module="CLEARANCE",
                object_id=item_id,
                title="Clearance Item Requires Admin Approval",
            ).exists()
        )

    def test_final_admin_approval_notifies_issuer(self):
        response = self.create_item_through_api()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        manager_response = self.client.post(
            f"/api/clearance/items/{item_id}/approve-manager/",
            {},
            format="json",
        )

        self.assertEqual(
            manager_response.status_code,
            status.HTTP_200_OK,
            manager_response.data,
        )

        self.client.force_authenticate(user=self.admin)

        admin_response = self.client.post(
            f"/api/clearance/items/{item_id}/approve-admin/",
            {},
            format="json",
        )

        self.assertEqual(
            admin_response.status_code,
            status.HTTP_200_OK,
            admin_response.data,
        )

        self.assertEqual(
            admin_response.data["approval_status"],
            IssuedItem.ApprovalStatus.APPROVED,
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.staff,
                module="CLEARANCE",
                object_id=item_id,
                title="Clearance Item Fully Approved",
            ).exists()
        )

    def test_rejection_notifies_issuer_with_reason(self):
        response = self.create_item_through_api()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        item_id = response.data["id"]
        reason = "Incorrect item quantity"

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {
                "stage": "MANAGER",
                "rejection_reason": reason,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        notification = Notification.objects.get(
            recipient=self.staff,
            module="CLEARANCE",
            object_id=item_id,
            title="Clearance Item Rejected",
        )

        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.WARNING,
        )

        self.assertIn(reason, notification.message)


    def test_rejection_requires_reason(self):
        response = self.create_item_through_api()
        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {"stage": "MANAGER"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_rejection_requires_valid_stage(self):
        response = self.create_item_through_api()
        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {
                "rejection_reason": "Incorrect quantity",
                "stage": "INVALID",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
    )


    def test_rejection_requires_reason(self):
        response = self.create_item_through_api()
        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {"stage": "MANAGER"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_rejection_requires_valid_stage(self):
        response = self.create_item_through_api()
        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {
                "rejection_reason": "Incorrect quantity",
                "stage": "INVALID",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)



    def test_rejection_requires_reason(self):
        response = self.create_item_through_api()
        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {"stage": "MANAGER"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_rejection_requires_valid_stage(self):
        response = self.create_item_through_api()
        item_id = response.data["id"]

        self.client.force_authenticate(user=self.manager_a)

        response = self.client.post(
            f"/api/clearance/items/{item_id}/reject/",
            {
                "rejection_reason": "Incorrect quantity",
                "stage": "INVALID",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)