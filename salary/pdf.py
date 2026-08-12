from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_payslip_pdf(salary):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20,
    )

    normal_style = styles["Normal"]

    elements = []

    # Company title
    elements.append(
        Paragraph("AL NAAZ MANDI", title_style)
    )

    elements.append(
        Paragraph(
            "SALARY PAYSLIP",
            ParagraphStyle(
                "Subtitle",
                parent=normal_style,
                alignment=TA_CENTER,
                fontSize=14,
            )
        )
    )

    elements.append(Spacer(1, 20))

    employee = salary.employee

    # Employee information
    employee_data = [
        ["Employee", employee.name],
        ["Designation", employee.designation],
        ["Salary Month", f"{salary.month}/{salary.year}"],
        ["Salary Type", salary.salary_type],
    ]

    employee_table = Table(
        employee_data,
        colWidths=[130, 330],
    )

    employee_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(employee_table)

    elements.append(Spacer(1, 20))

    # Attendance information
    attendance_data = [
        ["Attendance", "Days"],
        ["Working Days", salary.working_days],
        ["Present Days", salary.present_days],
        ["Half Days", salary.half_days],
        ["Absent Days", salary.absent_days],
        ["Leave Days", salary.leave_days],
    ]

    attendance_table = Table(
        attendance_data,
        colWidths=[230, 230],
    )

    attendance_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(attendance_table)

    elements.append(Spacer(1, 20))

    # Salary information
    salary_data = [
        ["Salary Details", "Amount"],
        ["Gross Salary", f"Rs. {salary.gross_salary}"],
        ["Advance Deduction", f"Rs. {salary.advance_deduction}"],
        ["Net Salary", f"Rs. {salary.net_salary}"],
    ]

    salary_table = Table(
        salary_data,
        colWidths=[230, 230],
    )

    salary_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(salary_table)

    elements.append(Spacer(1, 20))

    # Payment information
    payment_date = (
        salary.payment_date.strftime("%d-%m-%Y")
        if salary.payment_date
        else "Not Paid"
    )

    payment_data = [
        ["Status", salary.status],
        ["Payment Date", payment_date],
    ]

    payment_table = Table(
        payment_data,
        colWidths=[130, 330],
    )

    payment_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    elements.append(payment_table)

    elements.append(Spacer(1, 30))

    elements.append(
        Paragraph(
            "This is a computer-generated payslip.",
            ParagraphStyle(
                "Footer",
                parent=normal_style,
                alignment=TA_CENTER,
                fontSize=9,
            )
        )
    )

    document.build(elements)

    buffer.seek(0)

    return buffer