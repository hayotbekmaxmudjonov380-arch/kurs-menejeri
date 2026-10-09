"""Guruhlar bilan ishlash servisi."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func as _func

from database.database import DATABASE
from database.models import Group, GroupMember, Student

logger = logging.getLogger(__name__)


def _group_to_dict(group: Group, member_count: int = 0) -> dict[str, Any]:
    return {
        "id": group.id,
        "name": group.name,
        "member_count": member_count,
        "created_at": group.created_at,
        "created_display": (
            group.created_at.strftime("%d.%m.%Y") if group.created_at else "—"
        ),
    }


def list_groups() -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        groups = s.query(Group).order_by(Group.created_at.desc(), Group.id.desc()).all()
        result = []
        for g in groups:
            count = (
                s.query(_func.count(GroupMember.id))
                .filter(GroupMember.group_id == g.id)
                .scalar()
                or 0
            )
            result.append(_group_to_dict(g, count))
        return result


def get_group(group_id: int) -> dict[str, Any] | None:
    with DATABASE.session() as s:
        g = s.query(Group).filter(Group.id == group_id).first()
        if not g:
            return None
        count = (
            s.query(_func.count(GroupMember.id))
            .filter(GroupMember.group_id == g.id)
            .scalar()
            or 0
        )
        return _group_to_dict(g, count)


def create_group(name: str) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Guruh nomini kiriting.")
    with DATABASE.session() as s:
        exists = s.query(Group).filter(Group.name == name).first()
        if exists:
            raise ValueError("Bu nomdagi guruh allaqachon mavjud.")
        g = Group(name=name)
        s.add(g)
        s.flush()
        new_id = g.id
    from services import activity_service as _act

    _act.log("group", f"Guruh ochildi: {name}")
    return new_id


def update_group(group_id: int, name: str) -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("Guruh nomini kiriting.")
    with DATABASE.session() as s:
        g = s.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise ValueError("Guruh topilmadi.")
        dup = (
            s.query(Group)
            .filter(Group.name == name, Group.id != group_id)
            .first()
        )
        if dup:
            raise ValueError("Bu nomdagi guruh allaqachon mavjud.")
        old_name = g.name
        g.name = name
    from services import activity_service as _act

    _act.log("group", f"Guruh nomi o'zgartirildi: {old_name} → {name}")


def delete_group(group_id: int) -> None:
    """Guruhni o'chiradi (o'quvchilar o'chmaydi, faqat a'zoliklar o'chadi)."""
    with DATABASE.session() as s:
        g = s.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise ValueError("Guruh topilmadi.")
        gone_name = g.name
        s.delete(g)
    from services import activity_service as _act

    _act.log("group", f"Guruh o'chirildi: {gone_name}")


def list_members(group_id: int) -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        rows = (
            s.query(GroupMember)
            .join(GroupMember.student)
            .filter(GroupMember.group_id == group_id)
            .order_by(Student.full_name.asc())
            .all()
        )
        return [
            {
                "member_id": r.id,
                "student_id": r.student_id,
                "full_name": r.student.full_name if r.student else "—",
                "phone": r.student.phone if r.student else "—",
                # O'quvchining JONLI to'lov holati (har safar bazadan o'qiladi)
                "payment_status": (
                    r.student.payment_status if r.student else "unpaid"
                ),
                "created_display": (
                    r.student.created_at.strftime("%d.%m.%Y")
                    if r.student and r.student.created_at else "—"
                ),
            }
            for r in rows
        ]


def available_students(group_id: int) -> list[dict[str, Any]]:
    """Guruhga hali qo'shilmagan o'quvchilar."""
    with DATABASE.session() as s:
        in_group = (
            s.query(GroupMember.student_id)
            .filter(GroupMember.group_id == group_id)
            .scalar_subquery()
        )
        rows = (
            s.query(Student)
            .filter(~Student.id.in_(in_group))
            .order_by(Student.full_name.asc())
            .all()
        )
        return [
            {"id": st.id, "full_name": st.full_name, "phone": st.phone}
            for st in rows
        ]


