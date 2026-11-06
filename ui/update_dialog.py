"""Yangilanish oynasi — login-form uslubidagi qorong'i dizayn.

Dizayn manbasi (React/styled-components login form):
    - aylanuvchi conic-gradient yorug'lik halqasi
    - #272727 karta, 24px burchak radiusi, ichki yorug' qirralar
    - #3a3a3a "input" panellari (versiya qatorlari)
    - #373737 pill tugmalar, hover'da oq yoqish
    - rgba(255,255,255,0.5) footer havolasi

Ikkala variant (Win10/Qt6 va win8/Qt5) uchun ishlaydi: faqat Qt6/Qt5
import farqi bor, u `tools/port_to_qt5.py` avtomatik almashtiradi.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

# --- CSS o'zgaruvchilaridan ko'chirilgan dizayn konstantalari ---
CARD_COLOR = "#272727"
INPUT_COLOR = "#3a3a3a"
BUTTON_COLOR = "#373737"
NOTES_COLOR = "#2f2f2f"
FOOTER_COLOR = "rgba(255, 255, 255, 0.5)"
DIM_COLOR = "rgba(255, 255, 255, 0.55)"
ACCENT = "#7db0ff"

RIM = 8  # aylanuvchi yorug'lik qalinligi (px)
CARD_RADIUS = 24
OUTER_RADIUS = 32
CARD_PAD = 22  # karta ichki qirqilishi
MARGIN = RIM + CARD_PAD


class _LogoBadge(QFrame):
    """Neumorfik logotip kvadrati (CSS'dagi .logo va uning ::before/::after)."""

    SIZE = 62

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)

        s = float(self.SIZE)
        box = QRectF(3, 3, s - 6, s - 6)

        # soyalar (qorong'i pastga-o'ng, yorug' yuqora-chap)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(box.translated(7, 7), 20, 20)
        p.setBrush(QColor(255, 255, 255, 16))
        p.drawRoundedRect(box.translated(-6, -6), 20, 20)

        # asosiy korpus: gradient + 2px oq ramka
        from PySide6.QtGui import QLinearGradient

        grad = QLinearGradient(box.topLeft(), box.bottomRight())
        grad.setColorAt(0.0, QColor(255, 255, 255, 52))
        grad.setColorAt(1.0, QColor(0, 0, 0, 52))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawRoundedRect(box, 20, 20)

        # glif: ayiruvchi (refresh) ustunali belgi
        cx = s / 2.0
        cy = s / 2.0
        r = 13.0
        p.setPen(QPen(QColor("#ffffff"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush())
        start, sweep = 55.0, 275.0
        p.drawArc(
            QRectF(cx - r, cy - r, r * 2, r * 2),
            int(start * 16),
            int(sweep * 16),
        )

        # strelka: yoyning oxirida (Qt: burchak o'sishi soat yo'nalishi ko'rinadi)
        ang = math.radians(start + sweep)
        ex = cx + r * math.cos(ang)
        ey = cy + r * math.sin(ang)
        tangent = math.atan2(math.cos(ang), -math.sin(ang))
        for off in (math.radians(42), -math.radians(42)):
            hx = ex + 9.0 * math.cos(tangent + math.pi + off)
            hy = ey + 9.0 * math.sin(tangent + math.pi + off)
            p.drawLine(QPointF(ex, ey), QPointF(hx, hy))
        p.end()


class UpdateDialog(QDialog):
    """Dastur yangilanishi oynasi: majburiy (forced) yoki ixtiyoriy rejim."""

    updateRequested = Signal()
    laterRequested = Signal()
    exitRequested = Signal()

    def __init__(
        self,
        parent=None,
        info: dict | None = None,
        forced: bool = False,
        current_version: str = "",
    ):
        super().__init__(parent)
        self.info = info or {}
        self.forced = forced
        self._angle = 45.0
        self._allow_close = False  # majburiy rejimda dastur chiqishi uchun flag

        self.setObjectName("updateDialog")
        self.setWindowTitle("Yangilanish shart" if forced else "Yangilanish mavjud")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        if forced:
            # Yopish tugmasi olib tashlanadi — faqat dialog tugmalari orqali yopiladi
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(430)

        # Kichik ekranda sig'ishi uchun balandlik chegarasi
        try:
            from PySide6.QtWidgets import QApplication

            screen = QApplication.primaryScreen()
            if screen is not None:
                self.setMaximumHeight(int(screen.availableGeometry().height() * 0.94))
        except Exception:  # noqa: BLE001
            pass

        self._build_ui(current_version)

        # Aylanuvchi conic-gradient (4 sekundda bir to'liq aylanish)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._spin)
        self._timer.start()
        self.finished.connect(self._timer.stop)

    # ---------- dizayn ----------
    def _spin(self) -> None:
        self._angle = (self._angle + 3.6) % 360.0
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)

        whole = QRectF(self.rect())
        p.setBrush(QColor("#101419"))
        p.drawRect(whole)

        outer = whole.adjusted(0.5, 0.5, -0.5, -0.5)

        # conic-gradient: transparent 62% -> oq nurga -> transparent
        grad = QConicalGradient(outer.center(), self._angle)
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.62, QColor(255, 255, 255, 0))
        grad.setColorAt(0.80, QColor(255, 255, 255, 70))
        grad.setColorAt(0.92, QColor(255, 255, 255, 255))
        grad.setColorAt(0.97, QColor(255, 255, 255, 190))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(outer, OUTER_RADIUS, OUTER_RADIUS)

        card = outer.adjusted(RIM, RIM, -RIM, -RIM)
        p.setBrush(QColor(CARD_COLOR))
        p.setPen(QPen(QColor(255, 255, 255, 36), 1))
        p.drawRoundedRect(card, CARD_RADIUS, CARD_RADIUS)
        p.end()

    # ---------- UI ----------
    @staticmethod
    def _dim_style(size: int = 13, bold: bool = False) -> str:
        return (
            "color: %s; background: transparent; border: none;"
            "font-size: %dpx; font-weight: %s;"
            % (DIM_COLOR, size, "700" if bold else "400")
        )

    def _version_row(self, label: str, value: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background-color: %s; border-radius: 12px; }" % INPUT_COLOR
        )
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 9, 14, 9)
        lay.setSpacing(8)

        left = QLabel(label)
        left.setStyleSheet(self._dim_style(13))
        right = QLabel(value)
        right.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;"
            "font-size: 14px; font-weight: 700;"
        )
        right.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(left)
        lay.addStretch(1)
        lay.addWidget(right)
        return row

    def _build_ui(self, current_version: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(11)

        def centered(widget) -> None:
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(widget)
            row.addStretch(1)
            layout.addLayout(row)

        logo = _LogoBadge()
        centered(logo)

        title = QLabel(
            "Yangilanish shart" if self.forced else "Yangilanish mavjud"
        )
        title.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;"
            "font-size: 23px; font-weight: 800;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        centered(title)

        sub = QLabel(
            "Ilovaning eski versiyasi ishlamaydi."
            if self.forced
            else "Yangi versiya tayyorlab qo'yildi."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(self._dim_style(13))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addWidget(self._version_row("Joriy versiya", "v%s" % current_version))
        layout.addWidget(
            self._version_row("Yangi versiya", "v%s" % self.info.get("version", ""))
        )

        notes = (self.info.get("notes") or "").strip()
        if notes:
            box = QFrame()
            box.setStyleSheet(
                "QFrame { background-color: %s; border-radius: 12px; }" % NOTES_COLOR
            )
            box_lay = QVBoxLayout(box)
            box_lay.setContentsMargins(14, 11, 14, 11)
            text = QLabel(notes)
            text.setWordWrap(True)
            text.setStyleSheet(self._dim_style(13))
            box_lay.addWidget(text)
            layout.addWidget(box)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            "color: %s; background: transparent; border: none;"
            "font-size: 13px; font-weight: 600;" % ACCENT
        )
        self.status.setVisible(False)
        layout.addWidget(self.status)

        self.btn_update = QPushButton("Yangilash")
        self._style_button(self.btn_update, primary=True)
        self.btn_update.clicked.connect(self.updateRequested.emit)
        layout.addWidget(self._button_row(self.btn_update))

        self.btn_secondary = QPushButton("Chiqish" if self.forced else "Keyinroq")
        self._style_button(self.btn_secondary, primary=False)
        self.btn_secondary.clicked.connect(self._on_secondary)
        layout.addWidget(self._button_row(self.btn_secondary))

        footer = QLabel(
            "Yangilanish tarixi va tafsilotlari: "
            '<a href="https://github.com/hayotbekmaxmudjonov380-arch/'
            'kurs-menejeri/releases" '
            'style="color: %s; text-decoration: none; font-weight: 600;">'
            "GitHub'da ko'rish</a>" % FOOTER_COLOR
        )
        footer.setWordWrap(True)
        footer.setOpenExternalLinks(True)
        footer.setTextFormat(Qt.TextFormat.RichText)
        footer.setStyleSheet(
            "color: %s; background: transparent; border: none; font-size: 12px;"
            % FOOTER_COLOR
        )
        layout.addWidget(footer)

    @staticmethod
    def _style_button(btn: QPushButton, primary: bool) -> None:
        if primary:
            bg = (
                "qlineargradient(x1:0, y1:0, x2:0, y2:1,"
                " stop:0 #434343, stop:1 #373737)"
            )
            border = "1px solid rgba(255, 255, 255, 0.30)"
            color = "#ffffff"
            hover = "rgba(255, 255, 255, 0.25)"
        else:
            bg = "transparent"
            border = "1px solid rgba(255, 255, 255, 0.16)"
            color = FOOTER_COLOR
            hover = "rgba(255, 255, 255, 0.10)"

        btn.setFixedHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            "  background-color: %s;"
            "  color: %s;"
            "  border: %s;"
            "  border-radius: 22px;"
            "  font-size: 14px;"
            "  font-weight: 700;"
            "  padding: 0 18px;"
            "}"
            "QPushButton:hover { background-color: %s; border-color: rgba(255,255,255,0.55); }"
            "QPushButton:pressed { background-color: rgba(255, 255, 255, 0.14); }"
            "QPushButton:disabled { color: rgba(255, 255, 255, 0.30); }"
            % (bg, color, border, hover)
        )

    @staticmethod
    def _button_row(btn: QPushButton) -> QFrame:
        """Tugmani to'liq kenglikda markazlash (kartaning ichki qirqilishi)."""
        wrap = QFrame()
        wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(btn)
        return wrap

    def _on_secondary(self) -> None:
        if self.forced:
            self._allow_close = True
            self.exitRequested.emit()
        else:
            self.laterRequested.emit()
            self.reject()

    # ---------- holat ----------
    def set_status(self, text: str) -> None:
        self.status.setText(text or "")
        self.status.setVisible(bool(text))

    def set_busy(self, busy: bool) -> None:
        self.btn_update.setEnabled(not busy)
        self.btn_secondary.setEnabled(not busy)
        self.btn_update.setText("Yuklanmoqda..." if busy else "Yangilash")

    def reject(self) -> None:
        """Majburiy rejimda Escape/Cancel bilan yopib bo'lmaydi."""
        if self.forced:
            return
        self._timer.stop()
        super().reject()

    def done(self, code) -> None:
        self._timer.stop()
        super().done(code)

    def closeEvent(self, event) -> None:
        if self.forced and not self._allow_close:
            # Alt+F4 orqali ham chiqib ketishga yo'l qo'ymaymiz
            event.ignore()
            return
        self._timer.stop()
        super().closeEvent(event)
