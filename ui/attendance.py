"""Davomat bo'limi (desktop) — haftalik jadval."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import attendance_service, course_service, student_service
from ui import dialogs
from ui.theme import GREEN, RED
from ui.widgets import PageHeader, make_button, make_item, setup_table

logger = logging.getLogger(__name__)

WEEKDAYS = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]


class AttendancePage(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.week_offset = 0
        self.dates = []
        self.students: list[dict] = []
        self.matrix: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(
            PageHeader("Davomat", "Haftalik davomat jurnali"), 1
        )
        add_btn = make_button("➕  Yangi o'quvchi")
        add_btn.clicked.connect(self._quick_add)
        prev_btn = make_button("‹ Oldingi", "ghost")
        prev_btn.clicked.connect(lambda: self._shift_week(-1))
        today_btn = make_button("Bugun", "ghost")
        today_btn.clicked.connect(lambda: self._shift_week(0, reset=True))
        next_btn = make_button("Keyingi ›", "ghost")
        next_btn.clicked.connect(lambda: self._shift_week(1))
        header_row.addWidget(add_btn)
        header_row.addWidget(prev_btn)
        header_row.addWidget(today_btn)
        header_row.addWidget(next_btn)
        layout.addLayout(header_row)

        self.week_label = QLabel()
        self.week_label.setObjectName("cardSub")
        layout.addWidget(self.week_label)

        columns = ["F.I.Sh"] + [""] * 7 + ["Davomat %"]
        self.table = setup_table(columns, [260] + [96] * 7 + [120])
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table, 1)

        hint = QLabel("Katakchani bosing: — → ✓ (kelgan) → ✗ (kelmagan) → —")
        hint.setObjectName("hintText")
        layout.addWidget(hint)

        self.refresh()

    def _shift_week(self, delta: int, reset: bool = False) -> None:
        if reset:
            self.week_offset = 0
        else:
            self.week_offset = max(min(self.week_offset + delta, 52), -52)
        self.refresh()

    def refresh(self) -> None:
        self.dates = attendance_service.week_dates(self.week_offset)
        self.students, self.matrix, stats = attendance_service.get_matrix(self.dates)
        self.stats = stats
        self.week_label.setText(
            f"Hafta: {self.dates[0].strftime('%d.%m')} — {self.dates[-1].strftime('%d.%m.%Y')}"
        )
        self._populate_table()

    def _populate_table(self) -> None:
        from datetime import date as _date

        table = self.table
        table.setRowCount(0)
        today = _date.today()

        headers = ["F.I.Sh"]
        for d in self.dates:
            mark = " ●" if d == today else ""
            headers.append(f"{WEEKDAYS[d.weekday()]}{mark}\n{d.strftime('%d.%m')}")
        headers.append("Davomat %")
        table.setHorizontalHeaderLabels(headers)

        for st in self.students:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(st["full_name"]))
            for col, d in enumerate(self.dates, start=1):
                val = self.matrix[st["id"]][d.isoformat()]
                item = self._make_cell(st["id"], d.isoformat(), val)
                table.setItem(row, col, item)
            pct = self.stats[st["id"]]["pct"]
            pct_item = make_item(f"{pct}%", align_right=True)
            font = pct_item.font()
            font.setBold(True)
            pct_item.setFont(font)
            table.setItem(row, 8, pct_item)

        if not self.students:
            table.insertRow(0)
            item = make_item("O'quvchilar yo'q — «➕ Yangi o'quvchi» tugmasini bosing")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setSpan(0, 0, 1, 9)
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    def _make_cell(self, student_id: int, iso: str, val) -> QTableWidgetItem:
        if val is True:
            item = make_item("✓")
            item.setBackground(QColor("#189a52"))
            item.setForeground(QColor("#ffffff"))
        elif val is False:
            item = make_item("✗")
            item.setBackground(QColor("#e0324b"))
            item.setForeground(QColor("#ffffff"))
        else:
            item = make_item("—")
        font = item.font()
        font.setBold(True)
        font.setPointSize(17)
        item.setFont(font)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setData(Qt.ItemDataRole.UserRole, (student_id, iso, val))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col < 1 or col > 7:
            return
        table = self.table
        item = table.item(row, col)
        if not item:
            return
        student_id, iso, val = item.data(Qt.ItemDataRole.UserRole)
        # — → True → False → None
        nxt = True if val is None else (False if val is True else None)
        try:
            from datetime import datetime as _dt

            result = attendance_service.set_attendance(
                student_id, _dt.strptime(iso, "%Y-%m-%d").date(), nxt
            )
            new_item = self._make_cell(student_id, iso, nxt)
            table.setItem(row, col, new_item)
            pct_item = make_item(f"{result['pct']}%", align_right=True)
            font = pct_item.font()
            font.setBold(True)
            pct_item.setFont(font)
            table.setItem(row, 8, pct_item)
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _quick_add(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Yangi o'quvchi", "F.I.Sh kiriting:"
        )
        if not ok:
            return
        name = name.strip()
        err = None
        from utils import validators

        err = validators.validate_full_name(name)
        if err:
            dialogs.warning(self, err)
            return
        courses = course_service.all_courses()
        active = [c for c in courses if c["active"]]
        cid = active[0]["id"] if active else (courses[0]["id"] if courses else None)
        if cid is None:
            dialogs.warning(self, "Avval kurs yarating.")
            return
        try:
            student_service.create_student(name, "", cid, "unpaid", "")
            dialogs.info(self, "Yangi o'quvchi qo'shildi.")
            self.refresh()
            self.data_changed.emit()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)