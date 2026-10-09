"""Database engine va session boshqaruvi.

Database fayli dastur bilan bir joyda (yoki o'qib bo'lmaydigan joyda bo'lsa
%LOCALAPPDATA%/KursManager) saqlanadi.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    """Dastur ma'lumot fayllari joylashgan papkani qaytaradi."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        try:
            probe = exe_dir / ".write_probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            return exe_dir
        except OSError:
            base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
            fallback = base / "KursManager"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
    return Path(__file__).resolve().parent.parent


DATA_DIR: Path = get_data_dir()
DB_PATH: Path = DATA_DIR / "kurs_manager.db"
LOG_PATH: Path = DATA_DIR / "kurs_manager.log"


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:  # pragma: no cover
        pass


class Database:
    """SQLite bazasi bilan ishlash uchun yagona interfeys."""

    def __init__(self, path: str | Path | None = None):
        self.path: Path = Path(path) if path else DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_engine()

    def _create_engine(self):
        self.engine: Engine = create_engine(
            f"sqlite:///{self.path}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        self.session_factory: sessionmaker = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    def init(self) -> None:
        Base.metadata.create_all(self.engine)
        self._migrate()

    def _migrate(self) -> None:
        """Eski database fayllariga yetishmayotgan ustunlarni qo'shadi."""
        import sqlite3

        try:
            conn = sqlite3.connect(self.path)
            try:
                cols = [
                    r[1]
                    for r in conn.execute("PRAGMA table_info(students)").fetchall()
                ]
                if "fee" not in cols:
                    conn.execute(
                        "ALTER TABLE students ADD COLUMN fee FLOAT DEFAULT 0"
                    )
                    conn.commit()
                    logger.info("Migration: students.fee ustuni qo'shildi")
                if "total_price" not in cols:
                    conn.execute(
                        "ALTER TABLE students ADD COLUMN total_price FLOAT DEFAULT 0"
                    )
                    conn.commit()
                    logger.info("Migration: students.total_price ustuni qo'shildi")
                if "paid_amount" not in cols:
                    conn.execute(
                        "ALTER TABLE students ADD COLUMN paid_amount FLOAT DEFAULT 0"
                    )
                    conn.commit()
                    logger.info("Migration: students.paid_amount ustuni qo'shildi")
                if "grade" not in cols:
                    conn.execute(
                        "ALTER TABLE students ADD COLUMN grade VARCHAR(20) DEFAULT ''"
                    )
                    conn.commit()
                    logger.info("Migration: students.grade ustuni qo'shildi")
                # Eski yozuvlarda umumiy narx bo'sh bo'lsa — kelishilgan summadan olish
                backfilled = conn.execute(
                    "UPDATE students SET total_price = fee "
                    "WHERE total_price = 0 AND fee > 0"
                ).rowcount
                if backfilled:
                    conn.commit()
                    logger.info("Migration: %d ta total_price backfill", backfilled)
                # "Kutilmoqda" holati olib tashlandi -> "To'lov qilinmagan" ga o'tkazish
                moved = conn.execute(
                    "UPDATE students SET payment_status='unpaid' "
                    "WHERE payment_status='pending'"
                ).rowcount
                if moved:
                    conn.commit()
                    logger.info("Migration: %d ta pending -> unpaid", moved)
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                if "payments" in tables:
                    moved_pay = conn.execute(
                        "UPDATE payments SET status='unpaid' "
                        "WHERE status='pending'"
                    ).rowcount
                    if moved_pay:
                        conn.commit()
                        logger.info("Migration: payments %d ta pending -> unpaid", moved_pay)
                if "monthly_payments" in tables:
                    mp_cols = [
                        r[1] for r in conn.execute(
                            "PRAGMA table_info(monthly_payments)"
                        ).fetchall()
                    ]
                    if "amount" not in mp_cols:
                        conn.execute(
                            "ALTER TABLE monthly_payments ADD COLUMN amount FLOAT DEFAULT 0"
                        )
                        conn.commit()
                        logger.info("Migration: monthly_payments.amount ustuni qo'shildi")
            finally:
                conn.close()
        except Exception:
            logger.exception("Migration failed")

    def dispose(self) -> None:
        self.engine.dispose()

    def recreate(self) -> None:
        """Engine'ni qayta yaratish — backup restore'dan keyin ishlatiladi."""
        self.dispose()
        self._create_engine()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Database transaction failed")
            raise
        finally:
            session.close()

    def get_setting(self, key: str, default: str = "") -> str:
        from database.models import Setting

        with self.session() as s:
            row = s.query(Setting).filter(Setting.key == key).first()
            return row.value if row else default

    def set_setting(self, key: str, value: str) -> None:
        from database.models import Setting

        with self.session() as s:
            row = s.query(Setting).filter(Setting.key == key).first()
            if row:
                row.value = value
            else:
                s.add(Setting(key=key, value=value))


# Yagona global database obyekti
DATABASE = Database()


def init_database() -> None:
    DATABASE.init()