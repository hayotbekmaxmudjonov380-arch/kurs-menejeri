# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Windows 8.1 kloni (Qt5)."""

import glob
import os
import sys
from pathlib import Path

project_root = Path(SPECPATH)
icon_path = str(project_root / "assets" / "icon.ico")

# --- CRT + UCRT (Windows 8.0-11 uchun zero-install) ---
py_dir = Path(sys.executable).parent  # D:\Python39
sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"

crt_binaries = [
    (str(py_dir / "vcruntime140.dll"), "."),
    (str(py_dir / "vcruntime140_1.dll"), "."),
    (str(sys32 / "msvcp140.dll"), "."),
    (str(sys32 / "msvcp140_1.dll"), "."),
    (str(sys32 / "msvcp140_2.dll"), "."),
    (str(sys32 / "msvcp140_atomic_wait.dll"), "."),
    (str(sys32 / "msvcp140_codecvt_ids.dll"), "."),
]

# UCRT: api-ms-win-*.dll + ucrtbase.dll
_ucrt_dir = r"C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x64"
if os.path.isdir(_ucrt_dir):
    for _dll in glob.glob(os.path.join(_ucrt_dir, "*.dll")):
        crt_binaries.append((_dll, "."))

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
