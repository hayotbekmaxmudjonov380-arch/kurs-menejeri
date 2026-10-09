"""Database backup/restore servisi."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from database.database import DATABASE

logger = logging.getLogger(__name__)


def create_backup(destination: str | Path) -> Path:
    """Database faylining nusxasini yaratadi. Fayl yo'lini qaytaradi."""
    if not DATABASE.path.exists():
        raise FileNotFoundError("Database fayli topilmadi.")
    dest = Path(destination)
    if dest.is_dir():
        default_name = f"kurs_manager_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        dest = dest / default_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DATABASE.path, dest)
    logger.info("Backup yaratildi: %s", dest)
    return dest


def restore_backup(backup_path: str | Path) -> Path:
    """Tanlangan backup faylidan database'ni tiklaydi va fayl yo'lini qaytaradi."""
    src = Path(backup_path)
    if not src.exists():
        raise FileNotFoundError("Backup fayli topilmadi.")

    # Nusxani avval yaxlit tekshirish uchun vaqtinchalik faylga ko'chiramiz
    import sqlite3

    tmp = DATABASE.path.parent / "restore_check.db"
    shutil.copy2(src, tmp)
    connection = sqlite3.connect(tmp)
    try:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='students'"
        ).fetchone()
        if not row:
            raise ValueError("Tanlangan fayl to'g'ri Kurs Manager backup fayli emas.")
    finally:
        connection.close()

    shutil.copy2(tmp, DATABASE.path)
    tmp.unlink(missing_ok=True)
    DATABASE.recreate()
    logger.info("Database tiklandi: %s", src)
    return DATABASE.path


def reset_demo_data() -> None:
    """Barcha jadvallarni tozalab, demo ma'lumotlarni qayta yuklaydi."""
    from services import demo_data

    DATABASE.recreate()
    demo_data.seed()