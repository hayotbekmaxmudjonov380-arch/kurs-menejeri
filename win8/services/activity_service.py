"""Faoliyat jurnali servisi — har bir o'zgarishni qayd qiladi."""

from __future__ import annotations

import logging
from typing import Any

from database.database import DATABASE
from database.models import ActivityLog

logger = logging.getLogger(__name__)

CATEGORIES = {
    "student": "O'quvchilar",
    "payment": "To'lovlar",
    "test": "Testlar",
    "attendance": "Davomat",
    "reminder": "Eslatmalar",
    "group": "Guruhlar",
}


def log(category: str, action: str, student_name: str = "") -> None:
    """Jurnalga yozuv qo'shadi. Xatoda dastur to'xtamaydi."""
    try:
        with DATABASE.session() as s:
            s.add(
                ActivityLog(
                    category=category,
                    action=(action or "").strip(),
                    student_name=(student_name or "").strip(),
                )
            )
    except Exception:
        logger.exception("Jurnalga yozishda xatolik")


def list_logs(limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        rows = (
            s.query(ActivityLog)
            .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "category": CATEGORIES.get(r.category, r.category),
                "action": r.action,
                "student_name": r.student_name,
                "created_at": r.created_at,
                "datetime_display": (
                    r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else "—"
                ),
            }
            for r in rows
        ]


def count_logs() -> int:
    from sqlalchemy import func as _func

    with DATABASE.session() as s:
        return s.query(_func.count(ActivityLog.id)).scalar() or 0
