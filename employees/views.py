from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
)
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema,OpenApiTypes
from organization.services.access_service import (
    get_accessible_branches,
)
from .services import create_salary_revision
from .models import Employee,EmployeeIdentityProof
from .permissions import (
    CanManageEmployees,
    CanManageEmployeeSalary,)
from .serializers import (
    EmployeeSerializer,
    EmployeeIdentityProofSerializer,
    EmployeeIdentityProofUploadSerializer,
    EmployeeSalaryHistorySerializer
)
from .services.identity_proof_service import (
    create_identity_proof,
    get_identity_proof_file_url
)


class EmployeeViewSet(viewsets.ModelViewSet):

    serializer_class = EmployeeSerializer

    permission_classes = [
        CanManageEmployees
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            Employee.objects
            .select_related(
                "branch",
                "department",
            )
            .order_by("-id")
        )

        # ---------------------------------
        # Branch access
        # ---------------------------------

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

        # ---------------------------------
        # Branch filter
        # ---------------------------------

        branch_id = self.request.query_params.get(
            "branch"
        )

        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        # ---------------------------------
        # Department filter
        # ---------------------------------

        department_id = self.request.query_params.get(
            "department"
        )

        if department_id:
            queryset = queryset.filter(
                department_id=department_id
            )

        # ---------------------------------
        # Designation filter
        # ---------------------------------

        designation = self.request.query_params.get(
            "designation"
        )

        if designation:
            queryset = queryset.filter(
                designation__iexact=designation
            )

        return queryset

    @extend_schema(
    request=EmployeeIdentityProofUploadSerializer,
    responses=EmployeeIdentityProofSerializer,
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="identity-proof",
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def identity_proof(
        self,
        request,
        pk=None,
    ):

        employee = self.get_object()

        self.check_object_permissions(
            request,
            employee,
        )

        # =========================
        # GET
        # =========================

        if request.method == "GET":

            try:
                identity_proof = employee.identity_proof

            except EmployeeIdentityProof.DoesNotExist:

                return Response(
                    {
                        "detail": (
                            "Identity proof not found "
                            "for this employee."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = (
                EmployeeIdentityProofSerializer(
                    identity_proof
                )
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # =========================
        # POST
        # =========================

        document_type = request.data.get(
            "document_type"
        )

        document_number = request.data.get(
            "document_number"
        )

        file = request.FILES.get("file")

        if not document_type:
            return Response(
                {
                    "detail": (
                        "document_type is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not document_number:
            return Response(
                {
                    "detail": (
                        "document_number is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file:
            return Response(
                {
                    "detail": "file is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            identity_proof = create_identity_proof(
                employee=employee,
                document_type=document_type,
                document_number=document_number,
                file=file,
                uploaded_by=request.user,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = (
            EmployeeIdentityProofSerializer(
                identity_proof
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
    responses={
        200: OpenApiTypes.URI,
    },
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="identity-proof/file",
    )
    def identity_proof_file(
        self,
        request,
        pk=None,
    ):

        employee = self.get_object()

        self.check_object_permissions(
            request,
            employee,
        )

        try:

            url = get_identity_proof_file_url(
                employee=employee,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "url": url,
            },
            status=status.HTTP_200_OK,
        )


    @extend_schema(
    request=EmployeeSalaryHistorySerializer,
    responses=EmployeeSalaryHistorySerializer,
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="salary-history",
    )
    def salary_history(self, request, pk=None):

        employee = self.get_object()

        # ==========================================
        # GET → Salary History
        # ==========================================

        if request.method == "GET":

            history = (
                employee.salary_history
                .select_related("created_by")
                .order_by("effective_from")
            )

            serializer = EmployeeSalaryHistorySerializer(
                history,
                many=True,
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # ==========================================
        # POST → Create Salary Revision
        # ==========================================

        permission = CanManageEmployeeSalary()

        if not permission.has_object_permission(
            request,
            self,
            employee,
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to change this employee's salary."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EmployeeSalaryHistorySerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            salary_history = create_salary_revision(
                employee=employee,
                salary_type=serializer.validated_data["salary_type"],
                monthly_salary=serializer.validated_data.get(
                    "monthly_salary"
                ),
                daily_wage=serializer.validated_data.get(
                    "daily_wage"
                ),
                biweekly_salary=serializer.validated_data.get(
                    "biweekly_salary"
                ),
                effective_from=serializer.validated_data[
                    "effective_from"
                ],
                reason=serializer.validated_data.get(
                    "reason",
                    "",
                ),
                created_by=request.user,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = EmployeeSalaryHistorySerializer(
            salary_history
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )