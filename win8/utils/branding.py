"""Dastur ikonkasi — image/logotip.png (topilmasa chizilgan zaxira)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide2.QtCore import QRectF, Qt
from PySide2.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap

from ui.theme import PRIMARY


def logo_path() -> Path:
    """Logotip fayl yo'li (exe ichida ham ishlaydi)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled = base / "image" / "logotip.png"
        if bundled.exists():
            return bundled
        return Path(sys.executable).parent / "image" / "logotip.png"
    return Path(__file__).resolve().parent.parent / "image" / "logotip.png"


def make_app_pixmap(size: int = 128) -> QPixmap:
    path = logo_path()
    if path.exists():
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            return pixmap.scaled(
                size, size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
    return _draw_fallback(size)


def _draw_fallback(size: int = 128) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    margin = size * 0.06
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#3b82f6"))
    gradient.setColorAt(1.0, QColor("#1e3a8a"))
    painter.setBrush(gradient)
    painter.setPen(QColor("#60a5fa"))
    painter.drawRoundedRect(rect, size * 0.22, size * 0.22)

    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", int(size * 0.55), QFont.Bold)
    painter.setFont(font)
    painter.drawText(rect, Qt.AlignCenter, "K")

    painter.end()
    return pixmap


def make_app_icon() -> QIcon:
    return QIcon(make_app_pixmap(128))