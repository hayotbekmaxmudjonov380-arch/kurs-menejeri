"""Telefon ulash (bir martalik juftlash + token)."""

from __future__ import annotations

import logging
import secrets
import socket
from datetime import datetime, timedelta
from typing import Any

from database.database import DATABASE
from database.models import TrustedDevice

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 5
SYNC_PORT = 8741


def _get_int_setting(key: str, default: int = 0) -> int:
    try:
        return int(DATABASE.get_setting(key, str(default)))
    except (TypeError, ValueError):
        return default


def generate_code() -> str:
    """4 xonali juftlash kodi (5 daqiqa amal qiladi)."""
    code = "%04d" % secrets.randbelow(10000)
    expires = datetime.now() + timedelta(minutes=CODE_TTL_MINUTES)
    DATABASE.set_setting("pair_code", code)
    DATABASE.set_setting("pair_expires", str(int(expires.timestamp())))
    return code


def _code_valid(code: str) -> bool:
    saved = DATABASE.get_setting("pair_code", "")
    if not saved or str(code).strip() != saved:
        return False
    exp = _get_int_setting("pair_expires", 0)
    try:
        if datetime.now() > datetime.fromtimestamp(exp):
            return False
    except (OSError, OverflowError, ValueError):
        return False
    return True


def _clear_code() -> None:
    DATABASE.set_setting("pair_code", "")
    DATABASE.set_setting("pair_expires", "0")


def confirm_pairing(code: str, device_id: str, device_name: str = "") -> str | None:
    """Kod to'g'ri bo'lsa token qaytaradi (qurilma eslab qolinadi)."""
    device_id = (device_id or "").strip()
    if not device_id or not _code_valid(code):
        return None
    token = secrets.token_hex(32)
    with DATABASE.session() as s:
        row = s.query(TrustedDevice).filter(TrustedDevice.device_id == device_id).first()
        if row:
            row.device_name = (device_name or "").strip()[:150]
            row.token = token
            row.paired_at = datetime.now()
        else:
            s.add(TrustedDevice(
                device_id=device_id,
                device_name=(device_name or "").strip()[:150],
                token=token,
            ))
    _clear_code()
    logger.info("Qurilma juftlandi: %s", device_id)
    return token


def verify_token(token: str) -> bool:
    if not token:
        return False
    with DATABASE.session() as s:
        return (
            s.query(TrustedDevice).filter(TrustedDevice.token == token).first()
            is not None
        )


def list_devices() -> list[dict[str, Any]]:
    with DATABASE.session() as s:
        rows = s.query(TrustedDevice).order_by(TrustedDevice.paired_at.desc()).all()
        return [
            {
                "id": r.id,
                "device_id": r.device_id,
                "device_name": r.device_name or r.device_id,
                "paired_at": r.paired_at,
                "paired_display": r.paired_at.strftime("%d.%m.%Y %H:%M") if r.paired_at else "—",
            }
            for r in rows
        ]


def remove_device(device_id: str) -> bool:
    with DATABASE.session() as s:
        row = s.query(TrustedDevice).filter(TrustedDevice.device_id == device_id).first()
        if not row:
            return False
        s.delete(row)
        return True


def get_local_ips() -> list[str]:
    """Kompyuterning lokal IP manzillari (telefonga ko'rsatish uchun)."""
    ips: set[str] = set()
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            ips.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass
    return sorted(ips)
