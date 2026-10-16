"""Asosiy oyna: sidebar + sahifalar."""

from __future__ import annotations

import logging

from PySide2.QtCore import Qt, QTimer, Signal
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGraphicsBlurEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ui.attendance import AttendancePage
from ui.dashboard import DashboardPage
from ui.groups import GroupsPage
from ui.payments import PaymentsPage
from ui.reminders import RemindersPage
from ui.reports import ReportsPage
from ui.students import StudentsPage
from ui.tests import TestsPage
from ui import theme
from utils.branding import logo_path, make_app_icon

logger = logging.getLogger(__name__)


class NavButton(QPushButton):
    """Hover'da yon tugmalarni blur qilish uchun signal chiqaradi."""

    hovered = Signal(bool)

    def enterEvent(self, event) -> None:
        self.hovered.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hovered.emit(False)
        super().leaveEvent(event)

NAV_ITEMS = [
    ("dashboard", "🏠  Bosh sahifa"),
    ("students", "👥  O'quvchilar"),
    ("groups", "🗂  Guruhlar"),
    ("payments", "💳  To'lovlar"),
    ("tests", "📝  Test natijalari"),
    ("attendance", "📅  Davomat"),
    ("reminders", "🔔  Eslatmalar"),
    ("reports", "📊  Hisobotlar"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kurs Manager")
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(1180, 720)
        self.resize(1320, 800)

        self.pages: dict[str, QWidget] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        self.tray: QSystemTrayIcon | None = None
        self._build_ui()
        self._connect_signals()
        self._setup_notifications()
        self._setup_auto_update()
        self._start_sync_server()

        # Har bir sahifadagi o'zgarishlarni barcha sahifalarga tarqatish
        for page in self.pages.values():
            if hasattr(page, "data_changed"):
                page.data_changed.connect(self.refresh_all)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("pageRoot")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------- Sidebar ----------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 14)
        sidebar_layout.setSpacing(6)

        title = QLabel()
        logo_pix = QPixmap(str(logo_path()))
        if not logo_pix.isNull():
            title.setPixmap(
                logo_pix.scaledToWidth(
                    200, Qt.SmoothTransformation
                )
            )
        else:
            title.setText("Kurs Manager")
            title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)
        sidebar_layout.addSpacing(14)

        nav_box = QFrame()
        nav_box.setObjectName("navBox")
        nav_layout = QVBoxLayout(nav_box)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(4)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for key, label in NAV_ITEMS:
            btn = NavButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.hovered.connect(
                lambda hovering, k=key: self._on_nav_hover(k, hovering)
            )
            self.nav_group.addButton(btn)
            self.nav_buttons[key] = btn
            nav_layout.addWidget(btn)
        sidebar_layout.addWidget(nav_box)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeToggle")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)
        self._update_theme_btn()

        self.update_btn = QPushButton("🔄  Yangilanishlar")
        self.update_btn.setObjectName("updateBtn")
        # Default holat: indikator o'chiq (yangilanish topilganda ko'k yonadi)
        self.update_btn.setProperty("updateAvailable", False)
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.clicked.connect(self._on_update_btn_clicked)
        self.update_btn.setVisible(True)
        sidebar_layout.addWidget(self.update_btn)

        self.phone_btn = QPushButton("📱  Telefon ulash")
        self.phone_btn.setObjectName("themeToggle")
        self.phone_btn.setCursor(Qt.PointingHandCursor)
        self.phone_btn.clicked.connect(self._open_phone_dialog)
        sidebar_layout.addWidget(self.phone_btn)

        sidebar_layout.addStretch(1)

        # ---------- Profil ----------
        profile = QFrame()
        profile.setObjectName("profileCard")
        profile_lay = QHBoxLayout(profile)
        profile_lay.setContentsMargins(10, 10, 10, 10)
        profile_lay.setSpacing(10)

        avatar = QLabel("F")
        avatar.setObjectName("avatarLabel")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(36, 36)
        profile_lay.addWidget(avatar)

        name_box = QVBoxLayout()
        name_box.setSpacing(0)
        name = QLabel("Farziddin Aminov")
        name.setObjectName("profileName")
        role = QLabel("O'qituvchi")
        role.setObjectName("profileRole")
        name_box.addWidget(name)
        name_box.addWidget(role)
        profile_lay.addLayout(name_box, 1)
        sidebar_layout.addWidget(profile)

        root.addWidget(sidebar)

        # ---------- Sahifalar ----------
        self.stack = QStackedWidget()
        self.pages["dashboard"] = DashboardPage()
        self.pages["students"] = StudentsPage()
        self.pages["groups"] = GroupsPage()
        self.pages["payments"] = PaymentsPage()
        self.pages["tests"] = TestsPage()
        self.pages["attendance"] = AttendancePage()
        self.pages["reminders"] = RemindersPage()
        self.pages["reports"] = ReportsPage()
        for key, page in self.pages.items():
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

    def _connect_signals(self) -> None:
        self.nav_group.buttonClicked.connect(self._on_nav_clicked)
        self.nav_buttons["dashboard"].setChecked(True)

    def _on_nav_hover(self, key: str, hovering: bool) -> None:
        """Bitta tugma ustiga kursor kelsa, qolganlarini blur qilish."""
        for k, btn in self.nav_buttons.items():
            if k == key:
                continue
            if hovering:
                effect = QGraphicsBlurEffect(btn)
                effect.setBlurRadius(1.5)
                btn.setGraphicsEffect(effect)
            else:
                btn.setGraphicsEffect(None)

    def _update_theme_btn(self) -> None:
        if theme.current_theme() == "light":
            self.theme_btn.setText("☀️  Kunduzgi rejim")
        else:
            self.theme_btn.setText("🌙  Tungi rejim")

    def toggle_theme(self) -> None:
        from PySide2.QtWidgets import QApplication

        new = "light" if theme.current_theme() == "dark" else "dark"
        theme.set_theme(new)
        try:
            from database.database import DATABASE

            DATABASE.set_setting("theme", new)
        except Exception:  # noqa: BLE001
            logger.exception("Mavzuni saqlashda xatolik")
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme.get_qss())
        self._update_theme_btn()
        self.refresh_all()

    def _on_nav_clicked(self, button: QPushButton) -> None:
        for key, btn in self.nav_buttons.items():
            if btn is button:
                self.switch_to(key)
                break

    def switch_to(self, key: str) -> None:
        page = self.pages.get(key)
        if not page:
            return
        self.nav_buttons[key].setChecked(True)
        self.stack.setCurrentWidget(page)
        page.refresh()

    def refresh_all(self) -> None:
        """Barcha sahifalarni yangilash (statistikalar sinxron bo'ladi)."""
        for key, page in self.pages.items():
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception:  # noqa: BLE001
                    logger.exception("Sahifani yangilashda xatolik: %s", key)

    def show_dashboard(self) -> None:
        self.switch_to("dashboard")

    # ---------- Masofaviy yangilanish ----------
    # Tugma yashirin turadi; yangilanish topilganda chiqadi + push keladi.
    def _setup_auto_update(self) -> None:
        self._update_checker = None
        self._update_info = None
        self._update_checking = False
        QTimer.singleShot(20_000, self.start_update_check)
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self.start_update_check)
        self._update_timer.start(6 * 3600_000)

    def _make_update_checker(self):
        from PySide2.QtCore import QObject, Signal

        main = self

        class UpdateChecker(QObject):
            finished = Signal(object)

            def start(self) -> None:
                import threading

                thread = threading.Thread(target=self._run, daemon=True)
                thread.start()

            def _run(self) -> None:
                try:
                    from services import update_service

                    info = update_service.check_for_updates()
                except Exception:  # noqa: BLE001
                    logger.exception("Yangilanish tekshiruvi xatosi")
                    info = None
                try:
                    self.finished.emit(info)
                except RuntimeError:
                    pass

        checker = UpdateChecker(main)
        checker.finished.connect(main._on_update_checked)
        return checker

    def start_update_check(self) -> None:
        if getattr(self, "_update_checking", False):
            return
        self._update_checking = True
        try:
            self._update_checker = self._make_update_checker()
            self._update_checker.start()
        except Exception:  # noqa: BLE001
            logger.exception("Updater ishga tushmadi")
            self._update_checking = False

    def _set_update_indicator(self, active: bool) -> None:
        """Yangilanish indikatori: yangilanish bor bo'lsa tugma ko'k yonadi,
        aks holda default (o'chiq) holatda turadi."""
        try:
            self.update_btn.setProperty("updateAvailable", active)
            self.update_btn.setText(
                "🔄  Yangilanishlar (Yangi!)" if active else "🔄  Yangilanishlar"
            )
            style = self.style()
            if style is not None:
                style.unpolish(self.update_btn)
                style.polish(self.update_btn)
            self.update_btn.update()
        except RuntimeError:
            pass

    def _on_update_checked(self, info) -> None:
        self._update_checking = False
        if not info:
            self._update_info = None
            self._set_update_indicator(False)
            return

        self._update_info = info
        self._set_update_indicator(True)

        # Push-habar — faqat yangilanish bor paytda chiqadi
        try:
            from version import VERSION

            self._notify(
                "🔄 Yangilanish mavjud (v%s)" % info.get("version", ""),
                "Yangi versiyani o'rnatish uchun\n"
                "sidebar'dagi «Yangilanishlar» tugmasini bosing.\n"
                "Hozirgi versiya: v%s." % VERSION,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Yangilanish push-xabari yuborilmadi")

    def _start_sync_server(self) -> None:
        from services import sync_server

        self.sync_server = sync_server.SyncServer()
        if not self.sync_server.start():
            logger.warning("Sync server ishga tushmadi (port band?)")

    def _open_phone_dialog(self) -> None:
        from PySide2.QtWidgets import QMessageBox

        from ui.phone_dialog import PhoneDialog

        server = getattr(self, "sync_server", None)
        if server is None or not server.running:
            self._start_sync_server()
            server = getattr(self, "sync_server", None)
        if server is None or not server.running:
            QMessageBox.warning(
                self,
                "Telefon ulash",
                "Sync server ishga tushmadi (port band bo'lishi mumkin).\n"
                "Dasturdan ortiqcha nusxa ishlayotgan bo'lsa yoping va qayta urining.",
            )
            return
        dlg = PhoneDialog(self)
        dlg.exec()

    def _on_update_btn_clicked(self) -> None:
        info = getattr(self, "_update_info", None)
        from PySide2.QtWidgets import QMessageBox

        if not info:
            try:
                from version import VERSION
            except Exception:
                VERSION = "1.3.10"
            QMessageBox.information(
                self,
                "Yangilanishlar",
                "Sizda eng so'nggi versiya (v%s) o'rnatilgan.\n\nYangilanishlar mavjud emas." % VERSION,
            )
            return

        from services import update_service

        answer = QMessageBox.question(
            self,
            "Yangilanish mavjud",
            update_service.format_info(info),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._do_update(info)

    def _do_update(self, info: dict) -> None:
        import os
        import tempfile

        from PySide2.QtWidgets import QMessageBox, QProgressDialog

        from services import update_service

        target = os.path.join(
            tempfile.gettempdir(),
            "KursManager_update_%s.exe" % info.get("version", "new"),
        )
        progress = QProgressDialog(
            "Yangilanish yuklanmoqda...", "Bekor qilish", 0, 100, self
        )
        progress.setWindowTitle("Yangilanish")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        cancelled = {"flag": False}

        def _cb(downloaded: int, total: int) -> bool:
            if progress.wasCanceled():
                cancelled["flag"] = True
                return False
            if total > 0:
                progress.setValue(int(downloaded * 100 / total))
            QApplication.processEvents()
            return True

        try:
            update_service.download_update(info["url"], target, _cb)
        except InterruptedError:
            progress.close()
            try:
                if os.path.exists(target):
                    os.remove(target)
            except OSError:
                pass
            return
        except Exception as exc:  # noqa: BLE001
            progress.close()
            QMessageBox.critical(
                self, "Xatolik", "Yuklashda xatolik:\n%s" % exc
            )
            return
        progress.close()
        if cancelled["flag"]:
            return
        if not update_service.verify_sha256(target, info.get("sha256", "")):
            QMessageBox.critical(
                self,
                "Xatolik",
                "Yuklangan fayl buzilgan (nazorat summasi mos emas).\n"
                "Qayta urinib ko'ring.",
            )
            try:
                os.remove(target)
            except OSError:
                pass
            return
        if not update_service.launch_updater(target):
            QMessageBox.warning(
                self,
                "Yangilanish",
                "Avtomatik almashtirib bo'lmadi.\n"
                "Yuklangan fayl:\n%s" % target,
            )
            return
        QApplication.instance().quit()

    # ---------- Bildirishnomalar (eslatma + to'lov muddati) ----------
    def _setup_notifications(self) -> None:
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray = QSystemTrayIcon(make_app_icon(), self)
                self.tray.setToolTip("Kurs Manager")
                self.tray.show()
        except Exception:  # noqa: BLE001
            logger.exception("Tray yaratilmadi")
            self.tray = None
        self.notify_timer = QTimer(self)
        self.notify_timer.timeout.connect(self.check_notifications)
        self.notify_timer.start(60_000)
        QTimer.singleShot(15_000, self.check_notifications)

    def _notify(self, title: str, text: str) -> None:
        try:
            QApplication.beep()
        except Exception:  # noqa: BLE001
            pass
        if self.tray:
            try:
                self.tray.showMessage(
                    title, text,
                    QSystemTrayIcon.Information, 10_000,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Tray habar yuborilmadi")

    def check_notifications(self) -> None:
        """Vaqti kelgan eslatmalar va to'lov muddatlarini tekshirish."""
        try:
            from services import reminder_service
            from services.due_service import get_payment_dues

            for r in reminder_service.get_due():
                text = r["datetime_display"]
                if r["note"]:
                    text += f"\n{r['note']}"
                self._notify(f"🔔 Eslatma: {r['title']}", text)
            for p in get_payment_dues():
                self._notify("💳 To'lov eslatmasi", p["text"])
        except Exception:  # noqa: BLE001
            logger.exception("Bildirishnoma tekshiruvida xatolik")