"""Hisobotlar bo'limi."""

from __future__ import annotations

import logging

from PySide2.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from services import report_service
from ui import dialogs
from ui.theme import GREEN, YELLOW
from ui.widgets import (
    Card,
    PageHeader,
    make_button,
    make_item,
    setup_table,
)

logger = logging.getLogger(__name__)


class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(PageHeader("Hisobotlar", "Umumiy statistika va moliyaviy ko'rsatkichlar"))

        # ---- Moliyaviy ----
        finance_row = QHBoxLayout()
        finance_row.setSpacing(14)
        self.finance_paid = Card()
        fp_lay = QVBoxLayout(self.finance_paid)
        fp_lay.setContentsMargins(16, 12, 16, 12)
        fp_lay.setSpacing(4)
        fp_title = QLabel("Jami tushgan to'lov")
        fp_title.setObjectName("statTitle")
        self.fp_value = QLabel("0 so'm")
        self.fp_value.setObjectName("statValue")
        self.fp_value.setStyleSheet(f"color: {GREEN};")
        fp_lay.addWidget(fp_title)
        fp_lay.addWidget(self.fp_value)

        self.finance_expected = Card()
        fe_lay = QVBoxLayout(self.finance_expected)
        fe_lay.setContentsMargins(16, 12, 16, 12)
        fe_lay.setSpacing(4)
        fe_title = QLabel("Kutilayotgan summa")
        fe_title.setObjectName("statTitle")
        self.fe_value = QLabel("0 so'm")
        self.fe_value.setObjectName("statValue")
        self.fe_value.setStyleSheet(f"color: {YELLOW};")
        fe_lay.addWidget(fe_title)
        fe_lay.addWidget(self.fe_value)
        finance_row.addWidget(self.finance_paid)
        finance_row.addWidget(self.finance_expected)
        finance_row.addStretch(1)
        layout.addLayout(finance_row)

        # ---- Kurslar bo'yicha ----
        table_title_row = QHBoxLayout()
        title = QLabel("Kurslar bo'yicha statistika")
        title.setObjectName("cardTitle")
        table_title_row.addWidget(title)
        table_title_row.addStretch(1)
        export_btn = make_button("📄  PDF eksport")
        export_btn.clicked.connect(self._export_pdf)
        table_title_row.addWidget(export_btn)
        layout.addLayout(table_title_row)

        self.table = setup_table(
            ["Kurs", "O'quvchilar soni", "To'laganlar", "Tushgan summa", "Kutilayotgan summa"],
            widths=[240, 160, 160, 220, 220],
        )
        layout.addWidget(self.table, 1)

        journal_title = QLabel("Faoliyat jurnali (PDF ga ham qo'shiladi)")
        journal_title.setObjectName("cardTitle")
        layout.addWidget(journal_title)
        self.journal_table = setup_table(
            ["Sana", "Bo'lim", "Harakat"],
            widths=[140, 140, 700],
        )
        self.journal_table.setMinimumHeight(180)
        layout.addWidget(self.journal_table, 1)

        self.refresh()

    def refresh(self) -> None:
        from services import activity_service

        data = report_service.summary()
        self.fp_value.setText(data["actual_revenue_display"])
        self.fe_value.setText(data["expected_display"])
        journal = activity_service.list_logs(limit=100)
        table = self.journal_table
        table.setRowCount(0)
        for entry in journal:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(entry["datetime_display"]))
            table.setItem(row, 1, make_item(entry["category"]))
            table.setItem(row, 2, make_item(entry["action"]))

        table = self.table
        table.setRowCount(0)
        for row_data in data["course_breakdown"]:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, make_item(row_data["course_name"]))
            table.setItem(row, 1, make_item(str(row_data["student_count"]), align_right=True))
            table.setItem(row, 2, make_item(str(row_data["paid_count"]), align_right=True))
            table.setItem(row, 3, make_item(row_data["revenue_display"], align_right=True))
            table.setItem(row, 4, make_item(row_data["expected_display"], align_right=True))
        if not data["course_breakdown"]:
            table.insertRow(0)
            item = make_item("Kurslar yo'q")
            table.setItem(0, 0, item)

    def _export_pdf(self) -> None:
        from pathlib import Path

        default_name = Path("kurs_manager_hisobot.pdf")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Hisobotni saqlash",
            str(default_name),
            "PDF fayl (*.pdf)",
        )
        if not path:
            return
        try:
            saved = report_service.export_pdf(path)
            dialogs.info(self, f"Hisobot saqlandi:\n{saved}")
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)