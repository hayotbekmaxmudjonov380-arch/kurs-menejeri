"""Sozlamalar bo'limi (backup/restore va boshqalar)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from database.database import DB_PATH
from services import backup_service
from ui import dialogs
from ui.theme import PRIMARY, RED
from ui.widgets import Card, PageHeader, make_button

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    def __init__(self, parent=None, on_data_reset=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.on_data_reset = on_data_reset or (lambda: None)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addWidget(PageHeader("Sozlamalar", "Ma'lumotlar imkoniyatlari va dastur sozlamalari"))

        # ---- Database haqida ----
        db_card = Card()
        db_lay = QVBoxLayout(db_card)
        db_lay.setContentsMargins(18, 14, 18, 14)
        db_lay.setSpacing(8)
        db_title = QLabel("💾  Ma'lumotlar bazasi")
        db_title.setObjectName("cardTitle")
        db_lay.addWidget(db_title)

        self.db_path_label = QLabel()
        self.db_path_label.setWordWrap(True)
        self.db_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        db_lay.addWidget(self.db_path_label)

        self.db_size_label = QLabel()
        self.db_size_label.setObjectName("cardSub")
        db_lay.addWidget(self.db_size_label)
        layout.addWidget(db_card)

        # ---- Backup ----
        backup_card = Card()
        bk_lay = QVBoxLayout(backup_card)
        bk_lay.setContentsMargins(18, 14, 18, 14)
        bk_lay.setSpacing(10)
        bk_title = QLabel("🛡  Database backup")
        bk_title.setObjectName("cardTitle")
        bk_lay.addWidget(bk_title)
        bk_desc = QLabel("Tanlangan papkaga bazaning nusxasini saqlang yoki avvalgi nusxadan qayta tiking.")
        bk_desc.setObjectName("cardSub")
        bk_desc.setWordWrap(True)
        bk_lay.addWidget(bk_desc)
        bk_row = QHBoxLayout()
        backup_btn = make_button("Backup yaratish")
        backup_btn.clicked.connect(self._create_backup)
        restore_btn = make_button("Backup'dan tiklash", "ghost")
        restore_btn.clicked.connect(self._restore_backup)
        bk_row.addWidget(backup_btn)
        bk_row.addWidget(restore_btn)
        bk_row.addStretch(1)
        bk_lay.addLayout(bk_row)
        layout.addWidget(backup_card)

        # ---- Xavfli joy ----
        danger_card = Card()
        dg_lay = QVBoxLayout(danger_card)
        dg_lay.setContentsMargins(18, 14, 18, 14)
        dg_lay.setSpacing(10)
        dg_title = QLabel("⚠️  Xavfli amallar")
        dg_title.setObjectName("cardTitle")
        dg_lay.addWidget(dg_title)
        dg_desc = QLabel("Barcha ma'lumotlar o'chirilib, demo ma'lumotlar qayta yuklanadi.")
        dg_desc.setObjectName("cardSub")
        dg_lay.addWidget(dg_desc)
        reset_btn = make_button("Demo ma'lumotlarni qayta yuklash", "danger")
        reset_btn.clicked.connect(self._reset_demo)
        dg_lay.addWidget(reset_btn)
        layout.addWidget(danger_card)

        layout.addStretch(1)

        version = QLabel("Kurs Manager  v1.0.0")
        version.setObjectName("hintText")
        layout.addWidget(version)

        self._refresh_db_info()

    def _refresh_db_info(self) -> None:
        self.db_path_label.setText(f"Lokatsiya:  {DB_PATH}")
        if DB_PATH.exists():
            size = DB_PATH.stat().st_size
            if size < 1024:
                size_text = f"{size} bayt"
            elif size < 1024 * 1024:
                size_text = f"{size / 1024:.1f} KB"
            else:
                size_text = f"{size / (1024 * 1024):.2f} MB"
            self.db_size_label.setText(f"Fayl hajmi: {size_text}")
        else:
            self.db_size_label.setText("Fayl hali yaratilmagan")

    def refresh(self) -> None:
        self._refresh_db_info()

    def _create_backup(self) -> None:
        default_dir = str(Path.home() / "Documents")
        default_name = f"kurs_manager_backup.db"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup faylini saqlash",
            str(Path(default_dir) / default_name),
            "SQLite database (*.db)",
        )
        if not path:
            return
        try:
            saved = backup_service.create_backup(path)
            dialogs.info(self, f"Backup yaratildi:\n{saved}")
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _restore_backup(self) -> None:
        if not dialogs.confirm(
            self,
            "Backup'dan tiklash barcha joriy ma'lumotlarni o'zgartirib qo'yadi.\nDavom etasizmi?",
            ok_text="Tiklash",
        ):
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Backup faylini tanlang",
            str(Path.home() / "Documents"),
            "SQLite database (*.db);;Barcha fayllar (*)",
        )
        if not path:
            return
        try:
            backup_service.restore_backup(path)
            dialogs.info(self, "Database muvaffaqiyatli tiklandi.")
            self.on_data_reset()
            self._refresh_db_info()
        except ValueError as exc:
            dialogs.warning(self, str(exc))
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _reset_demo(self) -> None:
        if not dialogs.confirm(
            self,
            "Barcha ma'lumotlar o'chirilib, demo ma'lumotlar qayta yuklanadi.\nDavom etasizmi?",
            ok_text="Qayta yuklash",
        ):
            return
        try:
            backup_service.reset_demo_data()
            dialogs.info(self, "Demo ma'lumotlar qayta yuklandi.")
            self.on_data_reset()
            self._refresh_db_info()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)