"""To'lov muddati push-xabarlari (web + desktop uchun umumiy)."""

from __future__ import annotations

import logging
from typing import Any

from database.database import DATABASE
from database.models import Student
from services.student_service import payment_schedule

logger = logging.getLogger(__name__)


def get_payment_dues() -> list[dict[str, Any]]:
    """Muddati yaqinlashgan/kechikkan to'lovlar ro'yxati.

    Har bir o'quvchi+middaat uchun BIR marta qaytaradi (settings'da belgi
    qo'yiladi, spam bo'lmaydi).
    """
    items = []
    with DATABASE.session() as s:
        students = s.query(Student).all()
        for st in students:
            sched = payment_schedule(st.created_at, st.payment_status)
            kind = sched["kind"]
            tag = None
            if kind == "overdue":
                tag = "over"
            elif kind == "today":
                tag = "0"
            elif kind in ("upcoming", "next") and 1 <= sched["days_left"] <= 3:
                tag = str(sched["days_left"])
            if tag is None:
                continue
            key = f"paydue_{st.id}_{sched['due_iso']}_{tag}"
            if DATABASE.get_setting(key) == "1":
                continue
            DATABASE.set_setting(key, "1")
            if kind == "overdue":
                text = f"{st.full_name}: {sched['label']} ({sched['due_display']})"
            elif kind == "today":
                text = f"{st.full_name}: Bugun to'lov kuni! ({sched['due_display']})"
            else:
                text = (
                    f"{st.full_name}: {sched['days_left']} kundan keyin "
                    f"({sched['due_display']})"
                )
            items.append(
                {
                    "id": f"pay-{st.id}",
                    "student_id": st.id,
                    "full_name": st.full_name,
                    "text": text,
                    "kind": kind,
                }
            )
    return items