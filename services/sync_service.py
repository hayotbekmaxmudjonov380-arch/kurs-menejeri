"""Sinxronizatsiya yordamchilari va merge-mantiq.

Asosiy qoida: **hech narsa o'chmaydi va hech narsa ustidan yozilmaydi**,
agar boshqa qurilma yangiroq bo'lmasa.

Kalit — `uid` (UUID), `id` emas:
- `id` ikki qurilmada bir xil bo'lmasligi mumkin (telefonda 1-sinf,
  kompyuterda 1-boshqa) — `id` bo'yicha merge ma'lumotni buzadi.
- `uid` global, shuning uchun har bir yozuv hamma joyda bir xil nomlanadi.

Merge qoidalari:
- Yangi yozuv (mahalliyda yo'q) — qo'shiladi.
- Mavjud yozuv: kelgan `updated_at` mahallikdan kechroq bo'lsa —
  yangilanadi, aks holda mahallik saqlanadi (local wins).
- O'chirilgan yozuv (tombstone) — mahallikda ham o'chadi va
  `tombstones` ga yoziladi, qayta "tirilmaydi".
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect as sa_inspect

from database.database import DATABASE
from database.models import new_uid

logger = logging.getLogger(__name__)

# (jadval nomi, model nomi, chet kalitlar {ustun: jadval})
# Tartib muhim: avval ota jadvallar (kurs/o'quvchi/guruh), keyin ularga
# bog'liq qatorlar — merge chet kalitni topa olishi uchun.
SYNC_TABLES: tuple[tuple[str, str, dict[str, str]], ...] = (
    ("courses", "Course", {}),
    ("students", "Student", {"course_id": "courses"}),
    ("groups", "Group", {}),
    (
        "group_members", "GroupMember",
        {"group_id": "groups", "student_id": "students"},
    ),
    ("payments", "Payment", {"student_id": "students"}),
    ("monthly_payments", "MonthlyPayment", {"student_id": "students"}),
    ("attendance", "Attendance", {"student_id": "students"}),
    ("test_results", "TestResult", {"student_id": "students"}),
    ("reminders", "Reminder", {}),
)

SYNC_TABLE_NAMES: tuple[str, ...] = tuple(t[0] for t in SYNC_TABLES)


def _models() -> dict[str, Any]:
    from database import models

    return {
        "courses": models.Course,
        "students": models.Student,
        "groups": models.Group,
        "group_members": models.GroupMember,
        "payments": models.Payment,
        "monthly_payments": models.MonthlyPayment,
        "attendance": models.Attendance,
        "test_results": models.TestResult,
        "reminders": models.Reminder,
    }


def fk_map() -> dict[str, dict[str, str]]:
    return {t[0]: t[2] for t in SYNC_TABLES}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def parse_iso(text: str | None) -> datetime | None:
    """ISO vaqtni datetime ga aylantiradi (xato bo'lsa None)."""
    if not text:
        return None
    raw = str(text).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw[:26], fmt)
                break
            except ValueError:
                continue
        else:
            return None
    # timezone'li va timezone'siz vaqtni solishtiriladigan qilish
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def to_json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


def _column_names(model: Any) -> list[str]:
    return [c.name for c in sa_inspect(model).columns]


def _fk_relationship(model: Any, fk_col: str) -> str | None:
    """FK ustuniga mos relationship nomini topadi (masalan course_id -> course).

    `getattr(obj, "course_id")` faqat int qaytaradi — uid uchun esa
    bog'lanish (relationship) orqali ota yozuv obyekti kerak.
    """
    for rel in sa_inspect(model).relationships:
        try:
            local_cols = {c.name for c in rel.local_remote_pairs[0][:1]}
        except (IndexError, AttributeError):
            continue
        if local_cols == {fk_col}:
            return rel.key
    return None


# ---------------------------------------------------------------- touch/tomb

def touch(obj: Any) -> None:
    """O'zgarish vaqtini belgilaydi (session ichida chaqiriladi)."""
    if hasattr(obj, "updated_at"):
        obj.updated_at = datetime.now()
    if hasattr(obj, "uid") and not getattr(obj, "uid", ""):
        obj.uid = new_uid()


def tomb(table_name: str, row_id: int | None, row_uid: str = "") -> None:
    """O'chirish qaydi (alohida sessionda, xatoda jim)."""
    if not row_id:
        return
    try:
        from database.models import Tombstone

        with DATABASE.session() as s:
            exists = (
                s.query(Tombstone)
                .filter(
                    Tombstone.table_name == table_name,
                    Tombstone.row_id == row_id,
                )
                .first()
            )
            if exists:
                exists.deleted_at = datetime.now()
                if row_uid:
                    exists.row_uid = row_uid
            else:
                s.add(Tombstone(
                    table_name=table_name,
                    row_id=row_id,
                    row_uid=row_uid or "",
                    deleted_at=datetime.now(),
                ))
    except Exception:
        logger.exception("Tombstone yozishda xatolik")


