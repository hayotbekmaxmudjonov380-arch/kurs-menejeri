"""Test natijalari bo'limi (desktop)."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services import student_service, test_service
from ui import dialogs
from ui.theme import GREEN, RED, YELLOW
from ui.widgets import (
    PageHeader,
    StatusBadge,
    make_button,
    make_item,
    make_search_input,
    setup_table,
)

logger = logging.getLogger(__name__)

GRADE_COLORS = {
    "green": GREEN,
    "blue": "#2b7fff",
    "amber": YELLOW,
    "red": RED,
}


class TestsPage(QWidget):
    data_changed = Signal()

    COLUMNS = ["Sana", "F.I.Sh", "Test mavzusi", "Savollar", "To'g'ri", "Foiz", "Baho", "Amallar"]
    WIDTHS = [100, 220, 220, 80, 80, 150, 150, 110]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.results: list[dict] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(
            PageHeader("Test natijalari", "O'quvchilarning test natijalari va foiz ko'rsatkichlari")
        )

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        add_btn = make_button("➕  Yangi natija")
        add_btn.clicked.connect(self._add_result)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)
        self.search = make_search_input("F.I.Sh yoki mavzuni qidiring...")
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search)
        layout.addLayout(toolbar)

        self.table = setup_table(self.COLUMNS, self.WIDTHS)
        layout.addWidget(self.table, 1)

        hint = QLabel("A'lo ≥85%  •  Yaxshi ≥70%  •  Qoniqarli ≥55%  •  Qoniqarsiz <55%")
        hint.setObjectName("hintText")
        layout.addWidget(hint)

        self.refresh()

    def refresh(self) -> None:
        search = self.search.text().strip()
        self.results = test_service.list_results(search=search)
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        for res in self.results:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(res["date_display"]))
            table.setItem(row, 1, make_item(res["full_name"]))
            table.setItem(row, 2, make_item(res["topic"]))
            table.setItem(row, 3, make_item(str(res["total_questions"]), align_right=True))
            table.setItem(row, 4, make_item(str(res["correct_answers"]), align_right=True))
            table.setCellWidget(row, 5, self._make_progress(res["percentage"]))
            table.setCellWidget(row, 6, self._make_grade_badge(res))
            self._attach_action_button(row, res)
        if not self.results:
            table.insertRow(0)
            item = make_item("Natijalar topilmadi")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setSpan(0, 0, 1, len(self.COLUMNS))
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    def _make_progress(self, pct: float) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)
        label = QLabel(f"{pct}%")
        label.setStyleSheet("font-weight: 800; font-size: 12px;")
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(pct))
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        lay.addWidget(label)
        lay.addWidget(bar, 1)
        return box

    def _make_grade_badge(self, res: dict) -> QLabel:
        color = GRADE_COLORS.get(res["grade_color"], GREEN)
        label = QLabel(f"🏅 {res['grade']}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"background-color: {color}22; color: {color};"
            f"border: 1px solid {color}55; border-radius: 12px;"
            f"padding: 4px 12px; font-size: 11px; font-weight: 700;"
        )
        return label

    def _attach_action_button(self, row: int, res: dict) -> None:
        btn = QToolButton()
        btn.setObjectName("actionButton")
        btn.setText("Amallar ▾")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False, b=btn, r=res: self._open_action_menu(b, r))
        self.table.setCellWidget(row, 7, btn)

    def _open_action_menu(self, button, res: dict) -> None:
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        menu = QMenu(button)
        edit_action = QAction("✏️ Tahrirlash", menu)
        edit_action.setData("edit")
        delete_action = QAction("🗑 O'chirish", menu)
        delete_action.setData("delete")
        menu.addAction(edit_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        action = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        if not action:
            return
        if action.data() == "edit":
            self._edit_result(res)
        elif action.data() == "delete":
            self._delete_result(res)

    def _add_result(self) -> None:
        if student_service.get_stats()["total"] == 0:
            dialogs.warning(self, "O'quvchilar ro'yxati bo'sh.\nAvval o'quvchi qo'shing.")
            return
        dlg = dialogs.TestDialog(self)
        if dlg.exec():
            self._after_change()

    def _edit_result(self, res: dict) -> None:
        current = test_service.get_result(res["id"])
        if not current:
            return
        dlg = dialogs.TestDialog(self, current)
        if dlg.exec():
            self._after_change()

    def _delete_result(self, res: dict) -> None:
        if not dialogs.confirm(
            self,
            "Ushbu natijani o'chirishni xohlaysizmi?",
            ok_text="O'chirish",
        ):
            return
        try:
            test_service.delete_result(res["id"])
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _after_change(self) -> None:
        self.refresh()
        self.data_changed.emit()