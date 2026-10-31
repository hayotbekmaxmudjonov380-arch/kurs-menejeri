# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — bitta fayl (onefile) sifatida build qiladi.

Ishga tushirish:
    pyinstaller KursManager.spec
"""

import os
from pathlib import Path

project_root = Path(SPECPATH)
icon_path = str(project_root / "assets" / "icon.ico")

# VC++ runtime DLLlari — mijoz kompyuterida VC++ Redistributable
# o'rnatilmagan bo'lsa ham dastur ishlasin. PyInstaller tizim
# kutubxonalarini avtomatik chetlab o'tgani uchun qo'lda qo'shiladi
# ("DLL load failed while importing QtGui" xatosining oldini oladi).
_sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
_crt_names = ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll")
crt_binaries = [(str(_sys32 / n), ".") for n in _crt_names if (_sys32 / n).exists()]

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=crt_binaries,
    datas=[(str(project_root / "image" / "logotip.png"), "image")],
    hiddenimports=[
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.sql.default_comparator",
        "reportlab.pdfbase._fontdata",
        "reportlab.lib.fonts",
    ],
    hookspath=[],
    hooksconfig={},
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