def tomb_rows(table_name: str, rows: list[Any]) -> None:
    """Kaskad o'chirilgan bolalar uchun tombstone (ota yozuv o'chirilganda).

    SQLite `ON DELETE CASCADE` bilan bolalar avtomatik o'chadi — lekin
    ularning tombstone'lari yozilmasa, telefon ularni qayta qo'shib yuboradi
    (yetim qator) va ma'lumot buziladi.
    """
    if not rows:
        return
    for row in rows:
        try:
            tomb(table_name, getattr(row, "id", None), getattr(row, "uid", "") or "")
        except Exception:  # noqa: BLE001
            logger.exception("Kaskad tombstone yozishda xatolik (%s)", table_name)


def collect_cascade(parent_rows: list[Any]) -> dict[str, list[Any]]:
    """Ota yozuvlar o'chirishdan oldin ularning bolalarini yig'adi."""
    if not parent_rows:
        return {}
    models = _models()
    with DATABASE.session() as s:
        ids = [getattr(r, "id", None) for r in parent_rows if getattr(r, "id", None)]
        if not ids:
            return {}
        return {
            "payments": s.query(models["payments"]).filter(
                models["payments"].student_id.in_(ids)).all(),
            "monthly_payments": s.query(models["monthly_payments"]).filter(
                models["monthly_payments"].student_id.in_(ids)).all(),
            "attendance": s.query(models["attendance"]).filter(
                models["attendance"].student_id.in_(ids)).all(),
            "test_results": s.query(models["test_results"]).filter(
                models["test_results"].student_id.in_(ids)).all(),
            "group_members": s.query(models["group_members"]).filter(
                models["group_members"].student_id.in_(ids)).all(),
        }


def tomb_list(since_iso: str | None = None) -> list[dict[str, Any]]:
    """Berilgan vaqtdan keyingi o'chirishlar ro'yxati."""
    from database.models import Tombstone

    since = parse_iso(since_iso)
    with DATABASE.session() as s:
        query = s.query(Tombstone)
        if since:
            query = query.filter(Tombstone.deleted_at > since)
        rows = query.order_by(Tombstone.deleted_at.asc()).all()
        return [
            {
                "table": r.table_name,
                "row_id": r.row_id,
                "uid": r.row_uid or "",
                "deleted_at": (
                    r.deleted_at.isoformat(timespec="microseconds")
                    if r.deleted_at else ""
                ),
            }
            for r in rows
        ]


# ------------------------------------------------------------------- row <-> dict

def row_to_wire(obj: Any, table_name: str) -> dict[str, Any]:
    """Model obyektini JSON-safe dict ga aylantiradi.

    Chet kalitlar (student_id, group_id, course_id) qoldirilmaydi —
    ular o'rniga `<fk>_uid` maydonlari qo'yiladi (mahalliy id emas,
    global uid — aks holda merge noto'g'ri yozuvni o'zgartiradi).
    """
    fks = fk_map().get(table_name, {})
    out: dict[str, Any] = {}
    for col in _column_names(type(obj)):
        if col == "id" or col in fks:
            continue
        out[col] = to_json_value(getattr(obj, col, None))
    return out


def wire_to_row(
    wire: dict[str, Any], table_name: str, session: Any
) -> dict[str, Any] | None:
    """Kelgan dict -> model uchun qiymatlar (chet kalitlar hal bo'lgan holda)."""
    if not isinstance(wire, dict):
        return None
    model = _models().get(table_name)
    if model is None:
        return None
    fks = fk_map().get(table_name, {})
    cols = set(_column_names(model))
    values: dict[str, Any] = {}
    for key, raw in wire.items():
        if key.endswith("_uid") or key == "id":
            continue
        if key not in cols:
            continue
        values[key] = _coerce(raw, model, key)

    # Majburiy (nullable=False) ustunlar to'ldirilmagan bo'lsa — yozuv
    # noto'g'ri, qo'shmaymiz (bazaga buzilgan qator kirib ketmasligi uchun).
    from sqlalchemy import inspect as _insp

    for c in _insp(model).columns:
        if c.primary_key or c.name in fks:
            continue  # id autoincrement, chet kalit quyida hal qilinadi
        if values.get(c.name) is not None:
            continue
        if c.nullable:
            continue
        if c.default is not None:
            values.pop(c.name, None)  # default ishlaydi
        else:
            return None  # majburiy maydon bo'sh — noto'g'ri qator
    for fk_col, parent_table in fks.items():
        ref = wire.get(f"{fk_col}_uid")
        if ref in (None, "", 0):
            # Chet kalit ixtiyoriy bo'lsa — null qoldiramiz
            if sa_inspect(model).columns[fk_col].nullable:
                values[fk_col] = None
                continue
            return None  # majburiy, lekin kelgan emas
        local_id = _lookup_id_by_ref(session, parent_table, ref)
        if local_id is None:
            return None  # ota yozuv hali kelmagan — keyin urinib ko'ramiz
        values[fk_col] = local_id
    return values


