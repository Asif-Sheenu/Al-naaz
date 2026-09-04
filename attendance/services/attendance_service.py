from django.db import transaction

from employees.models import Employee

from ..models import Attendance


@transaction.atomic
def save_bulk_attendance(
    *,
    branch_id,
    attendance_date,
    records,
):
    employee_ids = [
        record["employee"]
        for record in records
    ]

    # Prevent duplicate employee IDs
    if len(employee_ids) != len(set(employee_ids)):
        raise ValueError(
            "An employee can appear only once in an attendance request."
        )

    # Get only active employees belonging
    # to the requested branch.
    employees = (
        Employee.objects
        .filter(
            id__in=employee_ids,
            branch_id=branch_id,
            is_active=True,
        )
    )

    employees_by_id = {
        employee.id: employee
        for employee in employees
    }

    # Every submitted employee must belong
    # to this branch and be active.
    invalid_employee_ids = [
        employee_id
        for employee_id in employee_ids
        if employee_id not in employees_by_id
    ]

    if invalid_employee_ids:
        raise ValueError(
            "One or more employees do not belong "
            "to this branch or are inactive."
        )

    # Get existing attendance records for
    # this branch/date.
    existing_records = (
        Attendance.objects
        .filter(
            employee_id__in=employee_ids,
            date=attendance_date,
        )
    )

    existing_by_employee = {
        record.employee_id: record
        for record in existing_records
    }

    created_count = 0
    updated_count = 0

    results = []

    for record in records:

        employee_id = record["employee"]

        attendance = existing_by_employee.get(
            employee_id
        )

        if attendance:

            # Existing record → update
            attendance.status = record["status"]
            attendance.is_paid = record.get("is_paid", True)

            attendance.remarks = record.get(
                "remarks",
                "",
            )

            attendance.save(
                update_fields=[
                    "status",
                    "is_paid",
                    "remarks",
                ]
            )

            updated_count += 1

        else:

            # No record → create
            attendance = Attendance.objects.create(
                employee=employees_by_id[
                    employee_id
                ],
                date=attendance_date,
                status=record["status"],
                is_paid=record.get("is_paid", True),

                remarks=record.get(
                    "remarks",
                    "",
                ),
            )

            created_count += 1

        results.append(attendance)

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "records": results,
    }