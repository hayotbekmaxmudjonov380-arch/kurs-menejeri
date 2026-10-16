"""O'quvchilar bilan ishlash servisi."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from database.database import DATABASE
from database.models import Payment, PaymentStatus, Student

logger = logging.getLogger(__name__)


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y") if dt else ""


def _fee_of(st: Student) -> float:
    """O'quvchining kelishilgan to'lov miqdori (bo'lmasa kurs narxi)."""
    fee = st.fee or 0.0
    if fee > 0:
        return fee
    return st.course.price if st.course else 0.0


def add_months(dt, months: int):
    """Oy qo'shish (oy oxiri kunlarini to'g'ri hisoblaydi)."""
    from calendar import monthrange
    from datetime import date as _date

    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return _date(year, month, day)


def payment_schedule(created_at, payment_status: str) -> dict[str, Any]:
    """Har bir o'quvchining SHAXSIY oylik to'lov jadvalini hisoblaydi.

    Anchor = ro'yxatdan o'tgan sana. Birinchi muddat = +1 oy - 1 kun
    (masalan 1-dekabr -> 31-dekabr).
    """
    from datetime import date as _date
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    today = _date.today()
    if isinstance(created_at, _dt):
        base = created_at.date()
    else:
        base = created_at or today

    # Bugundan keyingi birinchi deadline
    k = 1
    while add_months(base, k) - _td(days=1) < today:
        k += 1
        if k > 1200:
            break
    due = add_months(base, k) - _td(days=1)

    if payment_status == PaymentStatus.PAID:
        # To'langan -> keyingi oy muddati
        nxt = add_months(base, k + 1) - _td(days=1)
        days = (nxt - today).days
        return {
            "due_date": nxt,
            "due_iso": nxt.isoformat(),
            "due_display": nxt.strftime("%d.%m.%Y"),
            "days_left": days,
            "kind": "next",
            "label": f"{days} kun qoldi",
        }

    if k == 1:
        days = (due - today).days
        if days <= 0:
            return {
                "due_date": due,
                "due_iso": due.isoformat(),
                "due_display": due.strftime("%d.%m.%Y"),
                "days_left": 0,
                "kind": "today",
                "label": "Bugun to'lov kuni!",
            }
        return {
            "due_date": due,
            "due_iso": due.isoformat(),
            "due_display": due.strftime("%d.%m.%Y"),
            "days_left": days,
            "kind": "upcoming",
            "label": f"{days} kun qoldi",
        }

    # Oldingi deadline o'tkazib yuborilgan
    prev = add_months(base, k - 1) - _td(days=1)
    over = (today - prev).days
    return {
        "due_date": prev,
        "due_iso": prev.isoformat(),
        "due_display": prev.strftime("%d.%m.%Y"),
        "days_left": -over,
        "kind": "overdue",
        "label": f"{over} kun kechikkan",
    }


def calc_paid_percent(total_price: float, paid_amount: float) -> float:
    """To'langan foiz: 0-100 (total 0 bo'lsa 0)."""
    try:
        total = float(total_price or 0)
        paid = float(paid_amount or 0)
    except (TypeError, ValueError):
        return 0.0
    if total <= 0 or paid <= 0:
        return 0.0
    return round(paid * 100 / total, 1)


def student_to_dict(st: Student) -> dict[str, Any]:
    fee = st.fee or 0.0
    total_price = st.total_price or 0.0
    paid_amount = st.paid_amount or 0.0
    sched = payment_schedule(st.created_at, st.payment_status)
    return {
        "id": st.id,
        "full_name": st.full_name,
        "phone": st.phone,
        "course_id": st.course_id,
        "course_name": st.course.name if st.course else "—",
        "payment_status": st.payment_status,
        "fee": fee,
        "fee_display": f"{fee:,.0f}".replace(",", " ") + " so'm" if fee > 0 else "—",
        "total_price": total_price,
        "paid_amount": paid_amount,
        "paid_percent": calc_paid_percent(total_price, paid_amount),
        "grade": st.grade or "",
        "grade_display": st.grade if st.grade else "—",
        "due_display": sched["due_display"],
        "due_label": sched["label"],
        "due_kind": sched["kind"],
        "days_left": sched["days_left"],
        "note": st.note,
        "created_at": st.created_at,
        "created_display": _fmt(st.created_at),
    }


def list_students(
    search: str = "",
    status: str | None = None,
    course_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        query = s.query(Student)
        if search.strip():
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(Student.full_name.ilike(like), Student.phone.ilike(like))
            )
        if status in PaymentStatus.ALL:
            query = query.filter(Student.payment_status == status)
        if course_id is not None:
            query = query.filter(Student.course_id == course_id)
        query = query.order_by(Student.created_at.desc(), Student.id.desc())
        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        rows = query.all()
        return [student_to_dict(st) for st in rows]


def count_students(
    search: str = "",
    status: str | None = None,
    course_id: int | None = None,
) -> int:
    from sqlalchemy import func as _func

    with DATABASE.session() as s:
        query = s.query(_func.count(Student.id))
        if search.strip():
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(Student.full_name.ilike(like), Student.phone.ilike(like))
            )
        if status in PaymentStatus.ALL:
            query = query.filter(Student.payment_status == status)
        if course_id is not None:
            query = query.filter(Student.course_id == course_id)
        return query.scalar() or 0


