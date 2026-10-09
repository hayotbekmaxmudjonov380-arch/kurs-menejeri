"""Test natijalari bilan ishlash servisi."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func as _func
from sqlalchemy import or_

from database.database import DATABASE
from database.models import Student, TestResult

logger = logging.getLogger(__name__)


def grade_info(percentage: float) -> tuple[str, str]:
    """Foizga qarab baho nomi va rangini qaytaradi."""
    if percentage >= 85:
        return ("A'lo", "green")
    if percentage >= 70:
        return ("Yaxshi", "blue")
    if percentage >= 55:
        return ("Qoniqarli", "amber")
    return ("Qoniqarsiz", "red")


def calc_percentage(total: int, correct: int) -> float:
    if total <= 0:
        return 0.0
    return round(correct * 100 / total, 1)


def _to_dict(t: TestResult) -> dict[str, Any]:
    grade, color = grade_info(t.percentage or 0.0)
    return {
        "id": t.id,
        "student_id": t.student_id,
        "full_name": t.student.full_name if t.student else "—",
        "phone": t.student.phone if t.student else "—",
        "topic": t.topic,
        "total_questions": t.total_questions,
        "correct_answers": t.correct_answers,
        "percentage": t.percentage or 0.0,
        "grade": grade,
        "grade_color": color,
        "result_date": t.result_date,
        "date_display": t.result_date.strftime("%d.%m.%Y") if t.result_date else "",
        "note": t.note,
    }


def _validate(total: int, correct: int) -> None:
    if total <= 0:
        raise ValueError("Savollar soni 0 dan katta bo'lishi kerak.")
    if correct < 0:
        raise ValueError("To'g'ri javoblar soni manfiy bo'lishi mumkin emas.")
    if correct > total:
        raise ValueError("To'g'ri javoblar savollar sonidan ko'p bo'lishi mumkin emas.")


def list_results(
    search: str = "",
    limit: int | None = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        query = s.query(TestResult).join(TestResult.student)
        if search.strip():
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(like),
                    Student.phone.ilike(like),
                    TestResult.topic.ilike(like),
                )
            )
        query = query.order_by(TestResult.result_date.desc(), TestResult.id.desc())
        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return [_to_dict(t) for t in query.all()]


def count_results(search: str = "") -> int:
    with DATABASE.session() as s:
        query = s.query(_func.count(TestResult.id)).join(TestResult.student)
        if search.strip():
            like = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(like),
                    Student.phone.ilike(like),
                    TestResult.topic.ilike(like),
                )
            )
        return query.scalar() or 0


def get_result(result_id: int) -> dict[str, Any] | None:
    with DATABASE.session() as s:
        t = s.query(TestResult).filter(TestResult.id == result_id).first()
        return _to_dict(t) if t else None


def create_result(
    student_id: int,
    topic: str,
    total_questions: int,
    correct_answers: int,
    result_date: datetime | None = None,
    note: str = "",
) -> int:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Test mavzusini kiriting.")
    _validate(total_questions, correct_answers)
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        t = TestResult(
            student_id=student_id,
            topic=topic,
            total_questions=total_questions,
            correct_answers=correct_answers,
            percentage=calc_percentage(total_questions, correct_answers),
            result_date=result_date or datetime.now(),
            note=(note or "").strip(),
        )
        s.add(t)
        s.flush()
        new_id = t.id
        who = st.full_name
        pct = t.percentage
    from services import activity_service as _act

    _act.log(
        "test",
        f"Test natijasi: {who} — {topic}: {correct_answers}/{total_questions} ({pct}%)",
        who,
    )
    return new_id


def update_result(
    result_id: int,
    topic: str,
    total_questions: int,
    correct_answers: int,
    result_date: datetime | None = None,
    note: str = "",
) -> None:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Test mavzusini kiriting.")
    _validate(total_questions, correct_answers)
    with DATABASE.session() as s:
        t = s.query(TestResult).filter(TestResult.id == result_id).first()
        if not t:
            raise ValueError("Natija topilmadi.")
        t.topic = topic
        t.total_questions = total_questions
        t.correct_answers = correct_answers
        t.percentage = calc_percentage(total_questions, correct_answers)
        if result_date:
            t.result_date = result_date
        t.note = (note or "").strip()
        from services.sync_service import touch as _touch

        _touch(t)
        who = t.student.full_name if t.student else ""
        pct = t.percentage
    from services import activity_service as _act

    _act.log(
        "test",
        f"Test natijasi yangilandi: {who} — {topic}: {correct_answers}/{total_questions} ({pct}%)",
        who,
    )


def delete_result(result_id: int) -> None:
    with DATABASE.session() as s:
        t = s.query(TestResult).filter(TestResult.id == result_id).first()
        if not t:
            raise ValueError("Natija topilmadi.")
        who = t.student.full_name if t.student else ""
        topic = t.topic
        gone_uid = t.uid or ""
        s.delete(t)
    from services import activity_service as _act
    from services.sync_service import tomb as _tomb

    _tomb("test_results", result_id, gone_uid)
    _act.log("test", f"Test natijasi o'chirildi: {who} — {topic}", who)