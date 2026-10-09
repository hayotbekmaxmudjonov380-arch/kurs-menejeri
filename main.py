"""Kurs Manager — ishga tushirish nuqtasi.

Ishga tushirish:
    python main.py

Test rejimi (avtomatik yopiladi):
    python main.py --smoke
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Loyiha ildizini sys.path ga qo'shish (fayl boshqa joydan ishga tushsa ham)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _setup_exception_hook(app) -> None:
    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("root").critical(
            "Kutilmagan xatolik", exc_info=(exc_type, exc_value, exc_tb)
        )
        try:
            from PySide6.QtWidgets import QMessageBox

            message = str(exc_value) or exc_type.__name__
            QMessageBox.critical(
                None,
                "Kutilmagan xatolik",
                "Dasturda xatolik yuz berdi.\n\n"
                f"{message}\n\n"
                "Batafsil ma'lumot log faylida saqlangan.",
            )
        except Exception:  # noqa: BLE001, pragma: no cover
            pass
        # Dastur ishlashda davom etishi uchun app exit qilmaymiz

    sys.excepthook = handle_exception


def main() -> int:
    from utils.logging_config import setup_logging

    setup_logging()
    logger = logging.getLogger("main")

    parser = argparse.ArgumentParser(description="Kurs Manager")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke test: oyna ochilib, avtomatik yopiladi",
    )
    args = parser.parse_args()

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from database.database import DATABASE, init_database
    from database.models import Student
    from services import demo_data
    from ui.main_window import MainWindow
    from ui import theme
    from utils.branding import make_app_icon

    # Database'ni yaratish (exe toza ochiladi: faqat kurslar, o'quvchisiz)
    init_database()
    demo_data.ensure_courses()
    logger.info("Database tayyor: ok")

    # Saqlangan mavzuni yuklash
    try:
        saved = DATABASE.get_setting("theme", "dark")
        theme.set_theme(saved if saved in theme.THEMES else "dark")
    except Exception:  # noqa: BLE001
        logger.exception("Mavzuni yuklashda xatolik")

    app = QApplication(sys.argv)
    app.setApplicationName("Kurs Manager")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(theme.get_qss())
    app.setWindowIcon(make_app_icon())

    window = MainWindow()
    window.show()

    _setup_exception_hook(app)

    if args.smoke:
        from PySide6.QtCore import QTimer

        logger.info("Smoke test rejimi — oyna 3 soniyadan keyin yopiladi")
        QTimer.singleShot(3000, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())