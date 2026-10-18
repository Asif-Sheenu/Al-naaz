from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from organization.services.access_service import get_accessible_branches
from .services.dashboard_service import get_dashboard_data


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            month_param = request.query_params.get("month")
            year_param = request.query_params.get("year")
            branch_param = request.query_params.get("branch")

            month = int(month_param) if month_param else None
            year = int(year_param) if year_param else None

            # Get branches the user is authorized to access.
            accessible_branches = get_accessible_branches(request.user)

            # Optional branch filter.
            branch_id = None

            if branch_param is not None:
                branch_id = int(branch_param)

                if branch_id <= 0:
                    raise ValueError(
                        "Branch must be a positive integer."
                    )

                if not accessible_branches.filter(
                    id=branch_id
                ).exists():
                    raise ValidationError({
                        "branch": (
                            "Branch does not exist or you do not "
                            "have permission to access it."
                        )
                    })

            data = get_dashboard_data(
                user=request.user,
                month=month,
                year=year,
                branch_id=branch_id,
            )

            return Response(data, status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )