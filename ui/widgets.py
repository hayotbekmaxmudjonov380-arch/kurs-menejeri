"""Qayta ishlatiladigan UI komponentlar."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.theme import STATUS_META


class Card(QFrame):
    """Yumaloq burchakli panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(90)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        layout.addWidget(title_label)
        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setObjectName("pageSub")
            layout.addWidget(sub_label)


class StatCard(Card):
    """Rangli statistika kartasi."""

    def __init__(self, title: str, value, color: str, emoji: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        layout.addWidget(title_label)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("statValue")
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

    def set_value(self, value) -> None:
        self.value_label.setText(str(value))


class StatusBadge(QLabel):
    """To'lov holati rangli badge."""

    def __init__(self, status: str, parent=None):
        super().__init__(parent)
        meta = STATUS_META.get(status, STATUS_META["unpaid"])
        color = meta["color"]
        label = meta["label"]
        emoji = meta["emoji"]
        self.setText(f"{emoji}  {label}")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(140)
        self.setStyleSheet(
            f"background-color: {color}22; color: {color};"
            f"border: 1px solid {color}55; border-radius: 12px;"
            f"padding: 4px 12px; font-size: 11px; font-weight: 700;"
        )


def make_button(
    text: str,
    kind: str = "primary",
    parent=None,
    object_name: str | None = None,
) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty("kind", kind)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if object_name:
        btn.setObjectName(object_name)
    return btn


def make_chip(text: str, parent=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty("kind", "chip")
    btn.setCheckable(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def make_search_input(placeholder: str = "F.I.Sh yoki telefon raqamini qidiring...", parent=None) -> QLineEdit:
    edit = QLineEdit(parent)
    edit.setObjectName("search")
    edit.setPlaceholderText(placeholder)
    edit.setClearButtonEnabled(True)
    edit.setMinimumWidth(280)
    return edit


def setup_table(
    columns: list[str],
    widths: list[int] | None = None,
    stretch_last: bool = True,
) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table.verticalHeader().setDefaultSectionSize(48)
    table.setWordWrap(False)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    header = table.horizontalHeader()
    if widths:
        for idx, w in enumerate(widths):
            header.resizeSection(idx, w)
    if stretch_last:
        header.setStretchLastSection(True)
    return table


def set_cell_widget_center(table: QTableWidget, row: int, col: int, widget: QWidget) -> None:
    table.setCellWidget(row, col, widget)


def make_item(text: str, align_right: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if align_right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


def text_color_for(hex_color: str) -> QColor:
    return QColor(hex_color)


FIELD_BG = "#333"
FIELD_ACCENT = "#00bfff"


def _field_stylesheet(floated: bool, focused: bool) -> str:
    pad = "18px 10px 6px 10px" if floated else "10px"
    border = FIELD_ACCENT if (floated and focused) else "rgba(105, 105, 105, 0.4)"
    return (
        "QLineEdit {"
        f"background-color: {FIELD_BG}; color: #fff;"
        f"border: 1px solid {border}; border-radius: 10px;"
        f"padding: {pad}; font-size: 14px;"
        "selection-background-color: #00bfff; selection-color: #fff;"
        "}"
    )


class FloatLabel(QObject):
    """Matn maydoni ichidagi suzuvchi label.

    Bo'sh va fokusda bo'lmasa — label ichida katta kulrang;
    yozilganda yoki fokusda — yuqoriga chiqib kichik cyan bo'ladi.
    Har qanday QLineEdit (jumladan MoneyEdit, DateEdit) bilan ishlaydi.
    """

    def __init__(self, edit: QLineEdit, text: str):
        super().__init__(edit)
        self.edit = edit
        self.label = QLabel(text, edit)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        edit.setPlaceholderText("")
        edit.installEventFilter(self)
        try:
            edit.textChanged.connect(lambda _t: self.update())
        except (RuntimeError, TypeError):
            pass
        self.update()

    def eventFilter(self, obj, event):
        if obj is self.edit and event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
            QEvent.Type.Resize,
        ):
            self.update()
        return super().eventFilter(obj, event)

    def floated(self) -> bool:
        return self.edit.hasFocus() or bool(self.edit.text())

    def update(self) -> None:
        f = self.floated()
        font = self.label.font()
        width = max(0, self.edit.width() - 20)
        if f:
            self.label.setGeometry(10, 1, width, 15)
            font.setPointSize(8)
            font.setBold(True)
            self.label.setFont(font)
            self.label.setStyleSheet(
                "background: transparent; border: none; color: #00bfff;"
            )
        else:
            self.label.setGeometry(10, 13, width, 22)
            font.setPointSize(11)
            font.setBold(False)
            self.label.setFont(font)
            self.label.setStyleSheet(
                "background: transparent; border: none; color: #8a8a8a;"
            )
        self.edit.setStyleSheet(_field_stylesheet(f, self.edit.hasFocus()))
        self.label.show()
        self.label.raise_()


class PulseDot(QWidget):
    """Sarlavha yonidagi pulsatsiyalanuvchi nuqta."""

    def __init__(self, parent=None, color: str = "#00bfff"):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(22, 22)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def _tick(self) -> None:
        if self.isVisible():
            self._phase = (self._phase + 0.04) % 1.0
            self.update()

    def showEvent(self, event) -> None:
        if not self._timer.isActive():
            self._timer.start(60)
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        cx, cy = 11, 11
        radius = 7 + self._phase * 7
        ring = QColor(self._color)
        ring.setAlpha(int(255 * (1 - self._phase)))
        painter.setBrush(ring)
        painter.drawEllipse(int(cx - radius), int(cy - radius),
                            int(radius * 2), int(radius * 2))
        painter.setBrush(self._color)
        painter.drawEllipse(cx - 7, cy - 7, 14, 14)
        painter.end()


class MoneyEdit(QLineEdit):
    """Pul miqdori kiritish maydoni.

    Yozayotganda minglik ajratgichlarni avtomatik qo'yadi
    (500000 -> "500 000"), kursor silliq yuradi, sufiks yo'q.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Masalan: 500 000")
        self.setInputMethodHints(Qt.InputMethodHint.ImhFormattedNumbersOnly)
        self.textChanged.connect(self._on_text_changed)
        self._formatting = False

    def _on_text_changed(self, text: str) -> None:
        if self._formatting:
            return
        digits = "".join(ch for ch in text if ch.isdigit())
        digits = digits.lstrip("0") or ("0" if digits else "")
        formatted = f"{int(digits):,}".replace(",", " ") if digits else ""
        if formatted != text:
            self._formatting = True
            try:
                # Foydalanuvchi yozgan raqamlar sonini topib, formatlangan
                # matnda o'sha miqdordagi raqamdan keyinga kursorni qo'yish
                cursor = self.cursorPosition()
                digits_before = sum(1 for ch in text[:cursor] if ch.isdigit())
                pos = 0
                seen = 0
                for i, ch in enumerate(formatted):
                    if ch.isdigit():
                        seen += 1
                        if seen == digits_before:
                            pos = i + 1
                            break
                else:
                    pos = len(formatted)
                self.setText(formatted)
                self.setCursorPosition(pos)
            finally:
                self._formatting = False

    def value(self) -> float:
        digits = "".join(ch for ch in self.text() if ch.isdigit())
        try:
            return float(digits) if digits else 0.0
        except ValueError:
            return 0.0

    def setValue(self, amount: float) -> None:
        try:
            amount = float(amount or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount > 0:
            self.setText(f"{int(amount):,}".replace(",", " "))
        else:
            self.clear()


def _format_uz_phone(national: str) -> str:
    """9 xonali milliy raqamni '+998 99 768 96 85' ko'rinishiga keltiradi."""
    national = national[:12]
    out = "+998"
    for part in (national[:2], national[2:5], national[5:7], national[7:9]):
        if part:
            out += " " + part
    if national[9:]:
        out += " " + national[9:]
    return out


class PhoneEdit(QLineEdit):
    """Telefon raqami maydoni (+998 avtomatik).

    Foydalanuvchi faqat 99 768 96 85 yozadi — +998 prefiksi o'zi
    qo'shiladi. Kursor silliq yuradi, faqat raqam qabul qiladi.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setInputMethodHints(Qt.InputMethodHint.ImhFormattedNumbersOnly)
        self.setMaxLength(19)
        self.textChanged.connect(self._on_text_changed)
        self._formatting = False

    def _on_text_changed(self, text: str) -> None:
        if self._formatting:
            return
        import re as _re

        digits = _re.sub(r"\D", "", text)
        if digits.startswith("998"):
            national = digits[3:]
        else:
            national = digits
        if not national:
            if text:
                self._set_text("")
            return
        formatted = _format_uz_phone(national)
        if formatted != text:
            self._formatting = True
            try:
                cursor = self.cursorPosition()
                before_digits = "".join(
                    ch for ch in text[:cursor] if ch.isdigit()
                )
                # "+998" prefiks raqamlarini hisobdan chiqaramiz
                if before_digits.startswith("998"):
                    national_before = len(before_digits) - 3
                else:
                    national_before = len(before_digits)
                national_before = max(0, national_before)
                # "+998 " (5 belgi) dan keyingi national qismda izlash
                pos = len(formatted)
                seen = 0
                for i in range(5, len(formatted)):
                    if formatted[i].isdigit():
                        seen += 1
                        if seen == national_before:
                            pos = i + 1
                            break
                self._set_text(formatted)
                self.setCursorPosition(pos)
            finally:
                self._formatting = False

    def _set_text(self, text: str) -> None:
        self._formatting = True
        try:
            self.setText(text)
        finally:
            self._formatting = False


class DateEdit(QLineEdit):
    """Sana kiritish maydoni (DD.MM.YYYY).

    Foydalanuvchi faqat raqam yozadi — nuqtalar avtomatik qo'yiladi
    (23092026 -> "23.09.2026"), kursor silliq yuradi.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("KK.OO.YYYY")
        self.setInputMethodHints(Qt.InputMethodHint.ImhFormattedNumbersOnly)
        self.setMaxLength(10)
        self.textChanged.connect(self._on_text_changed)
        self._formatting = False

    def _on_text_changed(self, text: str) -> None:
        if self._formatting:
            return
        digits = "".join(ch for ch in text if ch.isdigit())[:8]
        if not digits:
            if text:
                self._set_text("")
            return
        # DD.MM.YYYY guruhlash
        parts = [digits[:2], digits[2:4], digits[4:8]]
        formatted = parts[0]
        if len(digits) > 2:
            formatted += "." + parts[1]
        if len(digits) > 4:
            formatted += "." + parts[2]
        if formatted != text:
            self._formatting = True
            try:
                cursor = self.cursorPosition()
                digits_before = sum(1 for ch in text[:cursor] if ch.isdigit())
                pos = 0
                seen = 0
                for i, ch in enumerate(formatted):
                    if ch.isdigit():
                        seen += 1
                        if seen == digits_before:
                            pos = i + 1
                            break
                else:
                    pos = len(formatted)
                self._set_text(formatted)
                self.setCursorPosition(pos)
            finally:
                self._formatting = False

    def _set_text(self, text: str) -> None:
        self._formatting = True
        try:
            self.setText(text)
        finally:
            self._formatting = False

    def date(self):
        """Kiritilgan sanani datetime.date ko'rinishida qaytaradi (None bo'lishi mumkin)."""
        from datetime import date as _date

        digits = "".join(ch for ch in self.text() if ch.isdigit())
        if len(digits) != 8:
            return None
        try:
            day, month, year = int(digits[:2]), int(digits[2:4]), int(digits[4:8])
            return _date(year, month, day)
        except ValueError:
            return None

    def setDate(self, value) -> None:
        """datetime.date / QDate qabul qiladi."""
        from datetime import date as _date
        from datetime import datetime as _dt

        if value is None:
            self.clear()
            return
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            try:
                if hasattr(value, "toPython"):  # QDate
                    value = value.toPython()
                if isinstance(value, _dt):
                    value = value.date()
                self._set_text(value.strftime("%d.%m.%Y"))
                return
            except (ValueError, AttributeError):
                pass
        self.clear()

    def isValid(self) -> bool:
        return self.date() is not None