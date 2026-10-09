"""Demo ma'lumotlar (development/test uchun)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from database.database import DATABASE
from database.models import Course, Payment, PaymentStatus, Student

logger = logging.getLogger(__name__)


DEMO_COURSES = [
    ("Kimyo fani", 500_000),
]

DEMO_STUDENTS = [
    ("Abdullayev Azizbek", "+998 90 123 45 67"),
    ("Karimova Madina", "+998 91 234 56 78"),
    ("Tursunov Said", "+998 93 345 67 89"),
    ("Raxmatov Javohir", "+998 94 456 78 90"),
    ("Qodirova Dilshoda", "+998 95 567 89 01"),
    ("Islomov Behruz", "+998 90 111 22 33"),
    ("Yusupova Nilufar", "+998 91 222 33 44"),
    ("Ergashev Sardor", "+998 93 333 44 55"),
    ("Nematova Aziza", "+998 94 444 55 66"),
    ("Xolmatov Jasur", "+998 95 555 66 77"),
    ("Rahimova Gulnoza", "+998 90 666 77 88"),
    ("Sobirov Davron", "+998 91 777 88 99"),
    ("Aliyeva Feruza", "+998 93 888 99 00"),
    ("To'lqinov Ulug'bek", "+998 94 999 00 11"),
    ("Murodova Shaxnoza", "+998 95 112 23 44"),
    ("Komilov Oybek", "+998 90 223 34 55"),
    ("Saidova Munisa", "+998 91 334 45 66"),
    ("Normatov Ravshan", "+998 93 445 56 77"),
    ("G'aniyev Farrux", "+998 94 556 67 88"),
    ("Sultanova Umida", "+998 95 667 78 99"),
    ("Yodgorov Asad", "+998 90 778 89 11"),
    ("Mavlonova Sevinch", "+998 91 889 90 22"),
    ("Temirov Javlon", "+998 93 990 01 33"),
    ("Rasulova Dilnoza", "+998 94 112 23 44"),
    ("Olimov Sherzod", "+998 95 223 34 55"),
    ("Bekova Kamila", "+998 90 334 45 66"),
    ("Hamidov Zafar", "+998 91 445 56 77"),
    ("Norboyeva Shahzoda", "+998 93 556 67 88"),
]


def _status_for(index: int) -> str:
    if index < 18:
        return PaymentStatus.PAID
    if index < 23:
        return PaymentStatus.PENDING
    return PaymentStatus.UNPAID


def ensure_courses() -> None:
    """Faqat kurslarni yaratadi (o'quvchisiz — exe toza ochilishi uchun).

    Mavjud kurslarga tegmaydi, yetishmaydiganlarini qo'shadi.
    """
    with DATABASE.session() as s:
        for name, price in DEMO_COURSES:
            existing = s.query(Course).filter(Course.name == name).first()
            if not existing:
                s.add(Course(name=name, price=price, active=True))
    logger.info("Kurslar tekshirildi.")


def seed() -> None:
    """Database'ga demo ma'lumotlarni FAQAT bir marta kiritadi.

    Qayta ishga tushirishlarda yoki foydalanuvchi o'quvchilarni
    o'chirib tashlaganda qayta yuklanmaydi (settings jadvalidagi
    'seeded' bayrog'i orqali nazorat qilinadi).
    """
    if DATABASE.get_setting("seeded") == "1":
        return
    with DATABASE.session() as s:
        if s.query(Student).count() > 0:
            DATABASE.set_setting("seeded", "1")
            return

        course_ids = []
        for name, price in DEMO_COURSES:
            existing = s.query(Course).filter(Course.name == name).first()
            if existing:
                course_ids.append(existing.id)
            else:
                course = Course(name=name, price=price, active=True)
                s.add(course)
                s.flush()
                course_ids.append(course.id)

        now = datetime.now()
        for idx, (name, phone) in enumerate(DEMO_STUDENTS):
            status = _status_for(idx)
            course_id = course_ids[idx % len(course_ids)]
            days_ago = 3 + idx * 3
            created_date = now - timedelta(days=days_ago)
            st = Student(
                full_name=name,
                phone=phone,
                course_id=course_id,
                payment_status=status,
                note="",
                created_at=created_date,
            )
            s.add(st)
            s.flush()
            course = s.query(Course).filter(Course.id == course_id).first()
            amount = course.price if course else 0.0
            s.add(
                Payment(
                    student_id=st.id,
                    amount=amount,
                    status=status,
                    payment_date=created_date,
                    note="Dastlabki holat",
                )
            )
    logger.info("Demo ma'lumotlar yuklandi (%d o'quvchi).", len(DEMO_STUDENTS))
    DATABASE.set_setting("seeded", "1")