"""SQLAlchemy models for Kurs Manager.

Jadvallar: courses, students, payments, settings
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_uid() -> str:
    """Yozuvga beriladigan global identifikator (sinxron uchun).

    `id` ikki qurilmada bir xil bo'lmasligi mumkin, `uid` esa
    dunyo bo'ylab bir xil — shu bilan merge xavfsiz ishlaydi.
    """
    import uuid

    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class PaymentStatus:
    """To'lov holati kalitlari (database'da shu kalitlar saqlanadi)."""

    PAID = "paid"            # To'lov qilingan  -> yashil
    PENDING = "pending"      # Kutilmoqda       -> sariq
    UNPAID = "unpaid"        # To'lov qilinmagan -> qizil

    ALL = (PAID, PENDING, UNPAID)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    students: Mapped[list["Student"]] = relationship(
        back_populates="course", passive_deletes=True
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    course_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PAID
    )
    fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grade: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    course: Mapped[Optional["Course"]] = relationship(back_populates="students")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentStatus.PAID)
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    student: Mapped["Student"] = relationship(back_populates="payments")


class TestResult(Base):
    """O'quvchilarning test natijalari."""

    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    result_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    student: Mapped["Student"] = relationship()


class Reminder(Base):
    """Eslatmalar (rejalashtirilgan ishlar)."""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remind_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)


class Group(Base):
    """O'quvchilar guruhlari."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    members: Mapped[list["GroupMember"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GroupMember(Base):
    """Guruh a'zoligi (o'quvchi bir nechta guruhda bo'lishi mumkin)."""

    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "student_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    group: Mapped["Group"] = relationship(back_populates="members")
    student: Mapped["Student"] = relationship()


class ActivityLog(Base):
    """Faoliyat jurnali — dasturdagi har bir o'zgarish qaydi."""

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    student_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class MonthlyPayment(Base):
    """Oylik to'lov jurnali (har bir o'quvchi + yil + oy uchun bitta yozuv)."""

    __tablename__ = "monthly_payments"
    __table_args__ = (UniqueConstraint("student_id", "year", "month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    student: Mapped["Student"] = relationship()


class Attendance(Base):
    """Davomat (har bir o'quvchi + sana uchun bitta yozuv)."""

    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "att_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    att_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=datetime.now)
    uid: Mapped[str] = mapped_column(String(32), nullable=False, default=new_uid, unique=True, index=True)

    student: Mapped["Student"] = relationship()


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")


class TrustedDevice(Base):
    """Juftlangan telefonlar (bir martalik koddan keyin eslab qolinadi)."""

    __tablename__ = "trusted_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    device_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    paired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class Tombstone(Base):
    """O'chirilgan yozuvlar qaydi (sinxron paytida qayta 'tirilmasligi' uchun)."""

    __tablename__ = "tombstones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    row_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # Sinxron kaliti — boshqa qurilmadagi mahalliy id bilan emas, shu bilan
    # o'chirish to'g'ri yozuvga tedi (har doim ham to'g'ri kelmaydi).
    row_uid: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("table_name", "row_id"),
        UniqueConstraint("table_name", "row_uid"),
    )