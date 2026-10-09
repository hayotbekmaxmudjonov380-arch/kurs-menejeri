"""Eslatmalar bilan ishlash servisi."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func as _func

from database.database import DATABASE
from database.models import Reminder

logger = logging.getLogger(__name__)


def _to_dict(r: Reminder) -> dict[str, Any]:
    now = datetime.now()
    if r.is_done:
        status, color = "Bajarildi", "green"
    elif r.remind_at and r.remind_at < now:
        status, color = "Muddati o'tgan", "red"
    else:
        status, color = "Kutilmoqda", "amber"
    return {
        "id": r.id,
        "title": r.title,
        "note": r.note,
        "remind_at": r.remind_at,
        "date_display": r.remind_at.strftime("%d.%m.%Y") if r.remind_at else "—",
        "time_display": r.remind_at.strftime("%H:%M") if r.remind_at else "—",
        "datetime_display": r.remind_at.strftime("%d.%m.%Y %H:%M") if r.remind_at else "—",
        "datetime_input": r.remind_at.strftime("%Y-%m-%dT%H:%M") if r.remind_at else "",
        "is_done": r.is_done,
        "status": status,
        "status_color": color,
    }


def list_reminders(show_done: bool = True) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        query = s.query(Reminder)
        if not show_done:
            query = query.filter(Reminder.is_done.is_(False))
        rows = query.order_by(Reminder.remind_at.asc(), Reminder.id.desc()).all()
        return [_to_dict(r) for r in rows]


def pending_count() -> int:
    with DATABASE.session() as s:
        return (
            s.query(_func.count(Reminder.id))
            .filter(Reminder.is_done.is_(False))
            .scalar()
            or 0
        )


def get_reminder(reminder_id: int) -> dict[str, Any] | None:
    with DATABASE.session() as s:
        r = s.query(Reminder).filter(Reminder.id == reminder_id).first()
        return _to_dict(r) if r else None


def create_reminder(title: str, note: str, remind_at: datetime) -> int:
    title = (title or "").strip()
    if not title:
        raise ValueError("Eslatma sarlavhasini kiriting.")
    if not remind_at:
        raise ValueError("Sana va vaqtni belgilang.")
    with DATABASE.session() as s:
        r = Reminder(
            title=title,
            note=(note or "").strip(),
            remind_at=remind_at,
        )
        s.add(r)
        s.flush()
        new_id = r.id
    from services import activity_service as _act

    _act.log(
        "reminder",
        f"Eslatma qo'shildi: {title} ({remind_at.strftime('%d.%m.%Y %H:%M')})",
    )
    return new_id


def update_reminder(
    reminder_id: int, title: str, note: str, remind_at: datetime | None
) -> None:
    title = (title or "").strip()
    if not title:
        raise ValueError("Eslatma sarlavhasini kiriting.")
    with DATABASE.session() as s:
        r = s.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not r:
            raise ValueError("Eslatma topilmadi.")
        r.title = title
        r.note = (note or "").strip()
        if remind_at:
            r.remind_at = remind_at
            r.notified = False
        from services.sync_service import touch as _touch

        _touch(r)
    from services import activity_service as _act

    _act.log("reminder", f"Eslatma yangilandi: {title}")


def delete_reminder(reminder_id: int) -> None:
    with DATABASE.session() as s:
        r = s.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not r:
            raise ValueError("Eslatma topilmadi.")
        gone_title = r.title
        gone_uid = r.uid or ""
        s.delete(r)
    from services import activity_service as _act
    from services.sync_service import tomb as _tomb

    _tomb("reminders", reminder_id, gone_uid)
    _act.log("reminder", f"Eslatma o'chirildi: {gone_title}")


def set_done(reminder_id: int, done: bool) -> None:
    with DATABASE.session() as s:
        r = s.query(Reminder).filter(Reminder.id == reminder_id).first()
        if r:
            r.is_done = done
            done_title = r.title
            from services.sync_service import touch as _touch

            _touch(r)
        else:
            return
    from services import activity_service as _act

    _act.log(
        "reminder",
        f"Eslatma {'bajarildi' if done else 'qayta ochildi'}: {done_title}",
    )


def get_due() -> list[dict[str, Any]]:
    """Vaqti kelgan va hali xabar berilmagan eslatmalar.

    Qaytarilganlar `notified=True` deb belgilanadi (bir marta chiqishi uchun).
    """
    now = datetime.now()
    with DATABASE.session() as s:
        rows = (
            s.query(Reminder)
            .filter(
                Reminder.is_done.is_(False),
                Reminder.notified.is_(False),
                Reminder.remind_at <= now,
            )
            .order_by(Reminder.remind_at.asc())
            .all()
        )
        result = [_to_dict(r) for r in rows]
        for r in rows:
            r.notified = True
        return result