"""To'lovlar bilan ishlash servisi."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from database.database import DATABASE
from database.models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


def list_payments(
    search: str = "",
    status: str | None = None,
    limit: int | None = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        query = s.query(Payment).join(Payment.student)
        if search.strip():
            like = f"%{search.strip()}%"
            from database.models import Student

            query = query.filter(
                (Student.full_name.ilike(like)) | (Student.phone.ilike(like))
            )
        if status in PaymentStatus.ALL:
            query = query.filter(Payment.status == status)
        query = query.order_by(Payment.payment_date.desc(), Payment.id.desc())
        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        rows = query.all()
        result = []
        for p in rows:
            from services.student_service import payment_schedule as _sched

            sched = _sched(
                p.student.created_at if p.student else None,
                p.student.payment_status if p.student else "unpaid",
            )
            result.append(
                {
                    "id": p.id,
                    "student_id": p.student_id,
                    "full_name": p.student.full_name,
                    "phone": p.student.phone,
                    "course_name": (
                        p.student.course.name if p.student.course else "—"
                    ),
                    "amount": p.amount,
                    "status": p.status,
                    "payment_date": p.payment_date,
                    "date_display": p.payment_date.strftime("%d.%m.%Y"),
                    "note": p.note,
                    "due_display": sched["due_display"],
                    "due_label": sched["label"],
                    "due_kind": sched["kind"],
                }
            )
        return result


def add_payment(
    student_id: int,
    amount: float,
    status: str,
    payment_date: datetime | None = None,
    note: str = "",
) -> int:
    with DATABASE.session() as s:
        payment = Payment(
            student_id=student_id,
            amount=amount,
            status=status,
            payment_date=payment_date or datetime.now(),
            note=note.strip(),
        )
        s.add(payment)
        s.flush()
        return payment.id


def update_payment(payment_id, amount, status, payment_date, note) -> None:
    with DATABASE.session() as s:
        payment = s.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError("To'lov topilmadi.")
        payment.amount = amount
        payment.status = status
        payment.payment_date = payment_date
        payment.note = note.strip()


def delete_payment(payment_id: int) -> None:
    with DATABASE.session() as s:
        payment = s.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError("To'lov topilmadi.")
        s.delete(payment)


def count_payments(search: str = "", status: str | None = None) -> int:
    from sqlalchemy import func as _func

    with DATABASE.session() as s:
        query = s.query(_func.count(Payment.id)).join(Payment.student)
        if search.strip():
            like = f"%{search.strip()}%"
            from database.models import Student

            query = query.filter(
                (Student.full_name.ilike(like)) | (Student.phone.ilike(like))
            )
        if status in PaymentStatus.ALL:
            query = query.filter(Payment.status == status)
        return query.scalar() or 0


def list_by_student(student_id: int) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        rows = (
            s.query(Payment)
            .filter(Payment.student_id == student_id)
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
            .all()
        )
        return [
            {
                "id": p.id,
                "amount": p.amount,
                "status": p.status,
                "date_display": p.payment_date.strftime("%d.%m.%Y"),
                "note": p.note,
            }
            for p in rows
        ]