def _lookup_id_by_ref(session: Any, table: str, ref: Any) -> int | None:
    """`students:12` -> mahalliy id. uid bo'lsa uid bo'yicha qidiriladi."""
    if ref in (None, "", 0):
        return None
    model = _models().get(table)
    if model is None:
        return None
    raw = str(ref)
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    # Avval bu mahalliy id bo'lib ko'rinsin
    try:
        as_id = int(raw)
    except (TypeError, ValueError):
        as_id = None
    if as_id is not None:
        row = session.query(model).filter(model.id == as_id).first()
        if row:
            return row.id
    # Aks holda — bu boshqa qurilmaning uid'i
    if len(raw) == 32 and all(c in "0123456789abcdef" for c in raw.lower()):
        row = session.query(model).filter(model.uid == raw).first()
        if row:
            return row.id
    return None


def _coerce(raw: Any, model: Any, col: str) -> Any:
    """Kelgan qiymatni model ustun turiga moslaydi."""
    attr = sa_inspect(model).columns[col]
    py_type = attr.type.python_type
    if raw is None:
        return None
    try:
        if py_type is bool:
            if isinstance(raw, str):
                return raw.strip().lower() in ("1", "true", "yes", "ha")
            return bool(raw)
        if py_type is int:
            return int(raw)
        if py_type is float:
            return float(raw)
        if py_type is datetime:
            return parse_iso(raw) or datetime.now()
        if py_type is date:
            parsed = parse_iso(raw)
            return parsed.date() if parsed else None
        if py_type is str:
            return str(raw)
    except (TypeError, ValueError):
        return None
    return raw


# ------------------------------------------------------------------- collect

def collect_changes(since_iso: str | None = None) -> list[dict[str, Any]]:
    """Berilgan vaqtdan keyingi barcha o'zgarishlar (telefonga yuborish uchun)."""
    since = parse_iso(since_iso)
    models = _models()
    changes: list[dict[str, Any]] = []
    with DATABASE.session() as s:
        for table_name, _model_name, _fks in SYNC_TABLES:
            model = models[table_name]
            query = s.query(model)
            if since:
                query = query.filter(model.updated_at > since)
            for obj in query.order_by(model.updated_at.asc()).all():
                wire = row_to_wire(obj, table_name)
                # Chet kalitlarni uid bilan yuborish (mahalliy id emas!)
                model_cls = models[table_name]
                for fk_col, _parent_table in fk_map()[table_name].items():
                    rel_key = _fk_relationship(model_cls, fk_col)
                    ref_obj = getattr(obj, rel_key, None) if rel_key else None
                    if ref_obj is None:
                        wire[f"{fk_col}_uid"] = ""
                    else:
                        wire[f"{fk_col}_uid"] = getattr(ref_obj, "uid", "") or ""
                changes.append({
                    "table": table_name,
                    "uid": wire.get("uid", ""),
                    "updated_at": wire.get("updated_at", ""),
                    "deleted": False,
                    "row": wire,
                })
    return changes


def last_change_at() -> str:
    """Eng so'nggi o'zgarish vaqti (telefon o'z nuqtasini shundan oladi)."""
    models = _models()
    newest: datetime | None = None
    with DATABASE.session() as s:
        for table_name in SYNC_TABLE_NAMES:
            model = models[table_name]
            row = (
                s.query(model)
                .filter(model.updated_at.isnot(None))
                .order_by(model.updated_at.desc())
                .first()
            )
            if row and row.updated_at and (newest is None or row.updated_at > newest):
                newest = row.updated_at
    return newest.isoformat(timespec="microseconds") if newest else ""


def last_sync_at() -> str:
    return DATABASE.get_setting("last_sync_at", "")


# --------------------------------------------------------------------- apply

def apply_changes(
    changes: list[dict[str, Any]], deleted: list[dict[str, Any]] | None = None
) -> dict[str, int]:
    """Telefondan kelgan o'zgarishlarni qo'llaydi (merge).

    Qaytaradi: {"applied": n, "skipped": n, "deleted": n, "conflicts": n}
    """
    models = _models()
    result = {"applied": 0, "skipped": 0, "deleted": 0, "conflicts": 0}
    if not changes and not deleted:
        return result

    # Avval o'chirishlar (ular yozuvlarni bo'shatadi)
    for item in deleted or []:
        if _apply_delete(item, models, result):
            pass

    # Chet kalitli qatorlar ota yozuv kelgandan keyin — bir necha marta urinib ko'ramiz
    pending = list(changes or [])
    for _attempt in range(3):
        if not pending:
            break
        still: list[dict[str, Any]] = []
        for item in pending:
            if not _apply_one(item, models, result):
                still.append(item)
        pending = still

    # Hali ham chiqmagan qatorlar — keyingi sinxronga qoldiramiz (yo'qotilmaydi)
    if pending:
        logger.info("apply_changes: %d qator kutmoqda (ota yozuv topilmadi)", len(pending))
    return result


