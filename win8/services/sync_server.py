"""Desktop ichidagi sinxron server (telefon to'g'ridan-to'g'ri ulanadi).

Stdlib http.server — exe'ga Flask kerak emas. Alohida daemon oqimda ishlaydi.
- /sync/hello — tokensiz (kompyuterni topish)
- /sync/pair — juftlash kodi bilan (token beradi)
- /sync/changes, /sync/push — 6-bosqichda (token shart)
"""

from __future__ import annotations

import json
import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

logger = logging.getLogger(__name__)


class _SyncTCPServer(ThreadingHTTPServer):
    """Band portda ikkinchi nusxa jim ishga tushmasligi uchun.

    Windows'da SO_REUSEADDR buning oldini olmaydi — SO_EXCLUSIVEADDRUSE kerak.
    """

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        try:
            super().__init__(*args, **kwargs)
        except Exception:
            # Bind xato bersa yarim-ochiq soket qolmasligi uchun
            try:
                sock = getattr(self, "socket", None)
                if sock is not None:
                    sock.close()
            except Exception:  # noqa: BLE001
                pass
            raise

    def server_bind(self) -> None:
        # TCPServer.server_bind nusxasi, lekin SO_REUSEADDR siz
        # (u bilan SO_EXCLUSIVEADDRUSE ziddiyatlashadi).
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except OSError:
                pass
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="microseconds")


def _split_path(raw: str) -> tuple[str, dict[str, list[str]]]:
    """`/sync/changes?since=...` -> ("/sync/changes", {"since": [...]})."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(raw or "")
    return parsed.path, parse_qs(parsed.query)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    try:
        length = int(handler.headers.get("Content-Length") or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0 or length > 10 * 1024 * 1024:
        return {}
    try:
        raw = handler.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


class SyncHandler(BaseHTTPRequestHandler):
    server_version = "KursManagerSync/1"
    sys_version = ""

    def log_message(self, *args) -> None:  # noqa: ANN002, ANN003
        logger.debug("Sync HTTP: %s", args[0] % args[1:] if len(args) > 1 else args)

    def _send(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _token_ok(self) -> bool:
        from services import pairing_service as _pair

        token = self.headers.get("X-Device-Token") or ""
        return _pair.verify_token(token.strip())

    def do_GET(self) -> None:  # noqa: N802
        path, query = _split_path(self.path)
        if path == "/sync/hello":
            from version import VERSION

            self._send({"app": "KursManager", "version": VERSION,
                        "sync": 1, "needs_pairing": True,
                        "server_time": _now()})
        elif path == "/sync/changes":
            if not self._token_ok():
                self._send({"error": "Token noto'g'ri — qayta juftlang"}, 401)
                return
            from services import sync_service

            since = query.get("since", [""])[0]
            self._send({
                "changes": sync_service.collect_changes(since),
                "deleted": sync_service.tomb_list(since),
                "server_time": _now(),
            })
        else:
            self._send({"error": "topilmadi"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        path, _query = _split_path(self.path)
        if path == "/sync/pair":
            from services import pairing_service as _pair

            data = _read_json(self)
            token = _pair.confirm_pairing(
                str(data.get("code", "")),
                str(data.get("device_id", "")),
                str(data.get("device_name", "")),
            )
            if token:
                self._send({"ok": True, "token": token})
            else:
                self._send({"ok": False, "error": "Kod noto'g'ri yoki muddati o'tgan"}, 403)
        elif path == "/sync/push":
            if not self._token_ok():
                self._send({"error": "Token noto'g'ri — qayta juftlang"}, 401)
                return
            from services import sync_service

            data = _read_json(self)
            changes = data.get("changes")
            deleted = data.get("deleted")
            stats = sync_service.apply_changes(
                changes if isinstance(changes, list) else [],
                deleted if isinstance(deleted, list) else [],
            )
            sync_service.DATABASE.set_setting("last_sync_at", _now())
            self._send({
                "ok": True,
                "applied": stats["applied"],
                "skipped": stats["skipped"],
                "deleted": stats["deleted"],
                "conflicts": stats["conflicts"],
                "server_time": _now(),
                "last_change_at": sync_service.last_change_at(),
            })
        else:
            self._send({"error": "topilmadi"}, 404)


class SyncServer:
    """8741-portda tinglovchi server (daemon oqim)."""

    def __init__(self, port: int = 8741):
        from services.pairing_service import SYNC_PORT

        self.port = port or SYNC_PORT
        self._server: Any = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    def start(self) -> bool:
        if self.running:
            return True
        try:
            # _SyncTCPServer: port band bo'lsa ikkinchi server
            # jim ishga tushib ketmasligi kerak!
            self._server = _SyncTCPServer(("0.0.0.0", self.port), SyncHandler)
        except OSError:
            logger.exception("Sync server port band: %d", self.port)
            self._server = None
            return False
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True,
            name="sync-server",
        )
        self._thread.start()
        logger.info("Sync server ishga tushdi: 0.0.0.0:%d", self.port)
        return True

    def stop(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:  # noqa: BLE001
                pass
        logger.info("Sync server to'xtatildi")