def get_student(student_id: int) -> dict[str, Any] | None:
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            return None
        data = student_to_dict(st)
        from services.monthly_payment_service import manual_paid_months

        data["paid_months"] = manual_paid_months(student_id)
        from services.group_service import groups_for_student

        data["group_ids"] = groups_for_student(student_id)
        return data


def _to_amount(value, default: float = 0.0) -> float:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return max(0.0, amount)


GRADES = ["7-sinf", "8-sinf", "9-sinf", "10-sinf", "11-sinf"]


def _clean_grade(value) -> str:
    value = (value or "").strip()
    return value if value in GRADES else ""


def create_student(
    full_name: str,
    phone: str,
    course_id: int | None,
    payment_status: str,
    note: str = "",
    created_at: datetime | None = None,
    fee: float = 0.0,
    paid_months: list[int] | None = None,
    total_price: float = 0.0,
    paid_amount: float = 0.0,
    grade: str = "",
) -> int:
    with DATABASE.session() as s:
        if _similar_student_exists(s, full_name, phone):
            raise ValueError("Bu F.I.Sh yoki telefon raqami allaqachon ro'yxatda mavjud.")
        fee = _to_amount(fee)
        if fee <= 0:
            fee = _course_price(s, course_id)
        total_price = _to_amount(total_price, fee)
        if total_price <= 0:
            total_price = fee
        paid_amount = _to_amount(paid_amount)
        st = Student(
            full_name=full_name.strip(),
            phone=phone.strip(),
            course_id=course_id,
            payment_status=payment_status,
            fee=fee,
            total_price=total_price,
            paid_amount=paid_amount,
            grade=_clean_grade(grade),
            note=note.strip(),
            created_at=created_at or datetime.now(),
        )
        s.add(st)
        s.flush()
        # Kirish statusini to'lov tarixida saqlaymiz
        s.add(
            Payment(
                student_id=st.id,
                amount=fee,
                status=payment_status,
                payment_date=st.created_at,
                note="Dastlabki holat",
            )
        )
        new_id = st.id
        new_name = st.full_name
    if paid_months:
        from services.monthly_payment_service import set_manual_months

        set_manual_months(new_id, paid_months)
    from services import activity_service as _act

    grade_text = f" ({st.grade})" if st.grade else ""
    _act.log("student", f"Yangi o'quvchi qo'shildi: {new_name}{grade_text}", new_name)
    return new_id


