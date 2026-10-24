from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from notifications.models import Notification
from notifications.services.notification_service import (
    notify_admins_and_managers,
    notify_clearance_approvers,
    notify_user,
)

from employees.models import Employee

from users.permissions import (
    IsAdmin,
    IsAdminOrManager,
    IsAdminOrStaff,
    IsManager,
)

from .models import IssuedItem, ClearancePayment

from .permissions import IsAdminManagerOrStaff

from .serializers import (
    IssuedItemSerializer,
    ClearancePaymentSerializer,
    ClearanceRejectionSerializer
)

from .services import (
    issue_item,
    approve_by_manager,
    approve_by_admin,
    reject_issued_item,
    record_clearance_payment,
)


def handle_service_error(exc):
    """
    Convert Django validation errors into DRF validation errors.
    """
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict)

    raise ValidationError(exc.messages)


def get_accessible_items(user):
    """
    Return clearance items from branches accessible to the user.
    """
    from organization.services.user_branch_service import (
        get_accessible_branches,
    )

    accessible_branch_ids = get_accessible_branches(
        user
    ).values_list(
        "id",
        flat=True,
    )

    return (
        IssuedItem.objects.filter(
            employee__branch_id__in=accessible_branch_ids
        )
        .select_related(
            "employee",
            "employee__branch",
            "issued_by",
            "manager_approved_by",
            "admin_approved_by",
        )
        .prefetch_related("payments")
    )


class ClearanceItemListCreateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminManagerOrStaff,
    ]

    def get(self, request):
        items = get_accessible_items(request.user)

        approval_status = request.query_params.get(
            "approval_status"
        )

        employee_id = request.query_params.get("employee")

        if approval_status:
            valid_statuses = IssuedItem.ApprovalStatus.values

            if approval_status not in valid_statuses:
                raise ValidationError({
                    "approval_status": "Invalid approval status."
                })

            items = items.filter(
                approval_status=approval_status
            )

        if employee_id:
            items = items.filter(
                employee_id=employee_id
            )

        serializer = IssuedItemSerializer(
            items,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        request=IssuedItemSerializer,
        responses={201: IssuedItemSerializer},
    )
    def post(self, request):
        serializer = IssuedItemSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        employee = Employee.objects.filter(
            pk=serializer.validated_data["employee"].pk
        ).first()

        if employee is None:
            raise ValidationError({
                "employee": "Employee not found."
            })

        from organization.services.user_branch_service import (
            get_accessible_branches,
        )

        if not get_accessible_branches(
            request.user
        ).filter(
            pk=employee.branch_id
        ).exists():
            raise ValidationError({
                "employee": (
                    "You cannot issue items to employees "
                    "in this branch."
                )
            })

        try:
            item = issue_item(
                employee=employee,
                item_name=serializer.validated_data["item_name"],
                quantity=serializer.validated_data["quantity"],
                unit_value=serializer.validated_data["unit_value"],
                employee_payable=serializer.validated_data[
                    "employee_payable"
                ],
                issued_by=request.user,
                issued_date=serializer.validated_data.get(
                    "issued_date"
                ),
                notes=serializer.validated_data.get(
                    "notes",
                    "",
                ),
            )

        except DjangoValidationError as exc:
            handle_service_error(exc)

        # Determine who must approve this item next.
        if (
            item.approval_status
            == IssuedItem.ApprovalStatus.PENDING_MANAGER
        ):
            approval_stage = "MANAGER"

            title = "Clearance Item Requires Manager Approval"

            message = (
                f"{item.item_name} has been issued to employee "
                f"{item.employee}. Manager approval is required."
            )

        elif (
            item.approval_status
            == IssuedItem.ApprovalStatus.PENDING_ADMIN
        ):
            approval_stage = "ADMIN"

            title = "Clearance Item Requires Admin Approval"

            message = (
                f"{item.item_name} has been issued to employee "
                f"{item.employee}. Admin approval is required."
            )

        else:
            approval_stage = None

            title = "Clearance Item Created"

            message = (
                f"{item.item_name} has been issued to employee "
                f"{item.employee}. Current status: "
                f"{item.approval_status}."
            )

        # Notify only the users responsible for the next stage.
        if approval_stage:
            notify_clearance_approvers(
                approval_stage=approval_stage,
                title=title,
                message=message,
                object_id=item.pk,
                branch=item.employee.branch,
            )

        return Response(
            IssuedItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class ClearanceItemDetailView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminManagerOrStaff,
    ]

    def get(self, request, pk):
        item = get_accessible_items(
            request.user
        ).filter(
            pk=pk
        ).first()

        if item is None:
            return Response(
                {"detail": "Clearance item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            IssuedItemSerializer(item).data
        )


class ManagerApproveClearanceView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsManager,
    ]

    def post(self, request, pk):
        item = get_accessible_items(
            request.user
        ).filter(
            pk=pk
        ).first()

        if item is None:
            return Response(
                {"detail": "Clearance item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            request.user.role != "ADMIN"
            and not request.user.is_superuser
        ):
            if not request.user.branches.filter(
                pk=item.employee.branch_id
            ).exists():
                return Response(
                    {
                        "detail": (
                            "You cannot approve items "
                            "from this branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            item = approve_by_manager(
                issued_item_id=item.pk,
                approved_by=request.user,
            )

        except DjangoValidationError as exc:
            handle_service_error(exc)

        if (
            item.approval_status
            == IssuedItem.ApprovalStatus.APPROVED
        ):
            # The item has completed its approval workflow.
            notify_user(
                user=item.issued_by,
                notification_type=Notification.NotificationType.INFO,
                title="Clearance Item Fully Approved",
                message=(
                    f"Your clearance item '{item.item_name}' "
                    f"for employee {item.employee} "
                    "has been fully approved."
                ),
                module="CLEARANCE",
                object_id=item.pk,
            )

        elif (
            item.approval_status
            == IssuedItem.ApprovalStatus.PENDING_ADMIN
        ):
            # Manager approval is complete. Notify only admins.
            notify_clearance_approvers(
                approval_stage="ADMIN",
                title="Clearance Item Requires Admin Approval",
                message=(
                    f"{item.item_name} for employee "
                    f"{item.employee} has received manager "
                    "approval and is awaiting final admin approval."
                ),
                object_id=item.pk,
                branch=item.employee.branch,
            )

        return Response(
            IssuedItemSerializer(item).data
        )


class AdminApproveClearanceView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def post(self, request, pk):
        item = get_accessible_items(
            request.user
        ).filter(
            pk=pk
        ).first()

        if item is None:
            return Response(
                {"detail": "Clearance item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            item = approve_by_admin(
                issued_item_id=item.pk,
                approved_by=request.user,
            )

        except DjangoValidationError as exc:
            handle_service_error(exc)

        if (
            item.approval_status
            == IssuedItem.ApprovalStatus.APPROVED
        ):
            notify_user(
                user=item.issued_by,
                notification_type=Notification.NotificationType.INFO,
                title="Clearance Item Fully Approved",
                message=(
                    f"Your clearance item '{item.item_name}' "
                    f"for employee {item.employee} "
                    "has been fully approved."
                ),
                module="CLEARANCE",
                object_id=item.pk,
            )

        return Response(
            IssuedItemSerializer(item).data
        )


class RejectClearanceItemView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminOrManager,
    ]
    @extend_schema(
        request=ClearanceRejectionSerializer,
        responses={200: IssuedItemSerializer},
    )
    def post(self, request, pk):
        item = get_accessible_items(
            request.user
        ).filter(
            pk=pk
        ).first()

        if item is None:
            return Response(
                {"detail": "Clearance item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            request.user.role != "ADMIN"
            and not request.user.is_superuser
        ):
            if not request.user.branches.filter(
                pk=item.employee.branch_id
            ).exists():
                return Response(
                    {
                        "detail": (
                            "You cannot reject items "
                            "from this branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        reason = request.data.get(
            "rejection_reason",
            "",
        )

        stage = request.data.get(
            "stage",
            "",
        ).upper()

        if (
            stage == "ADMIN"
            and request.user.role != "ADMIN"
            and not request.user.is_superuser
        ):
            return Response(
                {
                    "detail": (
                        "Only an administrator can reject "
                        "at the admin stage."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            stage == "MANAGER"
            and request.user.role not in ["MANAGER", "ADMIN"]
            and not request.user.is_superuser
        ):
            return Response(
                {
                    "detail": (
                        "Only a manager or administrator can "
                        "reject at the manager stage."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            item = reject_issued_item(
                issued_item_id=item.pk,
                rejected_by=request.user,
                rejection_reason=reason,
                stage=stage,
            )

        except DjangoValidationError as exc:
            handle_service_error(exc)

        # Notify the person who issued the item.
        notify_user(
            user=item.issued_by,
            notification_type=Notification.NotificationType.WARNING,
            title="Clearance Item Rejected",
            message=(
                f"Your clearance item '{item.item_name}' "
                f"for employee {item.employee} was rejected. "
                f"Reason: {item.rejection_reason}"
            ),
            module="CLEARANCE",
            object_id=item.pk,
        )

        return Response(
            IssuedItemSerializer(item).data
        )


class ClearancePaymentListCreateView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdminOrStaff,
    ]

    def get(self, request):
        from organization.services.user_branch_service import (
            get_accessible_branches,
        )

        branch_ids = get_accessible_branches(
            request.user
        ).values_list(
            "id",
            flat=True,
        )

        payments = ClearancePayment.objects.filter(
            issued_item__employee__branch_id__in=branch_ids
        ).select_related(
            "issued_item",
            "issued_item__employee",
            "recorded_by",
        )

        employee_id = request.query_params.get(
            "employee"
        )

        if employee_id:
            payments = payments.filter(
                issued_item__employee_id=employee_id
            )

        return Response(
            ClearancePaymentSerializer(
                payments,
                many=True,
            ).data
        )

    @extend_schema(
        request=ClearancePaymentSerializer,
        responses={201: ClearancePaymentSerializer},
    )
    def post(self, request):
        serializer = ClearancePaymentSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        issued_item_id = serializer.validated_data[
            "issued_item"
        ].pk

        item = get_accessible_items(
            request.user
        ).filter(
            pk=issued_item_id
        ).first()

        if item is None:
            raise ValidationError({
                "issued_item": (
                    "Clearance item not found or inaccessible."
                )
            })

        try:
            payment = record_clearance_payment(
                issued_item_id=item.pk,
                amount=serializer.validated_data["amount"],
                payment_method=serializer.validated_data[
                    "payment_method"
                ],
                recorded_by=request.user,
                payment_date=serializer.validated_data.get(
                    "payment_date"
                ),
                reference=serializer.validated_data.get(
                    "reference",
                    "",
                ),
                notes=serializer.validated_data.get(
                    "notes",
                    "",
                ),
            )

        except DjangoValidationError as exc:
            handle_service_error(exc)

        # Preserve the existing payment notification behavior.
        notify_admins_and_managers(
            notification_type=Notification.NotificationType.INFO,
            title="Clearance Payment Recorded",
            message=(
                f"A payment of ₹{payment.amount} was recorded "
                f"for {item.item_name}, employee {item.employee}."
            ),
            module="CLEARANCE",
            object_id=item.pk,
            branch=item.employee.branch,
        )

        return Response(
            ClearancePaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )