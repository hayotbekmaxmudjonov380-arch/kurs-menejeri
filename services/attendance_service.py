"""Davomat bilan ishlash servisi."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from database.database import DATABASE
from database.models import Attendance, Student

logger = logging.getLogger(__name__)

WEEKDAYS = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]


def week_dates(offset: int = 0) -> list[date]:
    """Berilgan hafta siljishi uchun Du-Ya sanalar ro'yxati."""
    today = date.today()
    monday = today - timedelta_days(today.weekday()) + timedelta_days(7 * offset)
    return [monday + timedelta_days(i) for i in range(7)]


def timedelta_days(n: int):
    from datetime import timedelta

    return timedelta(days=n)


def get_matrix(dates: list[date]) -> tuple[list[dict], dict[int, dict[str, bool | None]], dict[int, dict]]:
    """Haftalik davomat matritsasi: o'quvchilar + katakchalar + statistika."""
    with DATABASE.session() as s:
        students = (
            s.query(Student).order_by(Student.full_name.asc(), Student.id.asc()).all()
        )
        isos = [d.isoformat() for d in dates]
        rows = (
            s.query(Attendance)
            .filter(Attendance.att_date.in_(dates))
            .all()
        )
        lookup = {(r.student_id, r.att_date.isoformat()): r.present for r in rows}

        student_list = [
            {"id": st.id, "full_name": st.full_name} for st in students
        ]
        matrix: dict[int, dict[str, bool | None]] = {}
        stats: dict[int, dict] = {}
        for st in students:
            cells = {iso: lookup.get((st.id, iso)) for iso in isos}
            matrix[st.id] = cells
            present = sum(1 for v in cells.values() if v is True)
            absent = sum(1 for v in cells.values() if v is False)
            # Foiz haftaning 7 kuniga nisbatan: 1 kun ✓ = 14%
            pct = round(present * 100 / 7)
            stats[st.id] = {"present": present, "absent": absent, "pct": pct}
        return student_list, matrix, stats


def set_attendance(student_id: int, att_date: date, present: bool | None) -> dict:
    """Katakchani o'rnatish (None = o'chirish). Yangi statistika qaytadi."""
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        row = (
            s.query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.att_date == att_date,
            )
            .first()
        )
        from services.sync_service import touch as _touch
        from services.sync_service import tomb as _tomb

        if present is None:
            if row:
                _tomb("attendance", row.id, row.uid or "")
                s.delete(row)
        else:
            if row:
                row.present = present
                _touch(row)
            else:
                s.add(Attendance(student_id=student_id, att_date=att_date, present=present))
        s.flush()
        # Shu o'quvchining joriy haftadagi statistikasi
        monday = att_date - timedelta_days(att_date.weekday())
        dates = [monday + timedelta_days(i) for i in range(7)]
        isos = [d.isoformat() for d in dates]
        vals = [
            r.present
            for r in s.query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.att_date.in_(dates),
            )
            .all()
        ]
        present_n = sum(1 for v in vals if v is True)
        absent_n = sum(1 for v in vals if v is False)
        pct = round(present_n * 100 / 7)
        state = "none" if present is None else ("1" if present else "0")
        who = st.full_name
    from services import activity_service as _act

    mark = "✓" if present is True else ("✗" if present is False else "o'chirildi")
    _act.log(
        "attendance",
        f"Davomat: {who} — {att_date.strftime('%d.%m.%Y')}: {mark}",
        who,
    )
    return {"state": state, "present": present_n, "absent": absent_n, "pct": pct}