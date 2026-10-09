"""Oylik to'lov jurnali bilan ishlash servisi.

Har bir o'quvchi uchun 12 oylik katakchalar: — → ✓ (to'lagan) → ✗ (to'lamagan).

Default holatda hamma katakcha bo'sh (—) bo'ladi. Belgi faqat ustoz
bosganda yoki ro'yxatga olishda oylar tanlanganda chiqadi.
"""

from __future__ import annotations

import logging
from datetime import date as _date
from typing import Any

from database.database import DATABASE
from database.models import MonthlyPayment, Student

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "Yan", "Fev", "Mar", "Apr", "May", "Iyn",
    "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek",
]

# Ko'rsatish tartibi: avgustdan boshlanib iyulda tugaydi
MONTH_ORDER = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]

MONTH_FULL_NAMES = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def ordered_months() -> list[tuple[int, str]]:
    """(oy_raqami, oy_nomi) juftliklari — avgustdan boshlanadi."""
    return [(m, MONTH_NAMES[m - 1]) for m in MONTH_ORDER]


def get_matrix(year: int, search: str = "") -> tuple[list[dict], dict[int, dict[int, bool | None]]]:
    """Berilgan yil uchun o'quvchilar ro'yxati + 12 oylik katakchalar."""
    from sqlalchemy import or_

    with DATABASE.session() as s:
        query = s.query(Student)
        if search.strip():
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(Student.full_name.ilike(like), Student.phone.ilike(like))
            )
        students = query.order_by(Student.full_name.asc(), Student.id.asc()).all()
        ids = [st.id for st in students]

        lookup: dict[tuple[int, int], dict] = {}
        if ids:
            rows = (
                s.query(MonthlyPayment)
                .filter(
                    MonthlyPayment.student_id.in_(ids),
                    MonthlyPayment.year == year,
                )
                .all()
            )
            lookup = {
                (r.student_id, r.month): {"paid": r.paid, "amount": r.amount or 0.0}
                for r in rows
            }

        student_list = [
            {
                "id": st.id,
                "full_name": st.full_name,
                "fee": st.fee or 0.0,
                "created_display": (
                    st.created_at.strftime("%d.%m.%Y") if st.created_at else "—"
                ),
            }
            for st in students
        ]
        matrix: dict[int, dict[int, dict | None]] = {}
        for st in students:
            row = {}
            for m in range(1, 13):
                cell = lookup.get((st.id, m))
                row[m] = dict(cell) if cell else None
            matrix[st.id] = row
        return student_list, matrix


def _to_amount(value) -> float:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return max(0.0, amount)


def set_status(
    student_id: int, year: int, month: int, paid: bool | None, amount: float = 0.0
) -> str:
    """Katakchani o'rnatish (None = o'chirish). Yangi holatni qaytaradi.

    Qaytadi: "1" (to'lagan), "0" (to'lamagan), "none" (bo'sh).
    """
    if not 1 <= month <= 12:
        raise ValueError("Oy 1 dan 12 gacha bo'lishi kerak.")
    amount = _to_amount(amount)
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        row = (
            s.query(MonthlyPayment)
            .filter(
                MonthlyPayment.student_id == student_id,
                MonthlyPayment.year == year,
                MonthlyPayment.month == month,
            )
            .first()
        )
        who = st.full_name
        if paid is None:
            if row:
                s.delete(row)
            result = "none"
        elif row:
            row.paid = paid
            row.amount = amount if paid else 0.0
            result = "1" if paid else "0"
        else:
            s.add(
                MonthlyPayment(
                    student_id=student_id,
                    year=year,
                    month=month,
                    paid=paid,
                    amount=amount if paid else 0.0,
                )
            )
            result = "1" if paid else "0"
    from services import activity_service as _act

    if paid is True:
        mark = f"✓ ({amount:,.0f}".replace(",", " ") + " so'm)"
    elif paid is False:
        mark = "✗"
    else:
        mark = "o'chirildi"
    _act.log(
        "payment",
        f"Oylik to'lov: {who} — {MONTH_NAMES[month - 1]} {year}: {mark}",
        who,
    )
    return result