def update_student(student_id, full_name, phone, course_id, payment_status, note, fee=None, paid_months=None, created_day=None, created_at=None, total_price=None, paid_amount=None, grade=None) -> None:
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        st.full_name = full_name.strip()
        st.phone = phone.strip()
        st.course_id = course_id
        st.payment_status = payment_status
        st.note = note.strip()
        if fee is not None:
            fee = _to_amount(fee)
            if fee <= 0:
                fee = _course_price(s, course_id)
            st.fee = fee
        if total_price is not None:
            st.total_price = _to_amount(total_price, st.fee or 0.0)
        if paid_amount is not None:
            st.paid_amount = _to_amount(paid_amount)
        if grade is not None:
            st.grade = _clean_grade(grade)
        if created_at is not None:
            if isinstance(created_at, datetime):
                st.created_at = created_at
            else:
                raise ValueError("Sanani to'g'ri kiriting.")
        elif created_day is not None:
            from calendar import monthrange

            try:
                day = int(created_day)
            except (TypeError, ValueError):
                raise ValueError("Kunni to'g'ri kiriting (1-31).")
            base = st.created_at or datetime.now()
            max_day = monthrange(base.year, base.month)[1]
            day = max(1, min(day, max_day))
            # Faqat KUN o'zgaradi (oy/yil o'zgarmaydi — oy belgilari saqlanadi)
            st.created_at = datetime(base.year, base.month, day)
        from services.sync_service import touch as _touch

        _touch(st)
    if paid_months is not None:
        from services.monthly_payment_service import set_manual_months

        set_manual_months(student_id, paid_months)
    from services import activity_service as _act

    _act.log(
        "student", f"O'quvchi tahrirlandi: {full_name.strip()}", full_name.strip()
    )


def delete_student(student_id: int) -> None:
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        gone_name = st.full_name
        gone_uid = st.uid or ""
        # Kaskad o'chiriladigan bolalarni o'chirishdan oldin yig'ish
        from services.sync_service import collect_cascade

        kids = collect_cascade([st])
        s.delete(st)
    from services import activity_service as _act
    from services.sync_service import tomb as _tomb, tomb_rows as _tomb_rows

    _tomb("students", student_id, gone_uid)
    for tbl, rows in kids.items():
        _tomb_rows(tbl, rows)
    _act.log("student", f"O'quvchi o'chirildi: {gone_name}", gone_name)


def set_payment_status(student_id: int, new_status: str, note: str = "") -> None:
    """To'lov holatini o'zgartirib, to'lov tarixiga yozadi."""
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        if new_status not in (PaymentStatus.PAID, PaymentStatus.UNPAID):
            raise ValueError("Noto'g'ri holat.")
        old_status = st.payment_status
        st.payment_status = new_status
        who = st.full_name
        from services.sync_service import touch as _touch

        _touch(st)
        amount = _fee_of(st)
        s.add(
            Payment(
                student_id=st.id,
                amount=amount,
                status=new_status,
                payment_date=datetime.now(),
                note=note or f"Holat o'zgartirildi: {old_status} → {new_status}",
            )
        )
    from database.models import PaymentStatus as _PS

    labels = {_PS.PAID: "To'lov qilingan", _PS.PENDING: "Kutilmoqda", _PS.UNPAID: "To'lov qilinmagan"}
    from services import activity_service as _act

    _act.log(
        "payment",
        f"To'lov holati: {who}: {labels.get(old_status, old_status)} → {labels.get(new_status, new_status)}",
        who,
    )


def get_stats() -> dict[str, int]:
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
        return {"total": total, "paid": paid, "pending": pending, "unpaid": unpaid}


def _course_price(s, course_id) -> float:
    from database.models import Course

    if course_id is None:
        return 0.0
    course = s.query(Course).filter(Course.id == course_id).first()
    return course.price if course else 0.0


def _similar_student_exists(s, full_name: str, phone: str) -> bool:
    like = f"%{full_name.strip()}%"
    if s.query(Student).filter(Student.full_name.ilike(like)).first() is not None:
        return True
    phone = (phone or "").strip()
    if phone:
        return s.query(Student).filter(Student.phone == phone).first() is not None
    return False


def _load_students_from_rows(rows) -> list[dict[str, Any]]:
    return [student_to_dict(r) for r in rows]


# SQLAlchemyError nuqtasiga umumiy yordamchi — kerak bo'lsa axborot berish uchun
def normalize_error(exc: Exception) -> str:
    if isinstance(exc, SQLAlchemyError):
        return "Ma'lumotlar bazasi xatosi yuz berdi. Iltimos qayta urinib ko'ring."
    return str(exc) or "Noma'lum xatolik yuz berdi."