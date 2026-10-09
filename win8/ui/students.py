"""O'quvchilar bo'limi."""

from __future__ import annotations

import logging

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services import course_service, monthly_payment_service, student_service
from ui import dialogs
from ui.widgets import (
    PageHeader,
    StatusBadge,
    make_button,
    make_item,
    make_search_input,
    setup_table,
)

logger = logging.getLogger(__name__)


class StudentsPage(QWidget):
    data_changed = Signal()

    COLUMNS = ["№", "F.I.Sh", "Telefon", "Kurs", "To'lov holati", "Qo'shilgan sana", "Amallar"]
    WIDTHS = [50, 250, 160, 170, 180, 110, 120]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.students: list[dict] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(
            PageHeader("O'quvchilar", "Barcha o'quvchilaringizni boshqaring")
        )

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        add_btn = make_button("➕  Yangi o'quvchi")
        add_btn.clicked.connect(self._add_student)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)
        self.month_combo = QComboBox()
        self.month_combo.addItem("Barcha oylar", 0)
        for month in (8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7):
            self.month_combo.addItem(
                monthly_payment_service.MONTH_FULL_NAMES[month - 1],
                month,
            )
        self.month_combo.setMinimumWidth(220)
        self.month_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.month_combo)
        self.search = make_search_input()
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search)
        layout.addLayout(toolbar)

        self.table = setup_table(self.COLUMNS, self.WIDTHS)
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        from datetime import date as _date

        search = self.search.text().strip()
        month = self.month_combo.currentData() or 0
        students = student_service.list_students(search=search)
        if month:
            paid_ids = set(
                monthly_payment_service.paid_student_ids(_date.today().year, month)
            )
            students = [st for st in students if st["id"] not in paid_ids]
        self.students = students
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        for idx, student in enumerate(self.students, start=1):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(str(idx)))
            table.setItem(row, 1, make_item(student["full_name"]))
            table.setItem(row, 2, make_item(student["phone"]))
            table.setItem(row, 3, make_item(student["course_name"]))
            badge = StatusBadge(student["payment_status"])
            table.setCellWidget(row, 4, badge)
            table.setItem(row, 5, make_item(student["created_display"]))
            self._attach_action_button(row, student)
        if not self.students:
            table.insertRow(0)
            item = make_item("Ma'lumot topilmadi")
            item.setTextAlignment(Qt.AlignCenter)
            table.setSpan(0, 0, 1, len(self.COLUMNS))
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    def _attach_action_button(self, row: int, student: dict) -> None:
        btn = QToolButton()
        btn.setObjectName("actionButton")
        btn.setText("Amallar ▾")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _=False, b=btn, s=student: self._open_action_menu(b, s))
        self.table.setCellWidget(row, 6, btn)

    def _open_action_menu(self, button: QToolButton, student: dict) -> None:
        menu = dialogs.build_student_menu(button, student["payment_status"])
        action = menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        if not action:
            return
        payload = action.data()
        if payload == "detail":
            dlg = dialogs.StudentDetailDialog(self, student["id"], on_change=self._after_change)
            dlg.exec()
        elif payload == "edit":
            self._edit_student(student)
        elif payload == "delete":
            self._delete_student(student)
        elif isinstance(payload, tuple) and payload[0] == "status":
            self._change_status(student, payload[1])

    def _add_student(self) -> None:
        if not course_service.all_courses():
            dialogs.warning(
                self,
                "Avval kurs yaratish kerak.\n«Kurslar» bo'limiga o'ting va yangi kurs qo'shing.",
            )
            return
        dlg = dialogs.StudentDialog(self)
        if dlg.exec():
            self._after_change()

    def _edit_student(self, student: dict) -> None:
        current = student_service.get_student(student["id"]) or student
        dlg = dialogs.StudentDialog(self, current)
        if dlg.exec():
            self._after_change()

    def _delete_student(self, student: dict) -> None:
        if not dialogs.confirm(
            self,
            "Ushbu o'quvchini o'chirishni xohlaysizmi?\nBu amalni qaytarib bo'lmaydi.",
            ok_text="O'chirish",
        ):
            return
        try:
            student_service.delete_student(student["id"])
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _change_status(self, student: dict, new_status: str) -> None:
        if new_status == student["payment_status"]:
            return
        try:
            student_service.set_payment_status(student["id"], new_status)
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _after_change(self) -> None:
        self.refresh()
        self.data_changed.emit()