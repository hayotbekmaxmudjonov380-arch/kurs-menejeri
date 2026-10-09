"""Guruhlar bo'limi (desktop)."""

from __future__ import annotations

import logging

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services import group_service
from ui import dialogs
from ui.widgets import (
    PageHeader,
    make_button,
    make_item,
    setup_table,
)

logger = logging.getLogger(__name__)


class GroupsPage(QWidget):
    data_changed = Signal()

    COLUMNS = ["Guruh nomi", "O'quvchilar soni", "Yaratilgan sana", "Amallar"]
    WIDTHS = [320, 180, 160, 140]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.groups: list[dict] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(
            PageHeader("Guruhlar", "O'quvchilarni xohlagancha guruhlarga bo'ling")
        )

        toolbar = QHBoxLayout()
        add_btn = make_button("➕  Yangi guruh")
        add_btn.clicked.connect(self._add_group)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.table = setup_table(self.COLUMNS, self.WIDTHS)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        self.groups = group_service.list_groups()
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        for group in self.groups:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(f"👥  {group['name']}"))
            table.setItem(row, 1, make_item(str(group["member_count"]), align_right=True))
            table.setItem(row, 2, make_item(group["created_display"]))
            self._attach_action_button(row, group)
        if not self.groups:
            table.insertRow(0)
            item = make_item("Guruhlar yo'q. «➕ Yangi guruh» tugmasini bosing.")
            item.setTextAlignment(Qt.AlignCenter)
            table.setSpan(0, 0, 1, len(self.COLUMNS))
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    def _attach_action_button(self, row: int, group: dict) -> None:
        btn = QToolButton()
        btn.setObjectName("actionButton")
        btn.setText("Amallar ▾")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _=False, b=btn, g=group: self._open_action_menu(b, g))
        self.table.setCellWidget(row, 3, btn)

    def _open_action_menu(self, button, group: dict) -> None:
        from PySide2.QtWidgets import QAction
        from PySide2.QtWidgets import QMenu

        menu = QMenu(button)
        members_action = QAction("👥 A'zolar", menu)
        members_action.setData("members")
        edit_action = QAction("✏️ Nomini tahrirlash", menu)
        edit_action.setData("edit")
        delete_action = QAction("🗑 Guruhni o'chirish", menu)
        delete_action.setData("delete")
        menu.addAction(members_action)
        menu.addAction(edit_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        action = menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        if not action:
            return
        if action.data() == "members":
            self._show_members(group)
        elif action.data() == "edit":
            self._edit_group(group)
        elif action.data() == "delete":
            self._delete_group(group)

    def _on_double_click(self, row: int, _col: int) -> None:
        if row < len(self.groups):
            self._show_members(self.groups[row])

    def _add_group(self) -> None:
        dlg = dialogs.GroupDialog(self)
        if dlg.exec():
            self._after_change()

    def _edit_group(self, group: dict) -> None:
        current = group_service.get_group(group["id"])
        if not current:
            return
        dlg = dialogs.GroupDialog(self, current)
        if dlg.exec():
            self._after_change()

    def _show_members(self, group: dict) -> None:
        dlg = dialogs.GroupDetailDialog(self, group["id"], on_change=self._after_change)
        dlg.exec()

    def _delete_group(self, group: dict) -> None:
        if not dialogs.confirm(
            self,
            f"«{group['name']}» guruhini o'chirishni xohlaysizmi?\n"
            f"O'quvchilar o'chmaydi (guruhda {group['member_count']} ta a'zo bor).",
            ok_text="O'chirish",
        ):
            return
        try:
            group_service.delete_group(group["id"])
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _after_change(self) -> None:
        self.refresh()
        self.data_changed.emit()