def _is_tombstoned(table_name: str, row_uid: str) -> bool:
    """Bu uid oldin o'chirilganmi? (qayta tirilmasligi uchun)"""
    if not row_uid:
        return False
    try:
        from database.models import Tombstone

        with DATABASE.session() as s:
            return (
                s.query(Tombstone)
                .filter(
                    Tombstone.table_name == table_name,
                    Tombstone.row_uid == row_uid,
                )
                .first()
                is not None
            )
    except Exception:  # noqa: BLE001
        return False


def _apply_one(
    item: dict[str, Any], models: dict[str, Any], result: dict[str, int]
) -> bool:
    table_name = str(item.get("table") or "")
    wire = item.get("row") if isinstance(item.get("row"), dict) else None
    if wire is None:
        return True  # bo'sh yoki noto'g'ri — jim o'tkazamiz (xato emas)
    model = models.get(table_name)
    if model is None:
        logger.warning("Noma'lum jadval: %s", table_name)
        return True

    incoming_uid = str(wire.get("uid") or item.get("uid") or "")
    incoming_at = parse_iso(wire.get("updated_at") or item.get("updated_at"))

    # Bu yozuv oldin O'CHIRILGAN bo'lsa — qayta tirilmaydi.
    # (uid noyob: qayta qo'shsa ham yangi uid beriladi, shuning uchun
    # shu uid uchun tombstone = abadiy o'chirish)
    if incoming_uid and _is_tombstoned(table_name, incoming_uid):
        result["skipped"] += 1
        return True

    with DATABASE.session() as s:
        local = None
        if incoming_uid:
            local = s.query(model).filter(model.uid == incoming_uid).first()
        if local is None and table_name in ("courses", "groups"):
            # Nomi bir xil kurs/guruh allaqachon bo'lsa - dublikat
            # yaratmaymiz, mavjud qatorni yangilaymiz (uid saqlanadi).
            nm = str(wire.get("name") or "").strip()
            if nm:
                local = s.query(model).filter(model.name == nm).first()
        if local is None:
            values = wire_to_row(wire, table_name, s)
            if values is None:
                return False  # ota yozuv hali yo'q
            values.pop("updated_at", None)
            values.pop("uid", None)
            obj = model(**values)
            if incoming_uid:
                obj.uid = incoming_uid
            if incoming_at:
                obj.updated_at = incoming_at
            else:
                touch(obj)
            s.add(obj)
            result["applied"] += 1
            return True

        # Mavjud yozuv — updated_at kechroq bo'lgani yutadi
        local_at = parse_iso(
            local.updated_at.isoformat() if local.updated_at else None
        )
        if incoming_at and local_at and incoming_at <= local_at:
            result["skipped"] += 1
            return True
        if incoming_at and local_at and incoming_at > local_at:
            result["conflicts"] += 1
        values = wire_to_row(wire, table_name, s)
        if values is None:
            return False
        for key, value in values.items():
            if key in ("uid", "updated_at"):
                continue
            setattr(local, key, value)
        local.updated_at = incoming_at or datetime.now()
        result["applied"] += 1
        return True


def _apply_delete(
    item: dict[str, Any], models: dict[str, Any], result: dict[str, int]
) -> bool:
    table_name = str(item.get("table") or "")
    model = models.get(table_name)
    if model is None:
        return False
    row_uid = str(item.get("uid") or item.get("row_uid") or "")
    deleted_at = parse_iso(item.get("deleted_at")) or datetime.now()
    with DATABASE.session() as s:
        local = None
        if row_uid:
            local = s.query(model).filter(model.uid == row_uid).first()
        if local is None:
            return False
        # Mahalliy updated_at yangiroq bo'lsa — o'chirishni qabul qilmaymiz
        # (mahalliy o'zgarish qimmatroq, hech narsa o'chmaydi)
        local_at = parse_iso(local.updated_at.isoformat() if local.updated_at else None)
        if local_at and local_at > deleted_at:
            return False
        row_id, keep_uid = local.id, (local.uid or "")
        s.delete(local)
    # O'chirish qaydi mahalliy bazada ham saqlanadi
    tomb(table_name, row_id, keep_uid)
    result["deleted"] += 1
    return True
