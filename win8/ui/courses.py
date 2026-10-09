"""Kurslar bo'limi."""

from __future__ import annotations

import logging

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from services import course_service
from ui import dialogs
from ui.theme import GREEN, RED
from ui.widgets import PageHeader, make_button, make_item, setup_table

logger = logging.getLogger(__name__)


class CoursesPage(QWidget):
    data_changed = Signal()

    COLUMNS = ["Kurs nomi", "Narxi", "O'quvchilar soni", "Holat", "Amallar"]
    WIDTHS = [280, 180, 170, 140, 130]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.courses: list[dict] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(PageHeader("Kurslar", "Kurslaringizni boshqaring"))

        toolbar = QHBoxLayout()
        add_btn = make_button("➕  Yangi kurs")
        add_btn.clicked.connect(self._add_course)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)
        hint = QLabel("Kurs o'chirilganda unga biriktirilgan o'quvchilar avval boshqa kursga o'tkazilishi kerak.")
        hint.setObjectName("hintText")
        toolbar.addWidget(hint)
        layout.addLayout(toolbar)

        self.table = setup_table(self.COLUMNS, self.WIDTHS)
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        self.courses = course_service.list_courses()
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        for course in self.courses:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(course["name"]))
            price_text = f"{course['price']:,.0f}".replace(",", " ") + " so'm"
            table.setItem(row, 1, make_item(price_text, align_right=True))
            table.setItem(row, 2, make_item(str(course["student_count"]), align_right=True))
            status = QLabel("🟢  Faol" if course["active"] else "⚪  Nofaol")
            if course["active"]:
                status.setStyleSheet(
                    f"color: {GREEN}; background: {GREEN}22; border: 1px solid {GREEN}55;"
                    "border-radius: 12px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
                )
            else:
                status.setStyleSheet(
                    f"color: #94a3b8; background: #64748b22; border: 1px solid #64748b55;"
                    "border-radius: 12px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
                )
            table.setCellWidget(row, 3, status)
            self._attach_action_button(row, course)
        if not self.courses:
            table.insertRow(0)
            item = make_item("Kurslar yo'q. «➕ Yangi kurs» tugmasini bosing.")
            item.setTextAlignment(Qt.AlignCenter)
            table.setSpan(0, 0, 1, len(self.COLUMNS))
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    def _attach_action_button(self, row: int, course: dict) -> None:
        btn = QToolButton()
        btn.setObjectName("actionButton")
        btn.setText("Amallar ▾")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _=False, b=btn, c=course: self._open_action_menu(b, c))
        self.table.setCellWidget(row, 4, btn)

    def _open_action_menu(self, button, course: dict) -> None:
        from PySide2.QtWidgets import QAction
        from PySide2.QtWidgets import QMenu

        menu = QMenu(button)
        edit_action = QAction("✏️ Tahrirlash", menu)
        edit_action.setData("edit")
        toggle_action = QAction(
            "⏸ Nofaol qilish" if course["active"] else "▶️ Faollashtirish", menu
        )
        toggle_action.setData("toggle")
        delete_action = QAction("🗑 O'chirish", menu)
        delete_action.setData("delete")
        menu.addAction(edit_action)
        menu.addAction(toggle_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        action = menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        if not action:
            return
        if action.data() == "edit":
            self._edit_course(course)
        elif action.data() == "toggle":
            self._toggle_course(course)
        elif action.data() == "delete":
            self._delete_course(course)

    def _add_course(self) -> None:
        dlg = dialogs.CourseDialog(self)
        if dlg.exec():
            self._after_change()

    def _edit_course(self, course: dict) -> None:
        dlg = dialogs.CourseDialog(self, course)
        if dlg.exec():
            self._after_change()

    def _toggle_course(self, course: dict) -> None:
        try:
            course_service.set_course_active(course["id"], not course["active"])
            self._after_change()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _delete_course(self, course: dict) -> None:
        if not dialogs.confirm(
            self,
            f"«{course['name']}» kursini o'chirishni xohlaysizmi?\nBu amalni qaytarib bo'lmaydi.",
            ok_text="O'chirish",
        ):
            return
        try:
            course_service.delete_course(course["id"])
            self._after_change()
        except ValueError as exc:
            dialogs.warning(self, str(exc))
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def _after_change(self) -> None:
        self.refresh()
        self.data_changed.emit()