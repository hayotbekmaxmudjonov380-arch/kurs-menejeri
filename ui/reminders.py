"""Eslatmalar bo'limi (desktop)."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services import reminder_service
from ui import dialogs
from ui.theme import GREEN, RED, YELLOW
from ui.widgets import (
    PageHeader,
    make_button,
    make_item,
    setup_table,
)

logger = logging.getLogger(__name__)


class RemindersPage(QWidget):
    data_changed = Signal()

    COLUMNS = ["Sana va vaqt", "Sarlavha", "Izoh", "Holat", "Amallar"]
    WIDTHS = [160, 260, 320, 160, 130]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.reminders: list[dict] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(
            PageHeader("Eslatmalar", "Rejalashtirilgan ishlar — vaqti kelganda ekranda habar chiqadi")
        )

        toolbar = QHBoxLayout()
        add_btn = make_button("➕  Yangi eslatma")
        add_btn.clicked.connect(self._add_reminder)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)
        hint = QLabel("⏰ Vaqt kelganda avtomatik habar chiqadi")
        hint.setObjectName("hintText")
        toolbar.addWidget(hint)
        layout.addLayout(toolbar)

        self.table = setup_table(self.COLUMNS, self.WIDTHS)
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        self.reminders = reminder_service.list_reminders()
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        for rem in self.reminders:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(f"📅 {rem['datetime_display']}"))
            table.setItem(row, 1, make_item(rem["title"]))
            table.setItem(row, 2, make_item(rem["note"] or "—"))
            table.setCellWidget(row, 3, self._make_status_badge(rem))
            self._attach_action_button(row, rem)
        if not self.reminders:
            table.insertRow(0)
            item = make_item("Eslatmalar yo'q")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setSpan(0, 0, 1, len(self.COLUMNS))
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    def _make_status_badge(self, rem: dict) -> QLabel:
        color = {"green": GREEN, "red": RED, "amber": YELLOW}.get(rem["status_color"], YELLOW)
        emoji = {"green": "✅", "red": "❗", "amber": "🕐"}.get(rem["status_color"], "🕐")
        label = QLabel(f"{emoji} {rem['status']}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"background-color: {color}22; color: {color};"
            f"border: 1px solid {color}55; border-radius: 12px;"
            f"padding: 4px 12px; font-size: 11px; font-weight: 700;"
        )
        return label

    def _attach_action_button(self, row: int, rem: dict) -> None:
        btn = QToolButton()
        btn.setObjectName("actionButton")
        btn.setText("Amallar ▾")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False, b=btn, r=rem: self._open_action_menu(b, r))
        self.table.setCellWidget(row, 4, btn)

    def _open_action_menu(self, button, rem: dict) -> None:
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        menu = QMenu(button)
        toggle_action = QAction(
            "↩️ Bajarilmagan deb belgilash" if rem["is_done"] else "✅ Bajarildi deb belgilash",
            menu,
        )
        toggle_action.setData("toggle")
        edit_action = QAction("✏️ Tahrirlash", menu)
        edit_action.setData("edit")
        delete_action = QAction("🗑 O'chirish", menu)
        delete_action.setData("delete")
        menu.addAction(toggle_action)
        menu.addAction(edit_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        action = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        if not action:
            return
        if action.data() == "toggle":
            self._toggle_reminder(rem)
        elif action.data() == "edit":
            self._edit_reminder(rem)
        elif action.data() == "delete":
            self._delete_reminder(rem)

    def _add_reminder(self) -> None:
        dlg = dialogs.ReminderDialog(self)
        if dlg.exec():
            self._after_change()

    def _edit_reminder(self, rem: dict) -> None:
        current = reminder_service.get_reminder(rem["id"])
        if not current:
            return
        dlg = dialogs.ReminderDialog(self, current)
        if dlg.exec():
            self._after_change()

    def _toggle_reminder(self, rem: dict) -> None:
        try:
            reminder_service.set_done(rem["id"], not rem["is_done"])
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _delete_reminder(self, rem: dict) -> None:
        if not dialogs.confirm(
            self,
            "Ushbu eslatmani o'chirishni xohlaysizmi?",
            ok_text="O'chirish",
        ):
            return
        try:
            reminder_service.delete_reminder(rem["id"])
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _after_change(self) -> None:
        self.refresh()
        self.data_changed.emit()