"""Hisobotlar va statistika servisi."""

from __future__ import annotations

import csv
import logging
from typing import Any

from sqlalchemy import func

from database.database import DATABASE
from database.models import Course, Payment, PaymentStatus, Student

logger = logging.getLogger(__name__)


def _money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " so'm"


def course_breakdown() -> list[dict[str, Any]]:
    """Har bir kurs bo'yicha: o'quvchilar soni, tushgan/kutilayotgan summa."""
    with DATABASE.session() as s:
        courses = s.query(Course).order_by(Course.name.asc()).all()
        breakdown = []
        for course in courses:
            students = (
                s.query(Student).filter(Student.course_id == course.id).all()
            )
            student_ids = [st.id for st in students]
            paid_count = 0
            revenue = 0.0
            expected = 0.0
            for st in students:
                from services.student_service import _fee_of

                amount = _fee_of(st)
                if st.payment_status == PaymentStatus.PAID:
                    paid_count += 1
                    revenue += amount
                else:
                    expected += amount
            generated = 0.0
            if student_ids:
                generated = (
                    s.query(func.coalesce(func.sum(Payment.amount), 0.0))
                    .filter(
                        Payment.student_id.in_(student_ids),
                        Payment.status == PaymentStatus.PAID,
                    )
                    .scalar()
                    or 0.0
                )
            breakdown.append(
                {
                    "course_id": course.id,
                    "course_name": course.name,
                    "student_count": len(students),
                    "paid_count": paid_count,
                    "revenue": max(generated, revenue),
                    "expected": expected,
                    "revenue_display": _money(max(generated, revenue)),
                    "expected_display": _money(expected),
                }
            )
        return breakdown


def summary() -> dict[str, Any]:
    """Umumiy hisobot ma'lumotlarini qaytaradi."""
    with DATABASE.session() as s:
        total = s.query(Student).count()
        paid = (
            s.query(Student)
            .filter(Student.payment_status == PaymentStatus.PAID)
            .count()
        )
        pending = (
            s.query(Student)
            .filter(Student.payment_status == PaymentStatus.PENDING)
            .count()
        )
        unpaid = (
            s.query(Student)
            .filter(Student.payment_status == PaymentStatus.UNPAID)
            .count()
        )
        actual_revenue = (
            s.query(func.coalesce(func.sum(Payment.amount), 0.0))
            .filter(Payment.status == PaymentStatus.PAID)
            .scalar()
            or 0.0
        )
        # Kutilayotgan summa = hali to'lanmagan (pending+unpaid) o'quvchilarning
        # shaxsiy kelishilgan miqdorlari yig'indisi
        from services.student_service import _fee_of

        expected = 0.0
        debtors = (
            s.query(Student)
            .filter(Student.payment_status != PaymentStatus.PAID)
            .all()
        )
        for st in debtors:
            expected += _fee_of(st)
        breakdown = course_breakdown()
        return {
            "total": total,
            "paid": paid,
            "pending": pending,
            "unpaid": unpaid,
            "actual_revenue": actual_revenue,
            "actual_revenue_display": _money(actual_revenue),
            "expected": expected,
            "expected_display": _money(expected),
            "course_breakdown": breakdown,
        }


