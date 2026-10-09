# -*- mode: python ; coding: utf-8 -*-
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
