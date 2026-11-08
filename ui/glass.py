"""Shisha (glassmorphism) yordamchilari — web bilan BIR XIL ko'rinish uchun.

Tokenlar web/templates/base.html :root dan olingan (`--glass-*`, `--bg`).

Nega qo'lda?
    Qt'da CSS `backdrop-filter` yo'q. Shuning uchun:
      1) fon (`--bg` + body::before/body::after radial glow) bir marta
         QPixmap'ga chiziladi;
      2) u `blur(12px) saturate(180%) contrast(200%)` dan o'tkaziladi;
      3) har bir shisha panel o'z ORTIDAGI fon qismini shu rasm'dan
         ko'chiradi, tepasiga `rgba` rangli qatlam + ichki yorug'lik
         (`--glass-edge`) chizadi.
    Natija — haqiqiy backdrop-blur: panel fonning o'zini ko'raydi.

Eslatma: tashqi drop-shadow chizilmaydi — child widget o'z chegarasidan
tashqariga bo'ya olmaydi (Qt kliplaydi), shuning uchun chuqurlik
`--glass-edge` ichki yorug'ligi + 1px `--glass-line` bilan beriladi.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QFrame,
    QWidget,
)

try:
    import numpy as _np
except Exception:  # noqa: BLE001
    _np = None


# ---------------------------------------------------------------------------
# base.html :root
# ---------------------------------------------------------------------------
PAD = 44
BLUR_PX = 12.0
SAT = 1.8
CON = 2.0

_BG = {"dark": "#080d19", "light": "#eef2f8"}
# body::before / body::after / uchinchi nur (ikkala mavzuda bir xil)
_GLOWS = (
    (110.0, 140.0, 230.0, (43, 127, 255, 87)),   # body::before
    (-100.0, 380.0, 250.0, (0, 122, 255, 56)),   # body::after
)


def _is_light() -> bool:
    try:
        from ui import theme

        return theme.current_theme() == "light"
    except Exception:  # noqa: BLE001
        return False


def tokens() -> dict[str, QColor]:
    """Joriy mavzuning glass tokenlari (base.html bilan bir xil qiymatlar)."""
    if _is_light():
        return {
            "bg": QColor(_BG["light"]),
            "surface": QColor(255, 255, 255, 140),   # --glass-surface  .55
            "surface2": QColor(255, 255, 255, 191),  # --glass-surface-2 .75
            "line": QColor(9, 22, 44, 31),           # --glass-line      .12
            "blue": QColor(0, 122, 255, 103),        # --glass-blue     .404
            "border": QColor(9, 22, 44, 41),         # --glass-border    .16
            "hi": QColor("#0d3f91"),                 # --glass-hi
            "on": QColor(9, 22, 44, 230),            # --glass-on         .9
            "edge": 150,                             # ichki yorug'lik kuchi
        }
    return {
        "bg": QColor(_BG["dark"]),
        "surface": QColor(255, 255, 255, 18),       # --glass-surface   .07
        "surface2": QColor(255, 255, 255, 31),      # --glass-surface-2 .12
        "line": QColor(255, 255, 255, 36),          # --glass-line      .14
        "blue": QColor(0, 122, 255, 103),           # --glass-blue     .404
        "border": QColor(255, 255, 255, 46),        # --glass-border    .18
        "hi": QColor("#06214d"),                    # --glass-hi
        "on": QColor(255, 255, 255, 230),           # --glass-on         .9
        "edge": 100,                                # ichki yorug'lik kuchi
    }


# ---------------------------------------------------------------------------
# Fon (+ backdrop)
# ---------------------------------------------------------------------------
_cache: dict[tuple, tuple[QPixmap, QImage]] = {}
_MAX_ENTRIES = 3


def invalidate() -> None:
    """Mavzu o'zgarganda chaqiriladi — fonni qayta qurish uchun."""
    _cache.clear()


