"""Dialog oynalari: o'quvchi, kurs, to'lov formalari va tasdiqlash."""

from __future__ import annotations

import logging
from datetime import date as _date
from datetime import datetime

from PySide2.QtCore import QDate, QDateTime, Qt, QTime
from PySide2.QtWidgets import QAction
from PySide2.QtGui import QFont
from PySide2.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services import course_service, payment_service, student_service
from services import attendance_service, group_service, reminder_service, test_service
from ui import theme
from ui.theme import STATUS_META
from ui.widgets import (
    DateEdit,
    FloatLabel,
    MoneyEdit,
    PhoneEdit,
    PulseDot,
    StatusBadge,
    make_button,
    make_item,
    setup_table,
)
from utils import validators

logger = logging.getLogger(__name__)

MONEY_SUFFIX = " so'm"


def confirm(
    parent: QWidget | None,
    message: str,
    title: str = "Tasdiqlash",
    ok_text: str = "Ha, davom etish",
    cancel_text: str = "Bekor qilish",
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setIcon(QMessageBox.Warning)
    ok_btn = box.addButton(ok_text, QMessageBox.AcceptRole)
    cancel_btn = box.addButton(cancel_text, QMessageBox.RejectRole)
    box.setDefaultButton(cancel_btn)
    box.exec()
    return box.clickedButton() is ok_btn


def info(parent: QWidget | None, message: str, title: str = "Ma'lumot") -> None:
    QMessageBox.information(parent, title, message)


def warning(parent: QWidget | None, message: str, title: str = "Diqqat") -> None:
    QMessageBox.warning(parent, title, message)


def error(parent: QWidget | None, message: str, title: str = "Xatolik") -> None:
    QMessageBox.critical(parent, title, message)


def error_from_exception(parent: QWidget | None, exc: Exception) -> None:
    message = student_service.normalize_error(exc)
    logger.exception("Xatolik yuz berdi")
    error(parent, message)


def build_status_menu(parent: QWidget, current: str | None = None) -> QMenu:
    """2 statusli QMenu yaratadi (current status disabled bo'ladi)."""
    menu = QMenu(parent)
    for key in ("paid", "unpaid"):
        meta = STATUS_META[key]
        action = QAction(f"{meta['emoji']}  {meta['label']}", menu)
        action.setData(key)
        if key == current:
            action.setEnabled(False)
        menu.addAction(action)
    return menu


def build_student_menu(parent: QWidget, current: str | None = None) -> QMenu:
    """Jadvaldagi «Amallar» menyusi: batafsil/tahrirlash + statuslar + o'chirish.

    Qaytarilgan action.data() qiymatlari:
      - "detail", "edit", "delete" — oddiy amallar
      - ("status", key)            — to'lov holatini o'zgartirish
    """
    menu = QMenu(parent)
    detail = QAction("🏷 Batafsil", menu)
    detail.setData("detail")
    edit = QAction("✏️ Tahrirlash", menu)
    edit.setData("edit")
    menu.addAction(detail)
    menu.addAction(edit)
    menu.addSeparator()
    for key in ("paid", "unpaid"):
        meta = STATUS_META[key]
        action = QAction(f"{meta['emoji']}  {meta['label']}", menu)
        action.setData(("status", key))
        if key == current:
            action.setEnabled(False)
        menu.addAction(action)
    menu.addSeparator()
    delete = QAction("🗑 O'chirish", menu)
    delete.setData("delete")
    menu.addAction(delete)
    return menu


def _combo_with_statuses(current: str | None = None) -> QComboBox:
    combo = QComboBox()
    for key in ("paid", "unpaid"):
        meta = STATUS_META[key]
        combo.addItem(f"{meta['emoji']}  {meta['label']}", key)
        if key == current:
            combo.setCurrentIndex(combo.count() - 1)
    return combo


class StudentDialog(QDialog):
    """Yangi o'quvchi qo'shish / tahrirlash formasi."""

    def __init__(
        self,
        parent: QWidget | None = None,
        student: dict | None = None,
    ):
        super().__init__(parent)
        self.student = student
        self.setWindowTitle("Tahrirlash" if student else "Yangi o'quvchi")
        self.setProperty("formStyle", "register")
        self.setMinimumWidth(480)
        self.setModal(True)
        # Kichik ekranlarga sig'ishi uchun: balandlik chegarasi + scroll
        try:
            from PySide2.QtWidgets import QApplication

            screen = QApplication.primaryScreen()
            if screen is not None:
                avail = screen.availableGeometry().height()
                self.setMaximumHeight(int(avail * 0.92))
        except Exception:  # noqa: BLE001
            pass

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(10)

        body = QWidget()
        body.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.addWidget(PulseDot(self))
        title = QLabel("Tahrirlash" if student else "Yangi o'quvchi")
        title.setStyleSheet(
            "font-size: 28px; font-weight: 600; color: #00bfff;"
            "background: transparent; border: none;"
        )
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        message = QLabel(
            "Ma'lumotlarni yangilang."
            if student else
            "Yangi o'quvchi qo'shing va to'liq boshqaring."
        )
        message.setWordWrap(True)
        message.setStyleSheet(
            "font-size: 14px; color: rgba(255, 255, 255, 0.7);"
            "background: transparent; border: none;"
        )
        layout.addWidget(message)

        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self._name_float = FloatLabel(self.name_edit, "F.I.Sh *")
        self.phone_edit = PhoneEdit()
        self._phone_float = FloatLabel(self.phone_edit, "Telefon *")

        self.course_combo = QComboBox()
        self.course_combo.addItem("Kursni tanlang", None)
        for c in course_service.all_courses():
            suffix = "" if c["active"] else " (nofaol)"
            self.course_combo.addItem(f"{c['name']}{suffix}", c["id"])

        self.status_combo = _combo_with_statuses()

        self.grade_combo = QComboBox()
        self.grade_combo.addItem("Tanlanmagan", "")
        for grade_name in ("7-sinf", "8-sinf", "9-sinf", "10-sinf", "11-sinf"):
            self.grade_combo.addItem(grade_name, grade_name)

        self.total_edit = MoneyEdit()
        self._total_float = FloatLabel(self.total_edit, "Umumiy kurs narxi (so'm)")
        self.paid_edit = MoneyEdit()
        self._paid_float = FloatLabel(self.paid_edit, "To'langan summa (so'm)")
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet(
            "font-size: 16px; font-weight: 800; color: #3b82f6;"
            "background: transparent; border: none;"
        )
        self.total_edit.textChanged.connect(self._update_percent)
        self.paid_edit.textChanged.connect(self._update_percent)

        self.date_edit = DateEdit()
        self._date_float = FloatLabel(
            self.date_edit, "Qo'shilgan sana (KK.OO.YYYY)")
        self.date_edit.setDate(_date.today())

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("Izoh (ixtiyoriy)")
        self.note_edit.setFixedHeight(80)
        self.note_edit.setStyleSheet(
            "QPlainTextEdit {"
            "background-color: #333; color: #fff;"
            "border: 1px solid rgba(105, 105, 105, 0.4); border-radius: 10px;"
            "padding: 10px; font-size: 14px;"
            "selection-background-color: #00bfff; selection-color: #fff;"
            "}"
            "QPlainTextEdit:focus { border: 1px solid #00bfff; }"
        )

        form.addWidget(self.name_edit)
        form.addWidget(self.phone_edit)
        form.addWidget(self._caption("Sinf"))
        form.addWidget(self.grade_combo)
        form.addWidget(self._caption("Kurs *"))
        form.addWidget(self.course_combo)
        form.addWidget(self._caption("To'lov holati"))
        form.addWidget(self.status_combo)
        form.addWidget(self.total_edit)
        form.addWidget(self.paid_edit)
        form.addWidget(self._caption("To'langan foiz (avtomatik)"))
        form.addWidget(self.percent_label)
        form.addWidget(self.date_edit)

        form.addWidget(self._caption("Guruhlar"))
        self.groups_list = QListWidget()
        self.groups_list.setObjectName("groupsList")
        self.groups_list.setMaximumHeight(132)
        for g in group_service.list_groups():
            item = QListWidgetItem(f"👥  {g['name']}")
            item.setData(Qt.UserRole, g["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.groups_list.addItem(item)
        if self.groups_list.count() == 0:
            item = QListWidgetItem("Avval Guruhlar bo'limida guruh yarating.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.groups_list.addItem(item)
        form.addWidget(self.groups_list)

        form.addWidget(self._caption("Izoh"))
        form.addWidget(self.note_edit)
        layout.addLayout(form)

        self.course_combo.currentIndexChanged.connect(self._sync_fee_default)

        if not student:
            hint = QLabel("Kurs bo'sh bo'lsa avval «Kurslar» bo'limida kurs yarating.")
            hint.setObjectName("hintText")
            layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = make_button("Bekor qilish", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("💾 Saqlash")
        save_btn.setProperty("formSubmit", True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

        if student:
            self._fill(student)

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            "font-size: 13px; color: #b3b3b3;"
            "background: transparent; border: none;"
        )
        return label

    def _sync_fee_default(self) -> None:
        """Kurs tanlanganda narx bo'sh bo'lsa kurs narxini qo'yadi."""
        if self.total_edit.value() > 0:
            return
        course_id = self.course_combo.currentData()
        if course_id is None:
            return
        course = course_service.get_course(course_id)
        if course:
            self.total_edit.setValue(course["price"])

    def _update_percent(self) -> None:
        total = self.total_edit.value()
        paid = self.paid_edit.value()
        pct = round(paid * 100 / total, 1) if total > 0 and paid > 0 else 0.0
        self.percent_label.setText(f"{pct}%")

    def _selected_groups(self) -> list[int]:
        result = []
        for i in range(self.groups_list.count()):
            item = self.groups_list.item(i)
            gid = item.data(Qt.UserRole)
            if gid and item.checkState() == Qt.CheckState.Checked:
                result.append(gid)
        return result

    def _fill(self, student: dict) -> None:
        self.name_edit.setText(student["full_name"])
        self.phone_edit.setText(student["phone"])
        g_idx = self.grade_combo.findData(student.get("grade") or "")
        if g_idx >= 0:
            self.grade_combo.setCurrentIndex(g_idx)
        idx = self.course_combo.findData(student["course_id"])
        if idx >= 0:
            self.course_combo.setCurrentIndex(idx)
        self.total_edit.setValue(student.get("total_price") or 0.0)
        self.paid_edit.setValue(student.get("paid_amount") or 0.0)
        self._update_percent()
        s_idx = self.status_combo.findData(student["payment_status"])
        if s_idx >= 0:
            self.status_combo.setCurrentIndex(s_idx)
        if student.get("created_at"):
            self.date_edit.setDate(student["created_at"])
        for gid in student.get("group_ids", []) or []:
            for i in range(self.groups_list.count()):
                item = self.groups_list.item(i)
                if item.data(Qt.UserRole) == gid:
                    item.setCheckState(Qt.CheckState.Checked)
        self.note_edit.setPlainText(student.get("note", ""))

    def _on_save(self) -> None:
        data = self.get_data()
        if data is None:
            return
        groups = data.pop("group_ids", [])
        try:
            if self.student:
                student_service.update_student(self.student["id"], **data)
                group_service.set_student_groups(self.student["id"], groups)
                info(self, "O'quvchi ma'lumotlari saqlandi.")
            else:
                new_id = student_service.create_student(**data)
                group_service.set_student_groups(new_id, groups)
                info(self, "Yangi o'quvchi qo'shildi.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)

    def get_data(self) -> dict | None:
        full_name = self.name_edit.text().strip()
        phone = self.phone_edit.text().strip()
        course_id = self.course_combo.currentData()
        payment_status = self.status_combo.currentData()
        grade = self.grade_combo.currentData() or ""
        note = self.note_edit.toPlainText().strip()
        total_price = self.total_edit.value()
        paid_amount = self.paid_edit.value()

        err = validators.validate_full_name(full_name)
        if err:
            warning(self, err)
            return None
        err = validators.validate_phone(phone)
        if err:
            warning(self, err)
            return None
        err = validators.validate_course_selected(course_id)
        if err:
            warning(self, err)
            return None
        if payment_status is None:
            payment_status = "paid"

        created = self.date_edit.date()
        if created is None:
            warning(self, "Qo'shilgan sanani to'g'ri kiriting (KK.OO.YYYY).")
            return None
        data = {
            "full_name": full_name,
            "phone": phone,
            "course_id": course_id,
            "payment_status": payment_status,
            "note": note,
            "total_price": total_price,
            "paid_amount": paid_amount,
            "grade": grade,
            "group_ids": self._selected_groups(),
            "created_at": datetime(created.year, created.month, created.day),
        }
        return data


class StudentDetailDialog(QDialog):
    """O'quvchi tafsilotlari oynasi."""

    def __init__(
        self,
        parent: QWidget | None,
        student_id: int,
        on_change=None,
    ):
        super().__init__(parent)
        self.student_id = student_id
        self.on_change = on_change or (lambda: None)
        self.setWindowTitle("O'quvchi tafsilotlari")
        self.setMinimumSize(640, 560)
        self.setModal(True)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(20, 18, 20, 18)
        self.root.setSpacing(12)
        self._build()
        self._reload()

    def _build(self) -> None:
        from ui.widgets import Card

        self.header_row = QHBoxLayout()
        self.name_label = QLabel()
        self.name_label.setObjectName("pageTitle")
        self.badge = StatusBadge("paid")
        self.header_row.addWidget(self.name_label)
        self.header_row.addStretch(1)
        self.header_row.addWidget(self.badge)
        self.root.addLayout(self.header_row)

        head = QLabel("Asosiy ma'lumotlar")
        head.setObjectName("cardTitle")
        self.root.addWidget(head)

        self.info_card = Card()
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(24)
        self.info_labels: dict[str, QLabel] = {}
        for key, caption in [
            ("phone", "Telefon"),
            ("grade", "Sinf"),
            ("course", "Kurs"),
            ("total", "Umumiy narx"),
            ("paid", "To'langan"),
            ("percent", "Foiz"),
            ("date", "Qo'shilgan sana"),
            ("due", "To'lov muddati"),
        ]:
            box = QVBoxLayout()
            cap = QLabel(caption)
            cap.setObjectName("cardSub")
            val = QLabel("—")
            val.setObjectName("statValue")
            val.setStyleSheet(f"font-size: 15px; color: {theme.fg()};")
            box.addWidget(cap)
            box.addWidget(val)
            info_layout.addLayout(box)
            self.info_labels[key] = val
        self.root.addWidget(self.info_card)

        note_title = QLabel("Izoh")
        note_title.setObjectName("cardTitle")
        self.root.addWidget(note_title)
        self.note_label = QLabel("—")
        self.note_label.setWordWrap(True)
        self.root.addWidget(self.note_label)

        pay_title = QLabel("To'lov tarixi")
        pay_title.setObjectName("cardTitle")
        self.root.addWidget(pay_title)
        self.pay_table = setup_table(
            ["Sana", "Summa", "Holat", "Izoh"],
            widths=[110, 150, 170, 300],
        )
        self.pay_table.setMinimumHeight(170)
        self.root.addWidget(self.pay_table)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        edit_btn = make_button("✏️ Tahrirlash", "ghost")
        edit_btn.clicked.connect(self._edit)
        status_btn = make_button("🔄 To'lov holatini o'zgartirish", "warning")
        status_btn.clicked.connect(self._change_status)
        delete_btn = make_button("🗑 O'chirish", "danger")
        delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(status_btn)
        btn_row.addWidget(delete_btn)
        self.root.addLayout(btn_row)

    def _reload(self) -> None:
        student = student_service.get_student(self.student_id)
        if not student:
            error(self, "O'quvchi topilmadi.")
            self.reject()
            return
        self.name_label.setText(student["full_name"])
        self.info_labels["phone"].setText(student["phone"] or "—")
        self.info_labels["grade"].setText(student.get("grade_display", "—"))
        self.info_labels["course"].setText(student["course_name"])
        total = student.get("total_price", 0.0) or 0.0
        paid = student.get("paid_amount", 0.0) or 0.0
        self.info_labels["total"].setText(
            f"{total:,.0f}".replace(",", " ") + " so'm" if total > 0 else "—"
        )
        self.info_labels["paid"].setText(
            f"{paid:,.0f}".replace(",", " ") + " so'm" if paid > 0 else "—"
        )
        self.info_labels["percent"].setText(f"{student.get('paid_percent', 0.0)}%")
        self.info_labels["date"].setText(student["created_display"])
        self.info_labels["due"].setText(
            f"📅 {student.get('due_display', '—')} ({student.get('due_label', '')})"
        )
        self.note_label.setText(student["note"] or "Izoh yo'q")
        self.badge.setParent(None)
        self.badge = StatusBadge(student["payment_status"])
        self.header_row.insertWidget(2, self.badge)

        self.pay_table.setRowCount(0)
        for p in payment_service.list_by_student(self.student_id):
            row = self.pay_table.rowCount()
            self.pay_table.insertRow(row)
            badge = StatusBadge(p["status"])
            amount_text = f"{p['amount']:,.0f}".replace(",", " ") + MONEY_SUFFIX
            self.pay_table.setItem(row, 0, make_item(p["date_display"]))
            self.pay_table.setItem(row, 1, make_item(amount_text))
            self.pay_table.setCellWidget(row, 2, badge)
            self.pay_table.setItem(row, 3, make_item(p["note"] or "—"))

    def _edit(self) -> None:
        student = student_service.get_student(self.student_id)
        if not student:
            return
        dlg = StudentDialog(self, student)
        if dlg.exec() == QDialog.Accepted:
            self._reload()
            self.on_change()

    def _change_status(self) -> None:
        student = student_service.get_student(self.student_id)
        if not student:
            return
        menu = build_status_menu(self, student["payment_status"])
        action = menu.exec_(self.mapToGlobal(self.pos()))
        if not action:
            return
        new_status = action.data()
        if not new_status or new_status == student["payment_status"]:
            return
        try:
            student_service.set_payment_status(self.student_id, new_status)
            info(self, f"Holat «{STATUS_META[new_status]['label']}» ga o'zgartirildi.")
            self._reload()
            self.on_change()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)

    def _delete(self) -> None:
        if not confirm(
            self,
            "Ushbu o'quvchini o'chirishni xohlaysizmi?\nBu amalni qaytarib bo'lmaydi.",
            ok_text="O'chirish",
        ):
            return
        try:
            student_service.delete_student(self.student_id)
            self.accept()
            self.on_change()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class CourseDialog(QDialog):
    """Yangi kurs qo'shish / tahrirlash formasi."""

    def __init__(self, parent=None, course: dict | None = None):
        super().__init__(parent)
        self.course = course
        self.setWindowTitle("Kurs tahrirlash" if course else "Yangi kurs")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Kurs tahrirlash" if course else "Yangi kurs")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Masalan: Python")
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1_000_000_000)
        self.price_spin.setDecimals(0)
        self.price_spin.setSingleStep(100_000)
        self.price_spin.setSuffix(" so'm")
        self.price_spin.setGroupSeparatorShown(True)
        self.active_check = QCheckBox("Faol (o'quvchilar uchun ko'rinadi)")
        self.active_check.setChecked(True)

        form.addRow("Kurs nomi *", self.name_edit)
        form.addRow("Narxi", self.price_spin)
        form.addRow("Holat", self.active_check)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = make_button("Bekor qilish", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("💾 Saqlash")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        if course:
            self.name_edit.setText(course["name"])
            self.price_spin.setValue(course["price"])
            self.active_check.setChecked(course["active"])

    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        price = self.price_spin.value()
        active = self.active_check.isChecked()
        if not name:
            warning(self, "Kurs nomi kiritilishi kerak.")
            return
        try:
            if self.course:
                course_service.update_course(self.course["id"], name, price, active)
                info(self, "Kurs saqlandi.")
            else:
                course_service.create_course(name, price, active)
                info(self, "Yangi kurs qo'shildi.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class PaymentDialog(QDialog):
    """Yangi to'lov qo'shish / to'lovni tahrirlash formasi."""

    def __init__(self, parent=None, payment: dict | None = None):
        super().__init__(parent)
        self.payment = payment
        self.setWindowTitle("To'lovni tahrirlash" if payment else "Yangi to'lov")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("To'lovni tahrirlash" if payment else "Yangi to'lov")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.student_combo = QComboBox()
        for st in student_service.list_students():
            label = f"{st['full_name']}  —  {st['phone']}"
            self.student_combo.addItem(label, st["id"])

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 1_000_000_000)
        self.amount_spin.setDecimals(0)
        self.amount_spin.setSingleStep(50_000)
        self.amount_spin.setSuffix(" so'm")
        self.amount_spin.setGroupSeparatorShown(True)

        self.status_combo = _combo_with_statuses("paid")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("Izoh (ixtiyoriy)")
        self.note_edit.setFixedHeight(70)

        form.addRow("O'quvchi *", self.student_combo)
        form.addRow("Summa *", self.amount_spin)
        form.addRow("Holat", self.status_combo)
        form.addRow("Sana", self.date_edit)
        form.addRow("Izoh", self.note_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = make_button("Bekor qilish", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("💾 Saqlash")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        if payment:
            idx = self.student_combo.findData(payment["student_id"])
            if idx >= 0:
                self.student_combo.setCurrentIndex(idx)
            self.student_combo.setEnabled(False)
            self.amount_spin.setValue(payment["amount"])
            s_idx = self.status_combo.findData(payment["status"])
            if s_idx >= 0:
                self.status_combo.setCurrentIndex(s_idx)
            self.date_edit.setDate(
                QDate(
                    payment["payment_date"].year,
                    payment["payment_date"].month,
                    payment["payment_date"].day,
                )
            )
            self.note_edit.setPlainText(payment["note"])

    def _on_save(self) -> None:
        student_id = self.student_combo.currentData()
        amount = self.amount_spin.value()
        status = self.status_combo.currentData() or "paid"
        date = self.date_edit.date().toPython()
        date_obj = datetime(date.year, date.month, date.day)
        note = self.note_edit.toPlainText().strip()

        if student_id is None:
            warning(self, "O'quvchi tanlanmagan. Avval o'quvchi qo'shing.")
            return
        try:
            if self.payment:
                payment_service.update_payment(
                    self.payment["id"], amount, status, date_obj, note
                )
                info(self, "To'lov saqlandi.")
            else:
                payment_service.add_payment(
                    student_id, amount, status, date_obj, note
                )
                info(self, "Yangi to'lov qo'shildi.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class TestDialog(QDialog):
    """Yangi test natijasi qo'shish / tahrirlash formasi."""

    def __init__(self, parent=None, result: dict | None = None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle("Natijani tahrirlash" if result else "Yangi test natijasi")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Natijani tahrirlash" if result else "Yangi test natijasi")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.student_combo = QComboBox()
        for st in student_service.list_students():
            self.student_combo.addItem(f"{st['full_name']}  —  {st['phone']}", st["id"])

        self.topic_edit = QLineEdit()
        self.topic_edit.setPlaceholderText("Masalan: Organik kimyo")

        self.total_spin = QSpinBox()
        self.total_spin.setRange(1, 500)
        self.total_spin.setValue(20)

        self.correct_spin = QSpinBox()
        self.correct_spin.setRange(0, 500)
        self.correct_spin.setValue(0)

        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #3b82f6;")
        self.total_spin.valueChanged.connect(self._update_percent)
        self.correct_spin.valueChanged.connect(self._update_percent)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("Izoh (ixtiyoriy)")
        self.note_edit.setFixedHeight(70)

        form.addRow("O'quvchi *", self.student_combo)
        form.addRow("Test mavzusi *", self.topic_edit)
        form.addRow("Savollar soni *", self.total_spin)
        form.addRow("To'g'ri javoblar *", self.correct_spin)
        form.addRow("Foiz (avtomatik)", self.percent_label)
        form.addRow("Sana", self.date_edit)
        form.addRow("Izoh", self.note_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = make_button("Bekor qilish", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("💾 Saqlash")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        if result:
            idx = self.student_combo.findData(result["student_id"])
            if idx >= 0:
                self.student_combo.setCurrentIndex(idx)
            self.student_combo.setEnabled(False)
            self.topic_edit.setText(result["topic"])
            self.total_spin.setValue(result["total_questions"])
            self.correct_spin.setValue(result["correct_answers"])
            self.date_edit.setDate(
                QDate(
                    result["result_date"].year,
                    result["result_date"].month,
                    result["result_date"].day,
                )
            )
            self.note_edit.setPlainText(result["note"])
            self._update_percent()

    def _update_percent(self) -> None:
        total = self.total_spin.value()
        correct = self.correct_spin.value()
        pct = test_service.calc_percentage(total, correct)
        grade, _ = test_service.grade_info(pct)
        self.percent_label.setText(f"{pct}% ({grade})")

    def _on_save(self) -> None:
        student_id = self.student_combo.currentData()
        topic = self.topic_edit.text().strip()
        total = self.total_spin.value()
        correct = self.correct_spin.value()
        date = self.date_edit.date().toPython()
        date_obj = datetime(date.year, date.month, date.day)
        note = self.note_edit.toPlainText().strip()

        if student_id is None and not self.result:
            warning(self, "O'quvchi tanlanmagan. Avval o'quvchi qo'shing.")
            return
        try:
            if self.result:
                test_service.update_result(
                    self.result["id"], topic, total, correct, date_obj, note
                )
                info(self, "Natija saqlandi.")
            else:
                test_service.create_result(
                    student_id, topic, total, correct, date_obj, note
                )
                info(self, "Yangi test natijasi qo'shildi.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class ReminderDialog(QDialog):
    """Yangi eslatma qo'shish / tahrirlash formasi."""

    def __init__(self, parent=None, reminder: dict | None = None):
        super().__init__(parent)
        self.reminder = reminder
        self.setWindowTitle("Eslatmani tahrirlash" if reminder else "Yangi eslatma")
        self.setMinimumWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Eslatmani tahrirlash" if reminder else "Yangi eslatma")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Masalan: 10-sinfdan test olish")

        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("Izoh (ixtiyoriy)")
        self.note_edit.setFixedHeight(80)

        form.addRow("Sarlavha *", self.title_edit)
        form.addRow("Sana va vaqt *", self.datetime_edit)
        form.addRow("Izoh", self.note_edit)
        layout.addLayout(form)

        hint = QLabel("⏰ Vaqt kelganda ekranda habar chiqadi.")
        hint.setObjectName("hintText")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = make_button("Bekor qilish", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("💾 Saqlash")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        if reminder:
            self.title_edit.setText(reminder["title"])
            if reminder.get("remind_at"):
                ra = reminder["remind_at"]
                self.datetime_edit.setDateTime(
                    QDateTime(QDate(ra.year, ra.month, ra.day),
                              QTime(ra.hour, ra.minute))
                )
            self.note_edit.setPlainText(reminder.get("note", ""))

    def _on_save(self) -> None:
        title = self.title_edit.text().strip()
        note = self.note_edit.toPlainText().strip()
        qdt = self.datetime_edit.dateTime()
        remind_at = datetime(
            qdt.date().year(), qdt.date().month(), qdt.date().day(),
            qdt.time().hour(), qdt.time().minute(),
        )
        if not title:
            warning(self, "Eslatma sarlavhasini kiriting.")
            return
        try:
            if self.reminder:
                reminder_service.update_reminder(
                    self.reminder["id"], title, note, remind_at
                )
                info(self, "Eslatma saqlandi.")
            else:
                reminder_service.create_reminder(title, note, remind_at)
                info(self, "Yangi eslatma qo'shildi.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class GroupDialog(QDialog):
    """Yangi guruh ochish / nomini tahrirlash formasi."""

    def __init__(self, parent=None, group: dict | None = None):
        super().__init__(parent)
        self.group = group
        self.setWindowTitle("Guruh nomini tahrirlash" if group else "Yangi guruh")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Guruh nomini tahrirlash" if group else "Yangi guruh")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Masalan: Kimyo A guruh")
        form.addRow("Guruh nomi *", self.name_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = make_button("Bekor qilish", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("💾 Saqlash")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        if group:
            self.name_edit.setText(group["name"])

    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            warning(self, "Guruh nomini kiriting.")
            return
        try:
            if self.group:
                group_service.update_group(self.group["id"], name)
                info(self, "Guruh nomi saqlandi.")
            else:
                group_service.create_group(name)
                info(self, "Yangi guruh ochildi.")
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class GroupDetailDialog(QDialog):
    """Guruh a'zolarini boshqarish oynasi."""

    def __init__(self, parent, group_id: int, on_change=None):
        super().__init__(parent)
        self.group_id = group_id
        self.on_change = on_change or (lambda: None)
        self.setWindowTitle("Guruh a'zolari")
        self.setMinimumSize(560, 460)
        self.setModal(True)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(20, 18, 20, 18)
        self.root.setSpacing(12)

        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.root.addWidget(self.title_label)

        add_row = QHBoxLayout()
        add_row.setSpacing(10)
        self.student_combo = QComboBox()
        self.student_combo.setMinimumWidth(300)
        add_btn = make_button("➕  Guruhga qo'shish")
        add_btn.clicked.connect(self._add_member)
        add_row.addWidget(self.student_combo, 1)
        add_row.addWidget(add_btn)
        self.root.addLayout(add_row)

        self.table = setup_table(
            ["F.I.Sh", "Telefon", "To'lov holati", "Ro'yxatga olish sanasi", ""],
            widths=[200, 140, 170, 150, 80],
        )
        self.root.addWidget(self.table, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = make_button("Yopish", "ghost")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        self.root.addLayout(close_row)

        self._reload()

    def _reload(self) -> None:
        group = group_service.get_group(self.group_id)
        if not group:
            error(self, "Guruh topilmadi.")
            self.reject()
            return
        self.title_label.setText(f"👥 {group['name']}")

        self.student_combo.clear()
        self.student_combo.addItem("O'quvchini tanlang", None)
        for st in group_service.available_students(self.group_id):
            label = f"{st['full_name']}  —  {st['phone']}" if st["phone"] else st["full_name"]
            self.student_combo.addItem(label, st["id"])

        members = group_service.list_members(self.group_id)
        table = self.table
        table.setRowCount(0)
        for m in members:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(m["full_name"]))
            table.setItem(row, 1, make_item(m["phone"] or "—"))
            table.setCellWidget(
                row, 2, StatusBadge(m.get("payment_status", "unpaid"))
            )
            table.setItem(row, 3, make_item(m.get("created_display", "—")))
            actions = QWidget()
            actions_lay = QHBoxLayout(actions)
            actions_lay.setContentsMargins(0, 0, 0, 0)
            actions_lay.setSpacing(6)
            mv_btn = QToolButton()
            mv_btn.setObjectName("actionButton")
            mv_btn.setText("↔")
            mv_btn.setToolTip("Boshqa guruhga ko'chirish")
            mv_btn.setCursor(Qt.PointingHandCursor)
            mv_btn.clicked.connect(
                lambda _=False, b=mv_btn, sid=m["student_id"]: self._move_menu(b, sid)
            )
            rm_btn = make_button("🗑", "danger")
            rm_btn.setFixedWidth(44)
            rm_btn.setToolTip("Guruhdan chiqarish")
            rm_btn.clicked.connect(
                lambda _=False, sid=m["student_id"]: self._remove_member(sid)
            )
            actions_lay.addWidget(mv_btn)
            actions_lay.addWidget(rm_btn)
            table.setCellWidget(row, 4, actions)
        if not members:
            table.insertRow(0)
            item = make_item("Guruhda o'quvchilar yo'q")
            item.setTextAlignment(Qt.AlignCenter)
            table.setSpan(0, 0, 1, 5)
            table.setItem(0, 0, item)
            table.setRowHeight(0, 70)

    def _add_member(self) -> None:
        student_id = self.student_combo.currentData()
        if student_id is None:
            warning(self, "O'quvchini tanlang.")
            return
        try:
            group_service.add_member(self.group_id, student_id)
            self._reload()
            self.on_change()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)

    def _remove_member(self, student_id: int) -> None:
        try:
            group_service.remove_member(self.group_id, student_id)
            self._reload()
            self.on_change()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)

    def _move_menu(self, button, student_id: int) -> None:
        others = [
            g for g in group_service.list_groups() if g["id"] != self.group_id
        ]
        if not others:
            warning(self, "Ko'chirish uchun boshqa guruh yo'q.")
            return
        menu = QMenu(button)
        for g in others:
            action = QAction(f"→ {g['name']} ({g['member_count']})", menu)
            action.setData(g["id"])
            menu.addAction(action)
        chosen = menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        if not chosen:
            return
        try:
            target_name = group_service.move_member(
                self.group_id, chosen.data(), student_id
            )
            info(self, f"O'quvchi «{target_name}» guruhiga ko'chirildi.")
            self._reload()
            self.on_change()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)


class MonthPayDialog(QDialog):
    """Oylik to'lov kartochkasi: summa + avtomatik foiz."""

    def __init__(self, parent, student_id: int, year: int, month: int):
        super().__init__(parent)
        from services import monthly_payment_service as _mp

        try:
            self.detail = _mp.get_cell_detail(student_id, year, month)
        except Exception as exc:  # noqa: BLE001
            error(self, str(exc))
            self.detail = None
            self._failed = True
            return
        self._failed = False
        self.student_id = student_id
        self.year = year
        self.month = month
        self.fee = self.detail["fee"]
        self.result_action: str | None = None

        self.setWindowTitle(
            f"{self.detail['month_name']} — {self.detail['full_name']}"
        )
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel(f"{self.detail['month_name']} {year}")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        name_label = QLabel(self.detail["full_name"])
        name_label.setObjectName("cardSub")
        layout.addWidget(name_label)

        form = QFormLayout()
        form.setSpacing(12)
        self.amount_edit = MoneyEdit()
        self.amount_edit.setValue(self.detail["amount"])
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet(
            "font-size: 16px; font-weight: 800; color: #3b82f6;"
        )
        self.amount_edit.textChanged.connect(self._update_percent)
        form.addRow("Oylik narx", QLabel(
            f"{self.fee:,.0f}".replace(",", " ") + " so'm"
        ))
        form.addRow("To'langan summa *", self.amount_edit)
        form.addRow("Foiz (avtomatik)", self.percent_label)
        layout.addLayout(form)
        self._update_percent()

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        unpaid_btn = make_button("✗ To'lamadi", "danger")
        unpaid_btn.clicked.connect(lambda: self._done(False))
        clear_btn = make_button("🗑 Tozalash", "ghost")
        clear_btn.clicked.connect(lambda: self._done(None))
        save_btn = make_button("💾 Saqlash")
        save_btn.setProperty("formSubmit", True)
        save_btn.clicked.connect(lambda: self._done(True))
        btn_row.addWidget(unpaid_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _update_percent(self) -> None:
        pct = 0.0
        if self.fee > 0:
            pct = round(self.amount_edit.value() * 100 / self.fee, 1)
        self.percent_label.setText(f"{pct}%")

    def _done(self, paid) -> None:
        from services import monthly_payment_service as _mp

        if paid is True and self.amount_edit.value() <= 0:
            warning(self, "To'langan summani kiriting.")
            return
        try:
            if paid is None:
                _mp.set_status(self.student_id, self.year, self.month, None)
            elif paid is False:
                _mp.set_status(self.student_id, self.year, self.month, False)
            else:
                _mp.set_status(
                    self.student_id, self.year, self.month, True,
                    self.amount_edit.value(),
                )
            self.result_action = (
                "none" if paid is None else ("paid" if paid else "unpaid")
            )
            self.accept()
        except Exception as exc:  # noqa: BLE001
            error_from_exception(self, exc)