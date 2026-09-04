from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import User
from users.permissions import IsAdmin
from drf_spectacular.utils import extend_schema
from .models import Branch, Company,Department
from .serializers import BranchSerializer, CompanySerializer,AssignUserSerializer,RemoveUserSerializer,DepartmentSerializer
from .services.user_branch_service import (
    assign_user_to_branch,
    remove_user_from_branch,
    get_accessible_branches
)
from .permissions import (
    CanAccessBranch,
    CanManageBranches,
    CanManageDepartments,
    CanAccessDepartment,
)

class CompanyViewSet(viewsets.ModelViewSet):

    queryset = (
        Company.objects
        .prefetch_related("branches")
        .order_by("name")
    )

    serializer_class = CompanySerializer
    permission_classes = [IsAdmin]


class BranchViewSet(viewsets.ModelViewSet):

    serializer_class = BranchSerializer

    def get_permissions(self):

        if self.action in ["list", "retrieve"]:
            permission_classes = [CanAccessBranch]
        else:
            permission_classes = [CanManageBranches]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):

        user = self.request.user

        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return (
                Branch.objects
                .select_related("company")
                .prefetch_related("users")
                .order_by("name")
            )

        return (
            get_accessible_branches(user)
            .prefetch_related("users")
            .order_by("name")
        )
    
    @extend_schema(
    request=AssignUserSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="assign-user",
    )
    def assign_user(self, request, pk=None):

        branch = self.get_object()

        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {
                    "detail": "user_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(
                pk=user_id
            )
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "User not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            assign_user_to_branch(
                branch=branch,
                user=user,
            )
        except ValueError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "User assigned to branch successfully."
                ),
                "branch": branch.name,
                "user": user.username,
            },
            status=status.HTTP_200_OK,
        )
    @extend_schema(
        request=RemoveUserSerializer,
        )
    @action(
        detail=True,
        methods=["post"],
        url_path="remove-user",
    )
    def remove_user(self, request, pk=None):

        branch = self.get_object()

        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {
                    "detail": "user_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(
                pk=user_id
            )
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "User not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        remove_user_from_branch(
            branch=branch,
            user=user,
        )

        return Response(
            {
                "message": (
                    "User removed from branch successfully."
                ),
                "branch": branch.name,
                "user": user.username,
            },
            status=status.HTTP_200_OK,
        )




class DepartmentViewSet(viewsets.ModelViewSet):

    serializer_class = DepartmentSerializer

    def get_permissions(self):

        if self.action in ["list", "retrieve"]:
            permission_classes = [CanAccessDepartment]
        else:
            permission_classes = [CanManageDepartments]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            Department.objects
            .select_related("branch")
            .order_by("name")
        )

        # ==========================================
        # BRANCH ACCESS
        # ==========================================

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list(
                    "id",
                    flat=True,
                )
            )

            queryset = queryset.filter(
                branch_id__in=accessible_branch_ids
            )

        # ==========================================
        # BRANCH FILTER
        # ==========================================

        branch_id = self.request.query_params.get(
            "branch"
        )

        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        return queryset