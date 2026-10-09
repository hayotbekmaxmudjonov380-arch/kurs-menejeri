"""App ikonkasini .ico va .png fayllariga generatsiya qiladi.

Ishga tushirish:
    python tools/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QGuiApplication, QImageWriter, QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent


def build() -> None:
    import sys

    sys.path.insert(0, str(ROOT))
    from utils.branding import make_app_pixmap

    app = QApplication(sys.argv)  # noqa: F841  (pluginlarni yuklash uchun zarur)

    assets = ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    # PNG
    pixmap: QPixmap = make_app_pixmap(256)
    ok_png = pixmap.save(str(assets / "icon.png"))
    # ICO (bir necha o'lchamda)
    ok_ico = pixmap.save(str(assets / "icon.ico"))

    supported = {bytes(f).decode("utf-8") for f in QImageWriter.supportedImageFormats()}
    print("QImageWriter formats:", sorted(supported))
    print("icon.png ->", ok_png)
    print("icon.ico ->", ok_ico)


if __name__ == "__main__":
    build()