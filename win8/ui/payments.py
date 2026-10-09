"""To'lovlar bo'limi — oylik to'lov jurnali (davomat kabi katakchalar)."""

from __future__ import annotations

import logging
from datetime import date as _date

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import monthly_payment_service as mp
from ui import dialogs
from ui.widgets import (
    PageHeader,
    make_button,
    make_item,
    make_search_input,
    setup_table,
)

logger = logging.getLogger(__name__)


class PillLabel(QLabel):
    """Bosiladigan yumaloq katakcha (web'dagi mp-cell ko'rinishi)."""

    clicked = Signal(int, int)

    def __init__(self, row: int, col: int, parent=None):
        super().__init__(parent)
        self._row = row
        self._col = col
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setTextFormat(Qt.TextFormat.RichText)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._row, self._col)
        super().mousePressEvent(event)


class PaymentsPage(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.year = _date.today().year
        self.students: list[dict] = []
        self.matrix: dict = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(
            PageHeader("To'lovlar", "Oylik to'lov jurnali — katakchani bosing"), 1
        )
        prev_btn = make_button("‹ Oldingi yil", "ghost")
        prev_btn.clicked.connect(lambda: self._shift_year(-1))
        self.year_label = QLabel(str(self.year))
        self.year_label.setObjectName("pageTitle")
        self.year_label.setAlignment(Qt.AlignCenter)
        self.year_label.setMinimumWidth(90)
        today_btn = make_button("Joriy yil", "ghost")
        today_btn.clicked.connect(self._go_current_year)
        next_btn = make_button("Keyingi yil ›", "ghost")
        next_btn.clicked.connect(lambda: self._shift_year(1))
        header_row.addWidget(prev_btn)
        header_row.addWidget(self.year_label)
        header_row.addWidget(today_btn)
        header_row.addWidget(next_btn)
        layout.addLayout(header_row)

        self.stats_label = QLabel()
        self.stats_label.setObjectName("cardSub")
        layout.addWidget(self.stats_label)

        search_row = QHBoxLayout()
        search_row.addStretch(1)
        self.search = make_search_input()
        self.search.textChanged.connect(self.refresh)
        search_row.addWidget(self.search)
        layout.addLayout(search_row)

        columns = ["F.I.Sh", "Kelgan sana"] + [
            name for _, name in mp.ordered_months()
        ]
        widths = [260, 110] + [92] * 12
        self.table = setup_table(columns, widths)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table, 1)

        hint = QLabel("Katakchani bosing — to'lov kartochkasi ochiladi (summa + avtomatik foiz)")
        hint.setObjectName("hintText")
        layout.addWidget(hint)

        self.refresh()

    def _shift_year(self, delta: int) -> None:
        self.year = max(2000, min(self.year + delta, 2100))
        self.refresh()

    def _go_current_year(self) -> None:
        self.year = _date.today().year
        self.refresh()

    def refresh(self) -> None:
        search = self.search.text().strip()
        self.students, self.matrix = mp.get_matrix(self.year, search=search)
        stats = mp.matrix_stats(self.matrix)
        self.year_label.setText(str(self.year))
        collected = f"{stats.get('collected', 0.0):,.0f}".replace(",", " ")
        self.stats_label.setText(
            f"{self.year}-yil: ✓ {stats['paid']} ta to'lov  •  "
            f"✗ {stats['unpaid']} ta to'lanmagan  •  💰 {collected} so'm yig'ilgan"
        )
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.table
        table.setRowCount(0)
        for st in self.students:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(st["full_name"]))
            table.setItem(row, 1, make_item(st["created_display"]))
            for col, month in enumerate(mp.MONTH_ORDER, start=2):
                val = self.matrix[st["id"]][month]
                holder = make_item("")
                holder.setData(
                    Qt.UserRole, (st["id"], month, val)
                )
                holder.setFlags(holder.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col, holder)
                pill = self._make_pill(row, col, st["id"], month, val)
                pill.clicked.connect(self._on_cell_clicked)
                table.setCellWidget(row, col, pill)
        if not self.students:
            table.insertRow(0)
            item = make_item("O'quvchilar yo'q — avval Ro'yxatga olish bo'limida qo'shing")
            item.setTextAlignment(Qt.AlignCenter)
            table.setSpan(0, 0, 1, 14)
            table.setItem(0, 0, item)
            table.setRowHeight(0, 80)

    @staticmethod
    def _cell_paid(val) -> bool | None:
        if isinstance(val, dict):
            return val.get("paid")
        return val

    def _make_pill(self, row: int, col: int, student_id: int, month: int,
                     val) -> PillLabel:
        from ui import theme

        paid = self._cell_paid(val)
        amount = val.get("amount", 0.0) if isinstance(val, dict) else 0.0
        pill = PillLabel(row, col)
        if paid is True:
            pill.setText("✓")
            pill.setStyleSheet(
                "background-color: #189a52; border-radius: 14px;"
                "color: #ffffff; font-size: 20px; font-weight: 800;"
            )
            if amount > 0:
                pill.setToolTip(
                    f"{amount:,.0f}".replace(",", " ") + " so'm"
                )
        elif paid is False:
            pill.setText("✗")
            pill.setStyleSheet(
                "background-color: #e0324b; border-radius: 14px;"
                "color: #ffffff; font-size: 20px; font-weight: 800;"
            )
        else:
            pill.setText("—")
            if theme.current_theme() == "light":
                pill.setStyleSheet(
                    "background-color: #e7edf5; border-radius: 14px;"
                    "color: #8595ad; font-size: 20px; font-weight: 800;"
                )
            else:
                pill.setStyleSheet(
                    "background-color: #16203a; border-radius: 14px;"
                    "color: #64748b; font-size: 20px; font-weight: 800;"
                )
        return pill

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col < 2 or col > 13:
            return
        table = self.table
        item = table.item(row, col)
        if not item:
            return
        student_id, month, val = item.data(Qt.UserRole)
        # Bir bosish: — → ✓ → ✗ → — (summa kiritish shart emas)
        paid = self._cell_paid(val)
        nxt = True if paid is None else (False if paid is True else None)
        try:
            mp.set_status(student_id, self.year, month, nxt)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)
