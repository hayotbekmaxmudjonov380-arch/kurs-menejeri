"""Kurslar bilan ishlash servisi."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func

from database.database import DATABASE
from database.models import Course, Payment, PaymentStatus, Student

logger = logging.getLogger(__name__)


def list_courses(include_inactive: bool = True) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        query = (
            s.query(Course)
            .outerjoin(Student, Student.course_id == Course.id)
            .group_by(Course.id)
            .order_by(Course.created_at.desc(), Course.id.desc())
        )
        rows = query.all()
        result = []
        for course in rows:
            count = (
                s.query(func.count(Student.id))
                .filter(Student.course_id == course.id)
                .scalar()
            )
            result.append(_course_to_dict(course, count))
        return result


def active_courses() -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        rows = (
            s.query(Course)
            .filter(Course.active.is_(True))
            .order_by(Course.name.asc())
            .all()
        )
        return [_course_to_dict(c) for c in rows]


def all_courses() -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        rows = s.query(Course).order_by(Course.name.asc()).all()
        return [_course_to_dict(c) for c in rows]


def _course_to_dict(course: Course, student_count: int = 0) -> dict[str, Any]:
    return {
        "id": course.id,
        "name": course.name,
        "price": course.price,
        "active": course.active,
        "student_count": student_count,
        "created_at": course.created_at,
        "created_display": course.created_at.strftime("%d.%m.%Y"),
    }


def get_course(course_id: int) -> dict[str, Any] | None:
    with DATABASE.session() as s:
        course = s.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None
        count = (
            s.query(func.count(Student.id))
            .filter(Student.course_id == course.id)
            .scalar()
        )
        return _course_to_dict(course, count or 0)


def create_course(name: str, price: float, active: bool = True) -> int:
    with DATABASE.session() as s:
        exists = s.query(Course).filter(Course.name == name.strip()).first()
        if exists:
            raise ValueError("Bu nomdagi kurs allaqachon mavjud.")
        course = Course(name=name.strip(), price=price, active=active)
        s.add(course)
        s.flush()
        return course.id


def update_course(course_id: int, name: str, price: float, active: bool) -> None:
    with DATABASE.session() as s:
        course = s.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError("Kurs topilmadi.")
        dup = (
            s.query(Course)
            .filter(Course.name == name.strip(), Course.id != course_id)
            .first()
        )
        if dup:
            raise ValueError("Bu nomdagi kurs allaqachon mavjud.")
        course.name = name.strip()
        course.price = price
        course.active = active


def set_course_active(course_id: int, active: bool) -> None:
    with DATABASE.session() as s:
        course = s.query(Course).filter(Course.id == course_id).first()
        if course:
            course.active = active


def delete_course(course_id: int) -> None:
    with DATABASE.session() as s:
        course = s.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError("Kurs topilmadi.")
        student_count = (
            s.query(func.count(Student.id))
            .filter(Student.course_id == course_id)
            .scalar()
        )
        if student_count:
            raise ValueError(
                f"Bu kursda {student_count} ta o'quvchi bor. "
                "Avval ularni boshqa kursga o'tkazing yoki kursni nofaol qiling."
            )
        s.delete(course)