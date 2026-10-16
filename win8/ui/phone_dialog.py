"""Telefon ulash oynasi (QR kod + bir martalik kod + juftlangan qurilmalar)."""

from __future__ import annotations

import io
import logging

import qrcode
from PySide2.QtCore import Qt, QTimer
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import pairing_service
from ui import dialogs
from ui.widgets import PageHeader, PulseDot, make_button, make_chip

logger = logging.getLogger(__name__)


class PhoneDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Telefon ulash")
        self.setMinimumSize(560, 540)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        # ===== Header: avatar + sarlavha =====
        header = QHBoxLayout()
        header.setSpacing(14)
        avatar = QLabel("📱")
        avatar.setObjectName("phoneAvatar")
        avatar.setFixedSize(46, 46)
        avatar.setAlignment(Qt.AlignCenter)
        header.addWidget(avatar)
        header.addWidget(PageHeader(
            "Telefon ulash",
            "Bir martalik kod — keyin avtomatik ulanadi",
        ), 1)
        layout.addLayout(header)

        # ===== Server holati + IP manzillar =====
        server_card = QWidget()
        server_card.setObjectName("card")
        server_lay = QVBoxLayout(server_card)
        server_lay.setContentsMargins(16, 14, 16, 14)
        server_lay.setSpacing(8)

        server_title_row = QHBoxLayout()
        server_title_row.setSpacing(8)
        self.server_dot = QLabel()
        self.server_dot.setFixedSize(10, 10)
        self.server_dot.setStyleSheet(
            "background-color: #22c55e; border-radius: 5px; border: none;"
        )
        server_title_row.addWidget(self.server_dot)
        server_title = QLabel("Server ishlayapti")
        server_title.setObjectName("cardTitle")
        server_title_row.addWidget(server_title)
        server_title_row.addStretch(1)
        server_lay.addLayout(server_title_row)

        self.status_label = QLabel()
        self.status_label.setObjectName("cardSub")
        self.status_label.setWordWrap(True)
        server_lay.addWidget(self.status_label)

        self.ip_box = QVBoxLayout()
        self.ip_box.setSpacing(6)
        server_lay.addLayout(self.ip_box)
        layout.addWidget(server_card)

        # ===== Kod kartasi =====
        code_card = QWidget()
        code_card.setObjectName("codeCard")
        code_lay = QHBoxLayout(code_card)
        code_lay.setContentsMargins(18, 14, 18, 14)
        code_lay.setSpacing(16)

        code_left = QVBoxLayout()
        code_left.setSpacing(2)
        code_caption = QLabel("4 xonali kod")
        code_caption.setObjectName("statTitle")
        code_left.addWidget(code_caption)
        self.code_label = QLabel("————")
        self.code_label.setObjectName("codeValue")
        self.code_label.setAlignment(Qt.AlignCenter)
        code_left.addWidget(self.code_label)
        code_hint = QLabel("Telefonda shu kodni kiriting")
        code_hint.setObjectName("hintText")
        code_left.addWidget(code_hint)
        code_lay.addLayout(code_left, 1)

        # ===== QR kod =====
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(160, 160)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet(
            "background: white; border-radius: 12px; padding: 8px;"
        )
        code_lay.addWidget(self.qr_label, 0, Qt.AlignVCenter)

        new_code_btn = make_button("🔄 Yangi kod")
        new_code_btn.clicked.connect(self._new_code)
        code_lay.addWidget(new_code_btn, 0, Qt.AlignVCenter)
        layout.addWidget(code_card)

        hint = QLabel(
            "📱 Telefon kamerasi bilan QR kodni skanerlang —\n"
            "avtomatik ulanadi. Yoki IP manzil + kodni qo'lda kiriting.\n"
            "Birinchi marta Windows ruxsat so'rasa — «Ruxsat berish» bosing."
        )
        hint.setObjectName("hintText")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # ===== Juftlangan telefonlar =====
        dev_title_row = QHBoxLayout()
        dev_title = QLabel("Juftlangan telefonlar")
        dev_title.setObjectName("cardTitle")
        dev_title_row.addWidget(dev_title)
        self.count_pill = QLabel("0")
        self.count_pill.setObjectName("countPill")
        self.count_pill.setAlignment(Qt.AlignCenter)
        dev_title_row.addWidget(self.count_pill)
        dev_title_row.addStretch(1)
        layout.addLayout(dev_title_row)

        self.dev_list = QListWidget()
        self.dev_list.setObjectName("deviceList")
        self.dev_list.setMinimumHeight(120)
        self.dev_list.setMaximumHeight(150)
        layout.addWidget(self.dev_list, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        remove_btn = make_button("🗑 O'chirish", "danger")
        remove_btn.clicked.connect(self._remove_selected)
        close_btn = make_button("Yopish", "ghost")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._reload_devices)
        self._timer.start(3000)

        self._refresh_status()
        self._new_code()
        self._reload_devices()

    def _refresh_status(self) -> None:
        ips = pairing_service.get_local_ips()
        # Eski IP tugmalarini tozalash
        while self.ip_box.count():
            item = self.ip_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if ips:
            self.status_label.setText(
                "Telefon shu manzillardan biriga ulansin "
                "(nusxalash uchun bosing):"
            )
            for ip in ips:
                full = f"{ip}:{pairing_service.SYNC_PORT}"
                chip = make_chip(f"🔗  {full}")
                chip.setStyleSheet("text-align: left; padding-left: 18px;")
                chip.setToolTip("Nusxalash uchun bosing")
                chip.clicked.connect(lambda _=False, f=full: self._copy_ip(chip, f))
                self.ip_box.addWidget(chip)
        else:
            self.status_label.setText(
                "Lokal tarmoq topilmadi. WiFi yoki hotspotga "
                "ulanganingizni tekshiring."
            )
            self.server_dot.setStyleSheet(
                "background-color: #f59e0b; border-radius: 5px; border: none;"
            )
        # QR'ni yangilash (IP o'zgargan bo'lishi mumkin)
        code_text = self.code_label.text().replace(" ", "")
        if code_text and code_text != "————":
            self._update_qr(code_text)

    def _copy_ip(self, chip, full: str) -> None:
        QApplication.clipboard().setText(full)
        original = chip.text()
        chip.setText("✓ Nusxalandi")
        QTimer.singleShot(1400, lambda: chip.setText(original))

    def _new_code(self) -> None:
        try:
            code = pairing_service.generate_code()
            self.code_label.setText(" ".join(code))
            self._update_qr(code)
        except Exception:  # noqa: BLE001
            dialogs.error_from_exception(self, Exception("Kod yaratilmadi"))

    def _update_qr(self, code: str) -> None:
        """QR kod yaratadi: KM|IP:PORT|KOD formatida."""
        ips = pairing_service.get_local_ips()
        if not ips:
            self.qr_label.clear()
            self.qr_label.setToolTip("Tarmoq topilmadi")
            return
        ip = ips[0]
        data = f"KM|{ip}:{pairing_service.SYNC_PORT}|{code}"
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        self.qr_label.setPixmap(
            pixmap.scaled(
                144, 144,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.qr_label.setToolTip(f"Telefon bilan skanerlang:\n{data}")

    def _reload_devices(self) -> None:
        try:
            devices = pairing_service.list_devices()
        except Exception:  # noqa: BLE001
            return
        self.count_pill.setText(str(len(devices)))
        self.dev_list.clear()
        if not devices:
            item = QListWidgetItem("📭  Hali telefon ulanmagan")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.dev_list.addItem(item)
            return
        for d in devices:
            item = QListWidgetItem(
                f"📱  {d['device_name']}   •   {d['paired_display']}"
            )
            item.setData(Qt.UserRole, d["device_id"])
            self.dev_list.addItem(item)

    def _remove_selected(self) -> None:
        item = self.dev_list.currentItem()
        if not item:
            return
        device_id = item.data(Qt.UserRole)
        if not device_id:
            return
        if not dialogs.confirm(
            self,
            "Bu telefonni o'chirishni xohlaysizmi?\n"
            "Qayta ulash uchun kod kerak bo'ladi.",
            ok_text="O'chirish",
        ):
            return
        try:
            pairing_service.remove_device(device_id)
            self._reload_devices()
        except Exception as exc:  # noqa: BLE001
            dialogs.error_from_exception(self, exc)

    def closeEvent(self, event) -> None:
        try:
            self._timer.stop()
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(event)