def _is_paid(cell) -> bool:
    if isinstance(cell, dict):
        return cell.get("paid") is True
    return cell is True


def _is_unpaid(cell) -> bool:
    if isinstance(cell, dict):
        return cell.get("paid") is False
    return cell is False


def matrix_stats(matrix: dict) -> dict[str, Any]:
    """Ko'rsatilayotgan matritsa bo'yicha statistika: jami ✓, ✗ va summa."""
    paid = sum(1 for row in matrix.values() for v in row.values() if _is_paid(v))
    unpaid = sum(1 for row in matrix.values() for v in row.values() if _is_unpaid(v))
    collected = 0.0
    for row in matrix.values():
        for v in row.values():
            if isinstance(v, dict) and v.get("paid") is True:
                collected += v.get("amount") or 0.0
    return {"paid": paid, "unpaid": unpaid, "collected": collected}


def get_cell_detail(student_id: int, year: int, month: int) -> dict[str, Any]:
    """Bitta katakcha tafsiloti (to'lov kartochkasi modali uchun)."""
    if not 1 <= month <= 12:
        raise ValueError("Oy 1 dan 12 gacha bo'lishi kerak.")
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        row = (
            s.query(MonthlyPayment)
            .filter(
                MonthlyPayment.student_id == student_id,
                MonthlyPayment.year == year,
                MonthlyPayment.month == month,
            )
            .first()
        )
        fee = st.fee or (st.course.price if st.course else 0.0) or 0.0
        amount = (row.amount or 0.0) if row else 0.0
        paid = row.paid if row else None
        return {
            "student_id": student_id,
            "full_name": st.full_name,
            "year": year,
            "month": month,
            "month_name": MONTH_NAMES[month - 1],
            "fee": fee,
            "amount": amount,
            "paid": paid,
        }


def paid_student_ids(year: int, month: int) -> list[int]:
    """Berilgan oyda ✓ belgisi bor o'quvchilar id ro'yxati."""
    if not 1 <= month <= 12:
        return []
    with DATABASE.session() as s:
        rows = (
            s.query(MonthlyPayment.student_id)
            .filter(
                MonthlyPayment.year == year,
                MonthlyPayment.month == month,
                MonthlyPayment.paid.is_(True),
            )
            .all()
        )
        return [r[0] for r in rows]


def year_stats(year: int, search: str = "") -> dict[str, Any]:
    """Yillik statistika: jami ✓ va ✗ soni (avtomatik qiymatlar bilan)."""
    _, matrix = get_matrix(year, search=search)
    return matrix_stats(matrix)


def manual_paid_months(student_id: int) -> list[int]:
    """O'quvchining qo'lda belgilangan (✓) oylari — ro'yxatga olish yili bo'yicha."""
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st or not st.created_at:
            return []
        year = st.created_at.year
        rows = (
            s.query(MonthlyPayment.month)
            .filter(
                MonthlyPayment.student_id == student_id,
                MonthlyPayment.year == year,
                MonthlyPayment.paid.is_(True),
            )
            .all()
        )
        return sorted(r[0] for r in rows)


def set_manual_months(student_id: int, months: list[int]) -> None:
    """Qo'lda belgilangan oylarni almashtiradi (ro'yxatga olish yili).

    Belgilanmagan oylar avtomatik rejimga qaytadi (qo'lda yozuv o'chadi).
    """
    clean = sorted({m for m in months if isinstance(m, int) and 1 <= m <= 12})
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        who = st.full_name
        year = st.created_at.year if st.created_at else _date.today().year
        s.query(MonthlyPayment).filter(
            MonthlyPayment.student_id == student_id,
            MonthlyPayment.year == year,
        ).delete()
        for m in clean:
            s.add(MonthlyPayment(student_id=student_id, year=year, month=m, paid=True))
    if clean:
        from services import activity_service as _act

        names = ", ".join(MONTH_NAMES[m - 1] for m in clean)
        _act.log("payment", f"Oylik to'lovlar belgilandi: {who} — {names}", who)