def add_member(group_id: int, student_id: int) -> None:
    with DATABASE.session() as s:
        g = s.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise ValueError("Guruh topilmadi.")
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        exists = (
            s.query(GroupMember)
            .filter(
                GroupMember.group_id == group_id,
                GroupMember.student_id == student_id,
            )
            .first()
        )
        if exists:
            raise ValueError("Bu o'quvchi allaqachon guruhda.")
        s.add(GroupMember(group_id=group_id, student_id=student_id))
        who = st.full_name
        where = g.name
    from services import activity_service as _act

    _act.log("group", f"Guruhga qo'shildi: {who} → {where}", who)


def remove_member(group_id: int, student_id: int) -> None:
    with DATABASE.session() as s:
        row = (
            s.query(GroupMember)
            .filter(
                GroupMember.group_id == group_id,
                GroupMember.student_id == student_id,
            )
            .first()
        )
        if not row:
            raise ValueError("A'zolik topilmadi.")
        who = row.student.full_name if row.student else ""
        where = row.group.name if row.group else ""
        s.delete(row)
    from services import activity_service as _act

    _act.log("group", f"Guruhdan chiqarildi: {who} ← {where}", who)


def groups_for_student(student_id: int) -> list[int]:
    """O'quvchi a'zo bo'lgan guruhlar id ro'yxati."""
    with DATABASE.session() as s:
        rows = (
            s.query(GroupMember.group_id)
            .filter(GroupMember.student_id == student_id)
            .all()
        )
        return [r[0] for r in rows]


def set_student_groups(student_id: int, group_ids: list[int]) -> None:
    """O'quvchining guruhlarini almashtiradi (belgilanmaganlar o'chadi)."""
    clean = sorted({g for g in group_ids if isinstance(g, int) and g > 0})
    with DATABASE.session() as s:
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        for gid in clean:
            if not s.query(Group).filter(Group.id == gid).first():
                raise ValueError("Guruh topilmadi.")
        s.query(GroupMember).filter(
            GroupMember.student_id == student_id
        ).delete()
        for gid in clean:
            s.add(GroupMember(group_id=gid, student_id=student_id))


def move_member(from_group_id: int, to_group_id: int, student_id: int) -> str:
    """O'quvchini bir guruhdan boshqasiga ko'chiradi.

    Qaytaradi: maqsad guruh nomi. Bitta tranzaksiyada bajariladi.
    """
    if from_group_id == to_group_id:
        raise ValueError("O'quvchi allaqachon shu guruhda.")
    with DATABASE.session() as s:
        src = s.query(Group).filter(Group.id == from_group_id).first()
        dst = s.query(Group).filter(Group.id == to_group_id).first()
        if not src or not dst:
            raise ValueError("Guruh topilmadi.")
        st = s.query(Student).filter(Student.id == student_id).first()
        if not st:
            raise ValueError("O'quvchi topilmadi.")
        row = (
            s.query(GroupMember)
            .filter(
                GroupMember.group_id == from_group_id,
                GroupMember.student_id == student_id,
            )
            .first()
        )
        if not row:
            raise ValueError("O'quvchi bu guruhda emas.")
        exists = (
            s.query(GroupMember)
            .filter(
                GroupMember.group_id == to_group_id,
                GroupMember.student_id == student_id,
            )
            .first()
        )
        if exists:
            raise ValueError("O'quvchi tanlangan guruhda allaqachon bor.")
        s.delete(row)
        s.add(GroupMember(group_id=to_group_id, student_id=student_id))
        who = st.full_name
        src_name, dst_name = src.name, dst.name
    from services import activity_service as _act

    _act.log("group", f"Guruh almashtirildi: {who}: {src_name} → {dst_name}", who)
    return dst_name
