"""Masofaviy yangilanish (auto-update) servisi.

Ishlash sxemasi:
1. UPDATE_URL dagi updates.json da har variant uchun versiya + yuklash linki:
   {"win10": {"version": "...", "url": "...", "sha256": "...", "notes": "..."},
    "win8":  {...}}
2. Variant exe nomidan aniqlanadi (KursManager_Win8 -> "win8", aks holda "win10").
3. Yangi versiya topilsa — yuklab, sha256 tekshirib, .bat orqali almashtirib,
   dastur qayta ishga tushadi. Eski exe .bak nusxada qoladi (rollback).
4. Internet bo'lmasa — jim turadi, dastur odatdagidek ishlayveradi.

Faqat standart kutubxona ishlatiladi (Python 3.8+ mos).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# updates.json manzili (o'z GitHub repo'ingizga almashtiring;
# settings jadvalidagi "update_url" bilan ham ustun qilish mumkin).
DEFAULT_UPDATE_URL = (
    "https://raw.githubusercontent.com/hayotbekmaxmudjonov380-arch/"
    "kurs-menejeri/main/updates.json"
)

CHECK_TIMEOUT = 10
DOWNLOAD_TIMEOUT = 120
CHUNK_SIZE = 1024 * 256


def update_url() -> str:
    try:
        from database.database import DATABASE

        custom = DATABASE.get_setting("update_url", "")
        if custom.strip():
            return custom.strip()
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_UPDATE_URL


def get_variant() -> str:
    """Joriy build varianti: 'win8' yoki 'win10'."""
    try:
        from version import VARIANT

        if VARIANT in ("win8", "win10"):
            return VARIANT
    except Exception:  # noqa: BLE001
        pass
    try:
        name = Path(sys.executable).stem.lower() if getattr(sys, "frozen", False) else ""
        if "win8" in name:
            return "win8"
    except Exception:  # noqa: BLE001
        pass
    return "win10"


def get_current_version() -> str:
    try:
        from version import VERSION

        return VERSION
    except Exception:  # noqa: BLE001
        return "0.0.0"


def parse_version(text: str) -> tuple:
    parts = []
    for chunk in str(text).strip().split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(remote: str, current: str) -> bool:
    try:
        return parse_version(remote) > parse_version(current)
    except Exception:  # noqa: BLE001
        return False


def fetch_updates() -> dict:
    url = update_url()
    req = urllib.request.Request(url, headers={"User-Agent": "KursManager-Updater"})
    with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_for_updates() -> Optional[dict]:
    """Yangi versiya bo'lsa info qaytaradi, bo'lmasa None.

    Qaytgan dict: {"version", "url", "sha256", "notes"}.
    Internet/xatolikda None (jim).
    """
    try:
        try:
            data = fetch_updates()
        except Exception as exc:
            logger.debug("Yangilanish serveriga ulanib bo'lmadi: %s", exc)
            return None
        variant = get_variant()
        info = data.get(variant) or {}
        remote_version = str(info.get("version", ""))
        url = str(info.get("url", ""))
        if not remote_version or not url:
            return None
        if not is_newer(remote_version, get_current_version()):
            return None
        return {
            "version": remote_version,
            "url": url,
            "sha256": str(info.get("sha256", "")),
            "notes": str(info.get("notes", "")),
        }
    except Exception:
        logger.exception("Yangilanishni tekshirishda kutilmagan xatolik")
        return None


def download_update(
    url: str,
    dest: str,
    progress_cb: Optional[Callable[[int, int], bool]] = None,
) -> str:
    """Faylni yuklaydi. progress_cb(downloaded, total) False qaytarsa bekor.

    Qaytaradi: saqlangan fayl yo'li. Xatoda exception.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "KursManager-Updater"})
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if progress_cb is not None:
                    if progress_cb(downloaded, total) is False:
                        raise InterruptedError("Yuklash bekor qilindi")
    return dest


def verify_sha256(path: str, expected: str) -> bool:
    if not expected:
        return True
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    ok = actual.lower() == expected.strip().lower()
    if not ok:
        logger.error("SHA256 mos emas: %s != %s", actual, expected)
    return ok


def download_dir() -> Path:
    base = None
    if getattr(sys, "frozen", False):
        try:
            base = Path(sys.executable).resolve().parent
            probe = base / ".write_probe"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
        except OSError:
            base = None
    if base is None:
        base = Path(tempfile.gettempdir()) / "KursManagerUpdate"
        base.mkdir(parents=True, exist_ok=True)
    return base


def launch_updater(new_exe_path: str) -> bool:
    """Yangi exe'ni almashtiruvchi .bat ni ishga tushiradi.

    Faqat frozen (tayyor exe) rejimda ishlaydi. Muvaffaqiyatda True
    (chaqiruvchi dastur darhol yopilishi kerak).
    """
    if not getattr(sys, "frozen", False):
        logger.warning("Dev rejimda updater ishlamaydi")
        return False
    current_exe = str(Path(sys.executable).resolve())
    pid = os.getpid()
    bat_path = Path(tempfile.gettempdir()) / "kurs_manager_update.bat"
    bat = (
        "@echo off\r\n"
        "setlocal\r\n"
        'set "PID=%s"\r\n'
        'set "NEW=%s"\r\n'
        'set "EXE=%s"\r\n'
        ":WAITLOOP\r\n"
        "tasklist /FI \"PID eq %%PID%%\" 2>NUL | "
        "find /I \"%%PID%%\" >NUL\r\n"
        "if not errorlevel 1 (timeout /t 1 /nobreak >NUL & goto WAITLOOP)\r\n"
        'if exist "%%EXE%%.bak" del /F /Q "%%EXE%%.bak"\r\n'
        'copy /Y "%%EXE%%" "%%EXE%%.bak" >NUL\r\n'
        'move /Y "%%NEW%%" "%%EXE%%" >NUL\r\n'
        "if errorlevel 1 (\r\n"
        '  copy /Y "%%EXE%%.bak" "%%EXE%%" >NUL\r\n'
        '  start "" "%%EXE%%"\r\n'
        '  del "%%~f0"\r\n'
        "  exit /b 1\r\n"
        ")\r\n"
        'del /F /Q "%%EXE%%.bak"\r\n'
        'start "" "%%EXE%%"\r\n'
        'del "%%~f0"\r\n'
    ) % (pid, new_exe_path, current_exe)
    try:
        bat_path.write_text(bat, encoding="utf-8")
    except OSError:
        logger.exception("Updater .bat yozilmadi")
        return False
    try:
        from PySide2.QtCore import QProcess

        ok = QProcess.startDetached("cmd.exe", ["/c", str(bat_path)])
    except Exception:
        logger.exception("Updater ishga tushmadi")
        try:
            import subprocess

            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_path)],
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
            )
            ok = True
        except Exception:
            logger.exception("Updater zaxira usulda ham ishlamadi")
            ok = False
    return bool(ok)


def rollback_available() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    bak = str(Path(sys.executable).resolve()) + ".bak"
    return Path(bak).exists()


def current_exe_name() -> str:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).name
    return "KursManager (dev)"


def format_info(info: dict) -> str:
    text = "Yangi versiya mavjud: %s\n" % info.get("version", "")
    notes = (info.get("notes") or "").strip()
    if notes:
        text += "\n%s\n" % notes
    text += "\nHozir yuklab o'rnatilsinmi?"
    return text
