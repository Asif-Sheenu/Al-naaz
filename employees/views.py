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

from .models import Employee,EmployeeIdentityProof
from .permissions import CanManageEmployees
from .serializers import (
    EmployeeSerializer,
    EmployeeIdentityProofSerializer,
    EmployeeIdentityProofUploadSerializer
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
            .select_related("branch")
            .order_by("-id")
        )

        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            return queryset

        accessible_branch_ids = (
            get_accessible_branches(user)
            .values_list(
                "id",
                flat=True,
            )
        )

        return queryset.filter(
            branch_id__in=accessible_branch_ids
        )

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