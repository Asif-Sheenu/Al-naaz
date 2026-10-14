from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .services.dashboard_service import get_dashboard_data


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            month_param = request.query_params.get("month")
            year_param = request.query_params.get("year")

            month = int(month_param) if month_param else None
            year = int(year_param) if year_param else None

            data = get_dashboard_data(
                user=request.user,
                month=month,
                year=year,
            )

            return Response(data, status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
