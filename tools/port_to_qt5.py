"""Asosiy koddan Windows 8.1 klonini generatsiya qiladi (PySide6 -> PySide2/Qt5).

Ishga tushirish (asosiy Python bilan):
    python tools/port_to_qt5.py

Natija: win8/ papkada Qt5-mos kod + KursManager_Win8.spec
Keyin Python 3.9 bilan build:
    D:\\Python39\\python.exe -m PyInstaller win8/KursManager_Win8.spec --noconfirm
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "win8"

COPY_FILES = [
    "main.py",
    "version.py",
    "database/__init__.py",
    "database/database.py",
    "database/models.py",
    "services/__init__.py",
    "services/student_service.py",
    "services/course_service.py",
    "services/payment_service.py",
    "services/report_service.py",
    "services/backup_service.py",
    "services/demo_data.py",
    "services/test_service.py",
    "services/reminder_service.py",
    "services/attendance_service.py",
    "services/group_service.py",
    "services/monthly_payment_service.py",
    "services/due_service.py",
    "services/update_service.py",
    "services/activity_service.py",
    "services/pairing_service.py",
    "services/sync_server.py",
    "services/sync_service.py",
    "ui/__init__.py",
    "ui/theme.py",
    "ui/widgets.py",
    "ui/dialogs.py",
    "ui/main_window.py",
    "ui/phone_dialog.py",
    "ui/dashboard.py",
    "ui/groups.py",
    "ui/students.py",
    "ui/payments.py",
    "ui/tests.py",
    "ui/attendance.py",
    "ui/reminders.py",
    "ui/reports.py",
    "ui/courses.py",
    "ui/settings.py",
    "utils/__init__.py",
    "utils/validators.py",
    "utils/logging_config.py",
    "utils/branding.py",
]

# (pattern, replacement) — tartib muhim!
REPLACEMENTS = [
    # Importlar
    (r"from PySide6\.QtGui import QAction, ", "from PySide6.QtWidgets.QAction import QAction\nfrom PySide6.QtGui import "),
    (r"from PySide6\.QtGui import QAction", "from PySide6.QtWidgets.QAction import QAction"),
    (r"from PySide6(\.|$)", r"from PySide2\1"),
    (r"import PySide6(\.|$)", r"import PySide2\1"),
    # QAction alohida import qilingan joylar (funksiya ichida)
    # Qt scoped enumlar -> Qt5 uslubi
    (r"Qt\.AlignmentFlag\.AlignCenter", "Qt.AlignCenter"),
    (r"Qt\.AlignmentFlag\.AlignRight", "Qt.AlignRight"),
    (r"Qt\.AlignmentFlag\.AlignVCenter", "Qt.AlignVCenter"),
    (r"Qt\.AlignmentFlag\.AlignLeft", "Qt.AlignLeft"),
    (r"Qt\.ItemDataRole\.UserRole", "Qt.UserRole"),
    (r"Qt\.ItemFlag\.ItemIsEditable", "Qt.ItemIsEditable"),
    (r"Qt\.FocusPolicy\.NoFocus", "Qt.NoFocus"),
    (r"Qt\.CursorShape\.PointingHandCursor", "Qt.PointingHandCursor"),
    (r"Qt\.AspectRatioMode\.KeepAspectRatio", "Qt.KeepAspectRatio"),
    (r"Qt\.TransformationMode\.SmoothTransformation", "Qt.SmoothTransformation"),
    (r"Qt\.PenStyle\.NoPen", "Qt.NoPen"),
    (r"Qt\.TextInteractionFlag\.TextSelectableByMouse", "Qt.TextSelectableByMouse"),
    (r"Qt\.WidgetAttribute\.WA_TransparentForMouseEvents", "Qt.WA_TransparentForMouseEvents"),
    (r"Qt\.InputMethodHint\.ImhFormattedNumbersOnly", "Qt.ImhFormattedNumbersOnly"),
    (r"Qt\.GlobalColor\.transparent", "Qt.transparent"),
    (r"QAbstractItemView\.EditTrigger\.NoEditTriggers", "QAbstractItemView.NoEditTriggers"),
    (r"QAbstractItemView\.SelectionBehavior\.SelectRows", "QAbstractItemView.SelectRows"),
    (r"QAbstractItemView\.SelectionMode\.SingleSelection", "QAbstractItemView.SingleSelection"),
    (r"QHeaderView\.ResizeMode\.Interactive", "QHeaderView.Interactive"),
    (r"QFont\.Weight\.Bold", "QFont.Bold"),
    (r"QColor\.NameFormat\.HexArgb", "QColor.HexArgb"),
    (r"QPainter\.RenderHint\.Antialiasing", "QPainter.Antialiasing"),
    (r"QSystemTrayIcon\.MessageIcon\.Information", "QSystemTrayIcon.Information"),
    (r"QEvent\.Type\.FocusIn", "QEvent.FocusIn"),
    (r"QEvent\.Type\.FocusOut", "QEvent.FocusOut"),
    (r"QEvent\.Type\.Resize", "QEvent.Resize"),
    (r"QMessageBox\.Icon\.Warning", "QMessageBox.Warning"),
    (r"QMessageBox\.ButtonRole\.AcceptRole", "QMessageBox.AcceptRole"),
    (r"QMessageBox\.ButtonRole\.RejectRole", "QMessageBox.RejectRole"),
    (r"QMessageBox\.StandardButton\.Yes", "QMessageBox.Yes"),
    (r"QMessageBox\.StandardButton\.No", "QMessageBox.No"),
    (r"QDialog\.DialogCode\.Accepted", "QDialog.Accepted"),
    # app.exec() -> app.exec_() (PySide2)
    (r"return app\.exec\(\)", "return app.exec_()"),
    # QMenu.exec() Qt5 da yo'q -> exec_() (QDialog.exec() esa Qt5 da bor, tegilmaydi)
    (r"menu\.exec\(", "menu.exec_("),
]

MODELS_FIXES = [
    ("from datetime import datetime",
     "from datetime import datetime\nfrom typing import Optional"),
    ("Mapped[int | None]", "Mapped[Optional[int]]"),
    ('Mapped["Course | None"]', 'Mapped[Optional["Course"]]'),
    ('Mapped["Student"]', 'Mapped["Student"]'),
]


def port_text(text: str, is_models: bool = False) -> str:
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    if is_models:
        for old, new in MODELS_FIXES:
            text = text.replace(old, new)
    return text


def fix_qaction_imports(text: str) -> str:
    """QAction QtWidgets'dan import qilinishi kerak (Qt5)."""
    # "from PySide2.QtWidgets.QAction import QAction" xatoni to'g'rilash:
    text = text.replace(
        "from PySide2.QtWidgets.QAction import QAction",
        "from PySide2.QtWidgets import QAction",
    )
    # Bitta qatordagi "from PySide2.QtGui import QAction, X" ni ajratish:
    lines = text.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from PySide2.QtGui import ") and "QAction" in stripped:
            indent = line[: len(line) - len(line.lstrip())]
            rest = stripped[len("from PySide2.QtGui import "):]
            parts = [p.strip() for p in rest.split(",")]
            parts = [p for p in parts if p != "QAction"]
            out.append(f"{indent}from PySide2.QtWidgets import QAction")
            if parts:
                out.append(f"{indent}from PySide2.QtGui import {', '.join(parts)}")
        else:
            out.append(line)
    return "\n".join(out)


def build() -> Path:
    if DEST.exists():
        shutil.rmtree(DEST)
    for rel in COPY_FILES:
        src = ROOT / rel.replace("/", "\\")
        dst = DEST / rel.replace("/", "\\")
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        text = port_text(text, is_models=(src.name == "models.py"))
        text = fix_qaction_imports(text)
        # Qolgan PySide6 qoldiqlari bo'lmasligi kerak
        assert "PySide6" not in text, f"PySide6 qoldi: {rel}"
        dst.write_text(text, encoding="utf-8")

    # image/ va assets/ nusxalash (logo + icon)
    for folder in ("image", "assets"):
        src = ROOT / folder
        if src.exists():
            shutil.copytree(src, DEST / folder)

    # requirements-win8.txt
    (DEST / "requirements-win8.txt").write_text(
        "PySide2==5.15.2.1\nSQLAlchemy>=2.0,<3\nPyInstaller>=5.0,<7\nreportlab>=3.5,<5\n",
        encoding="utf-8",
    )

    # KursManager_Win8.spec
    spec = f'''# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Windows 8.1 kloni (Qt5)."""

from pathlib import Path

project_root = Path(SPECPATH)
icon_path = str(project_root / "assets" / "icon.ico")

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "image" / "logotip.png"), "image")],
    hiddenimports=[
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.sql.default_comparator",
        "reportlab.pdfbase._fontdata",
        "reportlab.lib.fonts",
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="KursManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
'''
    (DEST / "KursManager_Win8.spec").write_text(spec, encoding="utf-8")

    # win8 nusxada variantni qotirish (exe nomi universal bo'lganda ham ishlaydi)
    version_file = DEST / "version.py"
    if version_file.exists():
        text = version_file.read_text(encoding="utf-8")
        text = text.replace('VARIANT = "win10"', 'VARIANT = "win8"')
        if 'VARIANT = "win8"' not in text:
            text += '\nVARIANT = "win8"\n'
        version_file.write_text(text, encoding="utf-8")

    # exe alohida papkaga chiqishi uchun: build/dist-win8
    print(f"win8/ tayyor: {DEST}")
    return DEST


if __name__ == "__main__":
    build()
