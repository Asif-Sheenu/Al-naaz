from rest_framework import viewsets

from organization.services.access_service import (
    get_accessible_branches,
)
from datetime import date as python_date
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from .services.attendance_service import (
    save_bulk_attendance,
    )
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Attendance
from .serializers import AttendanceSerializer,DailyAttendanceSerializer,BulkAttendanceSerializer
from .permissions import CanManageAttendance
from employees.models import Employee
from .services.attendance_service import (
    save_bulk_attendance,
)


class AttendanceViewSet(viewsets.ModelViewSet):

    serializer_class = AttendanceSerializer
    permission_classes = [CanManageAttendance]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            Attendance.objects
            .select_related(
                "employee",
                "employee__branch",
            )
            .order_by("-date")
        )

        # ADMIN / SUPERUSER → all active branches
        if (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            pass

        # MANAGER / STAFF → only accessible branches
        else:
            accessible_branch_ids = (
                get_accessible_branches(user)
                .values_list(
                    "id",
                    flat=True,
                )
            )

            queryset = queryset.filter(
                employee__branch_id__in=accessible_branch_ids
            )

        # -----------------------------
        # Filters
        # -----------------------------

        employee = self.request.query_params.get(
            "employee"
        )

        date = self.request.query_params.get(
            "date"
        )

        status = self.request.query_params.get(
            "status"
        )

        year = self.request.query_params.get(
            "year"
        )

        month = self.request.query_params.get(
            "month"
        )

        start_date = self.request.query_params.get(
            "start_date"
        )

        end_date = self.request.query_params.get(
            "end_date"
        )

        designation = self.request.query_params.get(
            "designation"
        )

        search = self.request.query_params.get(
            "search"
        )

        if employee:
            queryset = queryset.filter(
                employee_id=employee
            )

        if date:
            queryset = queryset.filter(
                date=date
            )

        if status:
            queryset = queryset.filter(
                status=status
            )

        if month:
            queryset = queryset.filter(
                date__month=month
            )

        if year:
            queryset = queryset.filter(
                date__year=year
            )

        if start_date and end_date:
            queryset = queryset.filter(
                date__range=[
                    start_date,
                    end_date,
                ]
            )

        if designation:
            queryset = queryset.filter(
                employee__designation__iexact=designation
            )

        if search:
            queryset = queryset.filter(
                employee__name__icontains=search
            )

        return queryset
    

    @extend_schema(
    parameters=[
        OpenApiParameter(
            name="branch",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Branch ID.",
        ),
        OpenApiParameter(
            name="date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Attendance date in YYYY-MM-DD format.",
        ),
    ],
    responses=DailyAttendanceSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="daily",
    )
    def daily(self, request):

        branch_id = request.query_params.get(
            "branch"
        )

        attendance_date = request.query_params.get(
            "date"
        )

        if not branch_id:
            return Response(
                {
                    "detail": "branch is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not attendance_date:
            return Response(
                {
                    "detail": "date is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------------
        # Validate date
        # ------------------------------------------------

        try:
            attendance_date = python_date.fromisoformat(
                attendance_date
            )
        except ValueError:
            return Response(
                {
                    "detail": (
                        "Invalid date format. "
                        "Use YYYY-MM-DD."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        # ------------------------------------------------
        # Validate branch access
        # ------------------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            if not get_accessible_branches(user).filter(
                pk=branch_id
            ).exists():

                return Response(
                    {
                        "detail": (
                            "You do not have access "
                            "to this branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ------------------------------------------------
        # Get active employees in branch
        # ------------------------------------------------

        employees = (
            Employee.objects
            .filter(
                branch_id=branch_id,
                is_active=True,
            )
            .order_by("name")
        )

        # ------------------------------------------------
        # Get existing attendance for this date
        # ------------------------------------------------

        employee_ids = employees.values_list(
            "id",
            flat=True,
        )

        attendance_records = (
            Attendance.objects
            .filter(
                employee_id__in=employee_ids,
                date=attendance_date,
            )
        )

        attendance_map = {
            record.employee_id: record
            for record in attendance_records
        }

        # ------------------------------------------------
        # Build daily response
        # ------------------------------------------------

        data = []

        for employee in employees:

            attendance = attendance_map.get(
                employee.id
            )

            data.append(
                {
                    "employee": employee.id,
                    "employee_name": employee.name,
                    "designation": employee.designation,
                    "status": (
                        attendance.status
                        if attendance
                        else None
                    ),
                    "is_paid": attendance.is_paid if attendance else True,

                    "remarks": (
                        attendance.remarks
                        if attendance
                        else ""
                    ),
                }
            )

        serializer = DailyAttendanceSerializer(
            data,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=BulkAttendanceSerializer,
        responses=AttendanceSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="bulk",
    )
    def bulk(self, request):

        serializer = BulkAttendanceSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        branch_id = serializer.validated_data[
            "branch"
        ]

        attendance_date = serializer.validated_data[
            "date"
        ]

        records = serializer.validated_data[
            "records"
        ]

        user = request.user

        # -----------------------------------------
        # Check branch access
        # -----------------------------------------

        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):

            if not get_accessible_branches(user).filter(
                pk=branch_id
            ).exists():

                return Response(
                    {
                        "detail": (
                            "You do not have access "
                            "to this branch."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # -----------------------------------------
        # Save attendance
        # -----------------------------------------

        try:

            result = save_bulk_attendance(
                branch_id=branch_id,
                attendance_date=attendance_date,
                records=records,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------------------
        # Serialize results
        # -----------------------------------------

        response_serializer = AttendanceSerializer(
            result["records"],
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "message": (
                    "Attendance saved successfully."
                ),
                "created_count": (
                    result["created_count"]
                ),
                "updated_count": (
                    result["updated_count"]
                ),
                "records": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    

    @extend_schema(
    parameters=[
        OpenApiParameter(
            name="branch",
            type=OpenApiTypes.INT,
            required=True,
        ),
        OpenApiParameter(
            name="month",
            type=OpenApiTypes.INT,
            required=True,
        ),
        OpenApiParameter(
            name="year",
            type=OpenApiTypes.INT,
            required=True,
        ),
    ],
    responses=OpenApiTypes.OBJECT,
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="summary",
    )
    def summary(self, request):

        branch_id = request.query_params.get("branch")
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        if not branch_id or not month or not year:
            return Response(
                {
                    "detail": "branch, month and year are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            month = int(month)
            year = int(year)
            branch_id = int(branch_id)
        except ValueError:
            return Response(
                {
                    "detail": "branch, month and year must be valid integers."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month < 1 or month > 12:
            return Response(
                {
                    "detail": "month must be between 1 and 12."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        # Branch access check
        if not (
            user.is_superuser
            or user.role == "ADMIN"
        ):
            if not get_accessible_branches(user).filter(
                pk=branch_id
            ).exists():
                return Response(
                    {
                        "detail": "You do not have access to this branch."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Get employees in branch
        employees = Employee.objects.filter(
            branch_id=branch_id,
            is_active=True,
        ).order_by("name")

        # Get attendance records for the month
        attendance_records = Attendance.objects.filter(
            employee__branch_id=branch_id,
            employee__is_active=True,
            date__year=year,
            date__month=month,
        )

        # Group records by employee
        attendance_by_employee = {}

        for record in attendance_records:
            attendance_by_employee.setdefault(
                record.employee_id,
                []
            ).append(record)

        results = []

        for employee in employees:

            records = attendance_by_employee.get(
                employee.id,
                []
            )

            present = sum(
                1 for record in records
                if record.status == Attendance.Status.PRESENT
            )

            absent = sum(
                1 for record in records
                if record.status == Attendance.Status.ABSENT
            )

            half_day = sum(
                1 for record in records
                if record.status == Attendance.Status.HALF_DAY
            )

            leave = sum(
                1 for record in records
                if record.status == Attendance.Status.LEAVE
            )

            results.append(
                {
                    "employee": employee.id,
                    "employee_name": employee.name,
                    "designation": employee.designation,
                    "present": present,
                    "absent": absent,
                    "half_day": half_day,
                    "leave": leave,
                    "total_marked_days": len(records),
                }
            )

        return Response(
            {
                "branch": branch_id,
                "month": month,
                "year": year,
                "employees": results,
            },
            status=status.HTTP_200_OK,
        )