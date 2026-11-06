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


def is_forced(info: Optional[dict]) -> bool:
    """Majburiy yangilanish: updates.json dagi min_version joriy versiyadan baland bo'lsa.

    min_version faqat uni tushunadigan versiyalarda (1.3.17+) ishlaydi —
    undan avvalgi eski versiyalar bu maydonni e'tiborsiz qoldiradi va
    odatdagi «yangilanish mavjud» tartibida davom etadi.
    Internet bo'lmasa tekshiruv umuman ishlamaydi — dastur LAN'da
    odatdagidek ochilaveradi (majburiylik faqat serverga ulanganda).
    """
    if not info:
        return False
    min_v = str(info.get("min_version", "")).strip()
    if not min_v:
        return False
    try:
        return parse_version(get_current_version()) < parse_version(min_v)
    except Exception:  # noqa: BLE001
        return False


def _urlopen(req: urllib.request.Request, timeout: int):
    import ssl

    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except Exception as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc) or "certificate verify failed" in str(exc):
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise


def fetch_updates() -> dict:
    url = update_url()
    req = urllib.request.Request(url, headers={"User-Agent": "KursManager-Updater"})
    with _urlopen(req, timeout=CHECK_TIMEOUT) as resp:
        # utf-8-sig: fayl UTF-8 BOM bilan boshlansa ham ishlaydi
        return json.loads(resp.read().decode("utf-8-sig"))


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
            "min_version": str(info.get("min_version", "")),
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
    with _urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
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


# PyInstaller onefile ota jarayon bolaga _MEIPASS ni o'zgaruvchi sifatida
# o'tkazadi. Eski namuna yopilganda _MEI papkasini o'chiradi — agar .bat
# orqali yangi exe shu iflos muhitda ishga tushsa, bootloader o'zini
# "bola" deb olib, o'chirilgan papkadan python DLL izlaydi va
# "Failed to load Python DLL" xatosi bilan yopiladi (kuzatilgan halokat).
_STALE_ENV_PREFIX = "_MEI"
_STALE_ENV_KEYS = ("PYTHONHOME", "PYTHONPATH")


def _is_stale_env_key(key: str) -> bool:
    up = key.upper()
    return up.startswith(_STALE_ENV_PREFIX) or up in _STALE_ENV_KEYS


def _clean_update_env(env: Optional[dict] = None) -> dict:
    """Updater .bat uchun toza muhit (PyInstaller iflos o'zgaruvchilarsiz)."""
    src = dict(os.environ if env is None else env)
    return {k: v for k, v in src.items() if not _is_stale_env_key(k)}


def _build_update_bat(current_exe: str, new_exe_path: str, pid: int) -> str:
    """Almashtiruvchi .bat matnini quradi (sinovdan ajratilgan).

    - WAITLOOP: ilova (va uning ota-bootloaderi) yopilishini kutadi
    - TRYMOVE: exe fayl hali band bo'lsa (ota bootloader _MEI tozalayotganda,
      AV skanerlaganda) 30 soniya davomida har soniyada urinib ko'radi
    - HAR bir `start` dan oldin _MEIPASS/PYTHONHOME/PYTHONPATH tozalanadi —
      aks holda PyInstaller yangi namunani eski "bola" deb olib ishga
      tushmaydi (asosiy tuzatish shu)
    """
    bat = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set PID=%d\r\n"
        'set "NEW=%s"\r\n'
        'set "EXE=%s"\r\n'
        "set TRIES=0\r\n"
        ":WAITLOOP\r\n"
        "tasklist /FI \"PID eq %%PID%%\" 2>NUL | "
        "find /I \"%%PID%%\" >NUL\r\n"
        "if not errorlevel 1 (ping -n 2 127.0.0.1 >NUL & goto WAITLOOP)\r\n"
        'if exist "%%EXE%%.bak" del /F /Q "%%EXE%%.bak"\r\n'
        'copy /Y "%%EXE%%" "%%EXE%%.bak" >NUL\r\n'
        ":TRYMOVE\r\n"
        'move /Y "%%NEW%%" "%%EXE%%" >NUL 2>&1\r\n'
        "if not errorlevel 1 goto MOVED\r\n"
        "set /a TRIES+=1\r\n"
        "if %%TRIES%% GEQ 30 goto MOVEFAIL\r\n"
        "ping -n 2 127.0.0.1 >NUL\r\n"
        "goto TRYMOVE\r\n"
        ":MOVEFAIL\r\n"
        'copy /Y "%%EXE%%.bak" "%%EXE%%" >NUL 2>&1\r\n'
        'set "_MEIPASS="\r\n'
        'set "_MEIPASS2="\r\n'
        'set "PYTHONHOME="\r\n'
        'set "PYTHONPATH="\r\n'
        'start "" "%%EXE%%"\r\n'
        'del "%%~f0"\r\n'
        "exit /b 1\r\n"
        ":MOVED\r\n"
        'del /F /Q "%%EXE%%.bak"\r\n'
        'set "_MEIPASS="\r\n'
        'set "_MEIPASS2="\r\n'
        'set "PYTHONHOME="\r\n'
        'set "PYTHONPATH="\r\n'
        "ping -n 2 127.0.0.1 >NUL\r\n"
        'start "" "%%EXE%%"\r\n'
        'del "%%~f0"\r\n'
    ) % (int(pid), str(new_exe_path), str(current_exe))
    return bat


def launch_updater(
    new_exe_path: str,
    exe_path: Optional[str] = None,
    pid: Optional[int] = None,
) -> bool:
    """Yangi exe'ni almashtiruvchi .bat ni ishga tushiradi.

    Faqat frozen (tayyor exe) rejimda ishlaydi. Muvaffaqiyatda True
    (chaqiruvchi dastur darhol yopilishi kerak).

    exe_path/pid — faqat sinov uchun ustuvor parametrlar (default:
    joriy exe va joriy PID).
    """
    if not getattr(sys, "frozen", False):
        logger.warning("Dev rejimda updater ishlamaydi")
        return False
    current_exe = str(Path(exe_path or sys.executable).resolve())
    if pid is None:
        pid = os.getpid()
    bat_path = Path(tempfile.gettempdir()) / "kurs_manager_update.bat"
    bat = _build_update_bat(current_exe, str(new_exe_path), pid)
    try:
        bat_path.write_text(bat, encoding="utf-8")
    except OSError:
        logger.exception("Updater .bat yozilmadi")
        return False

    env = _clean_update_env()
    ok = False
    try:
        from PySide2.QtCore import QProcess

        # QProcess.startDetached statik metod muhitni qabul qilmaydi —
        # .bat ni ishga tushirguncha iflos o'zgaruvchilarni vaqtinchalik
        # olib tashlaymiz (bat ichidagi `set` bilan dublikat: ikkala
        # qatlam ham mustaqil ishlaydi).
        stale = [k for k in os.environ if _is_stale_env_key(k)]
        saved = {k: os.environ[k] for k in stale}
        for k in stale:
            os.environ.pop(k, None)
        try:
            ok = QProcess.startDetached("cmd.exe", ["/c", str(bat_path)])
        finally:
            os.environ.update(saved)
    except Exception:
        logger.exception("Updater ishga tushmadi (QProcess)")
        ok = False
    if not ok:
        try:
            import subprocess

            subprocess.Popen(
                ["cmd.exe", "/c", str(bat_path)],
                env=env,
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