def blur_pixmap(src: QPixmap, radius: float) -> QPixmap:
    if radius <= 0:
        return src
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(src)
    eff = QGraphicsBlurEffect()
    eff.setBlurRadius(radius)
    item.setGraphicsEffect(eff)
    scene.addItem(item)
    scene.setSceneRect(QRectF(src.rect()))
    out = QImage(src.size(), QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(p)
    p.end()
    return QPixmap.fromImage(out)


def apply_backdrop(src: QPixmap) -> QImage:
    """CSS: blur(12px) saturate(180%) contrast(200%)"""
    img = blur_pixmap(src, BLUR_PX).toImage().convertToFormat(
        QImage.Format.Format_ARGB32
    )
    if _np is None:
        return img
    try:
        h, w = img.height(), img.width()
        row = _np.frombuffer(img.bits(), _np.uint8).reshape(h, img.bytesPerLine())
        chunk = _np.ascontiguousarray(row[:, : w * 4]).reshape(h, w, 4)
        rgb = chunk[:, :, :3].astype(_np.float32)
        rgb = (rgb - 128.0) * CON + 128.0
        lum = rgb @ _np.array([0.2126, 0.7152, 0.0722], _np.float32)
        rgb = lum[..., None] + (rgb - lum[..., None]) * SAT
        chunk[:, :, :3] = _np.clip(rgb, 0, 255).astype(_np.uint8)
        # QImage(data, ...) tashqi xotirani KO'ZLAYDI (nusxalamaydi).
        # `data` lokal o'zgaruvchida saqlanadi va copy() shu vaqtda
        # bajariladi — aks holda PySide2 da use-after-free crash bo'ladi.
        data = chunk.tobytes()
        out = QImage(data, w, h, w * 4, QImage.Format.Format_ARGB32)
        if out.isNull():
            return img
        return out.copy()
    except Exception:  # noqa: BLE001
        return img


def _radial(p: QPainter, cx: float, cy: float, r: float, rgba) -> None:
    c = QColor(*rgba)
    g = QRadialGradient(QPointF(cx, cy), r)
    g.setColorAt(0.0, c)
    g.setColorAt(0.55, QColor(c.red(), c.green(), c.blue(), c.alpha() // 2))
    g.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
    p.setBrush(g)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(cx, cy), r, r)


def _get(w: int, h: int) -> tuple[QPixmap, QImage]:
    w, h = max(2, int(w)), max(2, int(h))
    key = (w, h, "light" if _is_light() else "dark")
    hit = _cache.get(key)
    if hit is not None:
        return hit

    bg_color = tokens()["bg"]
    raw = QImage(w + 2 * PAD, h + 2 * PAD, QImage.Format.Format_ARGB32_Premultiplied)
    raw.fill(bg_color)
    p = QPainter(raw)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for cx, cy, r, rgba in _GLOWS:
        _radial(p, PAD + (cx if cx >= 0 else w + cx), PAD + cy, r, rgba)
    # uchinchi nur — o'ng past
    _radial(p, PAD + w - 260, PAD + h + 40, 300, (29, 78, 216, 46))
    p.end()

    blur_full = apply_backdrop(QPixmap.fromImage(raw))
    bg_crop = QPixmap.fromImage(raw).copy(PAD, PAD, w, h)
    blur_crop = blur_full.copy(PAD, PAD, w, h)
    out = (bg_crop, blur_crop)

    if len(_cache) >= _MAX_ENTRIES:
        _cache.pop(next(iter(_cache)))
    _cache[key] = out
    return out


def paint_background(p: QPainter, w: int, h: int) -> None:
    """Butun oyna foni — body + radial glow'lar."""
    bg, _ = _get(w, h)
    p.drawPixmap(0, 0, bg)


def _sample(blur: QImage, wr: QRect) -> tuple[QImage | None, QPoint]:
    bw, bh = blur.width(), blur.height()
    x0, y0 = max(0, wr.x()), max(0, wr.y())
    x1, y1 = min(bw, wr.right() + 1), min(bh, wr.bottom() + 1)
    if x1 <= x0 or y1 <= y0:
        return None, QPoint(0, 0)
    return blur.copy(x0, y0, x1 - x0, y1 - y0), QPoint(x0 - wr.x(), y0 - wr.y())


# ---------------------------------------------------------------------------
# Shisha panel
# ---------------------------------------------------------------------------
def paint_glass(
    p: QPainter,
    widget: QWidget,
    rect,
    radius: float,
    tint: QColor,
    border: QColor,
    highlight: float = 1.0,
    backdrop: bool = True,
) -> None:
    """`rect` (widget koordinatalarida) ichiga shisha panel chizadi.

    Orqadagi fon oynaning umumiy backdrop rasm'dan olinadi.
    """
    if isinstance(rect, QRectF):
        rect_f = rect
        rect_i = QRect(rect.x(), rect.y(), rect.width(), rect.height())
    else:
        rect_i = QRect(int(rect.x()), int(rect.y()),
                       int(rect.width()), int(rect.height()))
        rect_f = QRectF(rect_i)

    tk = tokens()
    win = widget.window()
    origin = widget.mapTo(win, rect_i.topLeft())
    wr = QRect(origin, rect_i.size())

    p.save()
    path = QPainterPath()
    path.addRoundedRect(rect_f, radius, radius)
    p.setClipPath(path, Qt.ClipOperation.IntersectClip)

    if backdrop:
        _, blur = _get(win.width(), win.height())
        img, off = _sample(blur, wr)
        if img is not None:
            p.drawImage(rect_i.topLeft() + off, img)

    # rgba rangli qatlam
    p.fillRect(rect_i, tint)

    # --glass-edge: chap-yuqoridan oq yorug'lik, o'ng-pastdan yengilroq
    strength = tk["edge"] / 100.0
    g = QLinearGradient(QPointF(rect_f.left(), rect_f.top()),
                        QPointF(rect_f.right(), rect_f.bottom()))
    g.setColorAt(0.0, QColor(255, 255, 255, int(40 * highlight * strength)))
    g.setColorAt(0.45, QColor(255, 255, 255, 0))
    g.setColorAt(1.0, QColor(255, 255, 255, int(26 * highlight * strength)))
    p.fillRect(rect_i, g)

    # yuqori qirra (inset 0 -2px 0 rgba(255,255,255,.2))
    g2 = QLinearGradient(QPointF(rect_f.left(), rect_f.top()),
                         QPointF(rect_f.left(), rect_f.top() + 9))
    g2.setColorAt(0.0, QColor(255, 255, 255, int(70 * highlight * strength)))
    g2.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(QRect(rect_i.left(), rect_i.top(), rect_i.width(), 9), g2)
    p.restore()

    # 1px chegara (--glass-line / --glass-border)
    pen = QPen(border, 1)
    pen.setCosmetic(True)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(rect_f.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


# ---------------------------------------------------------------------------
# Tayyor vidjetlar
# ---------------------------------------------------------------------------
class GlassRoot(QWidget):
    """Markaziy widget — shisha foni (body + glow) chizadi."""

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_background(p, self.width(), self.height())
        p.end()


class GlassFrame(QFrame):
    """O'z chegarasi ichida shisha panel chizadigan QFrame.

    QSS fon/borderni chizmaydi (super() chaqirilmaydi) — shisha o'zi chizadi.
    """

    radius = 32
    inset = 10
    tint_key = "blue"
    border_key = "border"
    highlight = 1.15

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tk = tokens()
        rect = QRect(self.inset, self.inset,
                     max(1, self.width() - 2 * self.inset),
                     max(1, self.height() - 2 * self.inset))
        paint_glass(
            p, self, rect, self.radius,
            tk[self.tint_key], tk[self.border_key],
            highlight=self.highlight,
        )
        p.end()