def export_pdf(path: str | None = None) -> str:
    """Hisobotni PDF faylga eksport qiladi va fayl yo'lini qaytaradi."""
    import tempfile
    from pathlib import Path

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    data = summary()
    target = Path(path) if path else (
        Path(tempfile.gettempdir()) / "kurs_manager_hisobot.pdf"
    )

    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Kurs Manager — Hisobot",
    )

    title_style = ParagraphStyle(
        "Title2", fontName="Helvetica-Bold", fontSize=18, spaceAfter=4 * mm,
        textColor=colors.HexColor("#1d4ed8"),
    )
    h_style = ParagraphStyle(
        "H2", fontName="Helvetica-Bold", fontSize=13, spaceBefore=6 * mm,
        spaceAfter=3 * mm, textColor=colors.HexColor("#111827"),
    )
    cell = ParagraphStyle("Cell", fontName="Helvetica", fontSize=10)
    cell_b = ParagraphStyle("CellB", fontName="Helvetica-Bold", fontSize=10)

    story = [
        Paragraph("KURS MANAGER — HISOBOT", title_style),
        Paragraph(
            f"Sana: {__import__('datetime').datetime.now():%d.%m.%Y}",
            ParagraphStyle("Sub", fontName="Helvetica", fontSize=10,
                           textColor=colors.grey),
        ),
        Paragraph("Umumiy statistika", h_style),
    ]

    stat_rows = [
        [Paragraph("<b>Ko'rsatkich</b>", cell_b), Paragraph("<b>Qiymat</b>", cell_b)],
        [Paragraph("Jami o'quvchilar", cell), Paragraph(str(data["total"]), cell)],
        [Paragraph("To'lov qilganlar", cell), Paragraph(str(data["paid"]), cell)],
        [Paragraph("To'lov kutilmoqda", cell), Paragraph(str(data["pending"]), cell)],
        [Paragraph("To'lov qilmaganlar", cell), Paragraph(str(data["unpaid"]), cell)],
        [Paragraph("Jami tushgan to'lov", cell),
         Paragraph(data["actual_revenue_display"], cell)],
        [Paragraph("Kutilayotgan summa", cell),
         Paragraph(data["expected_display"], cell)],
    ]
    t1 = Table(stat_rows, colWidths=[85 * mm, 85 * mm])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t1)

    if data["course_breakdown"]:
        story.append(Paragraph("Kurslar bo'yicha", h_style))
        course_rows = [[
            Paragraph("<b>Kurs nomi</b>", cell_b),
            Paragraph("<b>O'quvchilar</b>", cell_b),
            Paragraph("<b>To'laganlar</b>", cell_b),
            Paragraph("<b>Tushgan summa</b>", cell_b),
            Paragraph("<b>Kutilayotgan</b>", cell_b),
        ]]
        for row in data["course_breakdown"]:
            course_rows.append([
                Paragraph(row["course_name"], cell),
                Paragraph(str(row["student_count"]), cell),
                Paragraph(str(row["paid_count"]), cell),
                Paragraph(row["revenue_display"], cell),
                Paragraph(row["expected_display"], cell),
            ])
        t2 = Table(course_rows, colWidths=[55 * mm, 27 * mm, 27 * mm, 33 * mm, 33 * mm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t2)

    from services import activity_service as _act
    from xml.sax.saxutils import escape as _escape

    journal = _act.list_logs(limit=500)
    story.append(Paragraph("Faoliyat jurnali (so'nggi %d)" % len(journal), h_style))
    journal_rows = [[
        Paragraph("<b>Sana</b>", cell_b),
        Paragraph("<b>Bo'lim</b>", cell_b),
        Paragraph("<b>Harakat</b>", cell_b),
    ]]
    for entry in journal:
        journal_rows.append([
            Paragraph(entry["datetime_display"], cell),
            Paragraph(_escape(entry["category"]), cell),
            Paragraph(_escape(entry["action"]), cell),
        ])
    if len(journal_rows) == 1:
        journal_rows.append([
            Paragraph("—", cell),
            Paragraph("—", cell),
            Paragraph("Hali qaydlar yo'q", cell),
        ])
    t3 = Table(journal_rows, colWidths=[32 * mm, 30 * mm, 108 * mm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t3)

    doc.build(story)
    return str(target)


def export_csv(path: str | None = None) -> str:
    """Hisobotni CSV faylga eksport qiladi va fayl yo'lini qaytaradi."""
    import tempfile
    from pathlib import Path

    data = summary()
    target = Path(path) if path else (Path(tempfile.gettempdir()) / "kurs_manager_hisobot.csv")

    with open(target, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["KURS MANAGER — HISOBOT"])
        writer.writerow([])
        writer.writerow(["Umumiy statistika"])
        writer.writerow(["Jami o'quvchilar", data["total"]])
        writer.writerow(["To'lov qilganlar", data["paid"]])
        writer.writerow(["To'lov kutilmoqda", data["pending"]])
        writer.writerow(["To'lov qilmaganlar", data["unpaid"]])
        writer.writerow(["Jami tushgan to'lov", data["actual_revenue_display"]])
        writer.writerow(["Kutilayotgan summa", data["expected_display"]])
        writer.writerow([])
        writer.writerow(["Kurslar bo'yicha"])
        writer.writerow(["Kurs nomi", "O'quvchilar soni", "To'laganlar", "Tushgan summa", "Kutilayotgan summa"])
        for row in data["course_breakdown"]:
            writer.writerow(
                [
                    row["course_name"],
                    row["student_count"],
                    row["paid_count"],
                    row["revenue_display"],
                    row["expected_display"],
                ]
            )
    return str(target)