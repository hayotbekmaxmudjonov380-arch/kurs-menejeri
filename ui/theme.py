"""Dastur uchun ranglar va QSS (dark professional dashboard)."""

from __future__ import annotations

from PySide6.QtGui import QColor

BG = "#0d1424"
BG_DARK = "#0b1120"
PANEL = "#141d34"
PANEL_ALT = "#16203a"
PANEL_INPUT = "#0f1830"
BORDER = "#223055"
BORDER_SOFT = "#27365b"
TEXT = "#e2e8f0"
TEXT_DIM = "#94a3b8"
TEXT_FAINT = "#64748b"
PRIMARY = "#3b82f6"
PRIMARY_DARK = "#1d4ed8"
PRIMARY_HOVER = "#2563eb"
GREEN = "#22c55e"
GREEN_DARK = "#16a34a"
YELLOW = "#f59e0b"
RED = "#ef4444"
RED_DARK = "#dc2626"

FONT_FAMILY = "Segoe UI"

# To'lov holatlari meta-ma'lumotlari
STATUS_META = {
    "paid": {"label": "To'lov qilingan", "color": GREEN, "emoji": "🟢"},
    "pending": {"label": "Kutilmoqda", "color": YELLOW, "emoji": "🟡"},
    "unpaid": {"label": "To'lov qilinmagan", "color": RED, "emoji": "🔴"},
}


def with_alpha(color: str, alpha: int) -> str:
    c = QColor(color)
    c.setAlpha(alpha)
    return c.name(QColor.NameFormat.HexArgb)


THEMES = ("dark", "light")
_current_theme = "dark"


def current_theme() -> str:
    return _current_theme


def set_theme(name: str) -> None:
    global _current_theme
    if name in THEMES:
        _current_theme = name


def get_qss() -> str:
    return LIGHT_QSS if _current_theme == "light" else QSS


def fg() -> str:
    """Joriy mavzudagi asosiy matn rangi (inline stillar uchun)."""
    return "#101f36" if _current_theme == "light" else "#e2e8f0"


def dim() -> str:
    """Joriy mavzudagi ikkinchi darajali matn rangi."""
    return "#4c5d78" if _current_theme == "light" else "#cbd5e1"


QSS = """
* {
    font-family: 'Segoe UI';
    outline: none;
}
QMainWindow, QDialog, QStackedWidget, #pageRoot {
    background-color: #0d1424;
    color: #e2e8f0;
}
QLabel {
    color: #cbd5e1;
    background: transparent;
}
#pageRoot { background-color: #0d1424; }

/* ===== Sidebar ===== */
#sidebar {
    background-color: #0b1120;
    border-right: 1px solid #16203a;
}
#sidebarTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
}
#sidebarSub {
    color: #64748b;
    font-size: 11px;
}
#navBox {
    background-color: #0d1117;
    border-radius: 12px;
}
#navButton {
    background: transparent;
    border: 2px solid transparent;
    border-radius: 10px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 600;
    padding: 10px;
    text-align: left;
}
#navButton:hover {
    border: 2px solid #1a1f24;
    color: #637185;
}
#navButton:checked {
    background-color: #1a1f24;
    border: 2px solid #1a1f24;
    border-left: 5px solid #2f81f7;
    color: #ffffff;
    padding-left: 22px;
}
#updateBtn {
    background: transparent;
    border: 1px solid #27365b;
    border-radius: 10px;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
    padding: 8px;
}
#updateBtn:hover {
    border-color: #3b82f6;
    color: #e2e8f0;
}
#updateBtn[updateAvailable="true"] {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 700;
}
#updateBtn[updateAvailable="true"]:hover {
    background-color: #1d4ed8;
}
#profileCard {
    background: #131c33;
    border: 1px solid #223055;
    border-radius: 14px;
}
#profileName { color: #ffffff; font-size: 13px; font-weight: 700; }
#profileRole { color: #64748b; font-size: 11px; }
#avatarLabel {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #1e3a8a);
    color: #ffffff;
    border-radius: 18px;
    font-weight: 800;
}

/* ===== Cards ===== */
#card {
    background-color: #141d34;
    border: 1px solid #223055;
    border-radius: 14px;
}
#cardAlt {
    background-color: #16203a;
    border: 1px solid #223055;
    border-radius: 10px;
}
#statTitle { color: #7d8db0; font-size: 12px; font-weight: 600; }
#statValue { font-size: 26px; font-weight: 800; }
#pageTitle { color: #f1f5f9; font-size: 22px; font-weight: 800; }
#pageSub { color: #64748b; font-size: 12px; }
#cardTitle { color: #e2e8f0; font-size: 15px; font-weight: 700; }
#cardSub { color: #64748b; font-size: 12px; }
#hintText { color: #64748b; font-size: 11px; }

/* ===== Buttons ===== */
QPushButton {
    background-color: #1d4ed8;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover { background-color: #2563eb; }
QPushButton:pressed { background-color: #1e40af; }
QPushButton:disabled { background-color: #283350; color: #64748b; }

QPushButton[kind="danger"] { background-color: #dc2626; }
QPushButton[kind="danger"]:hover { background-color: #ef4444; }
QPushButton[kind="success"] { background-color: #16a34a; }
QPushButton[kind="success"]:hover { background-color: #22c55e; }
QPushButton[kind="warning"] { background-color: #d97706; }
QPushButton[kind="warning"]:hover { background-color: #f59e0b; }

QPushButton[kind="ghost"] {
    background-color: transparent;
    color: #cbd5e1;
    border: 1px solid #2a3a5c;
}
QPushButton[kind="ghost"]:hover {
    background-color: #16203a;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton[kind="chip"] {
    background-color: transparent;
    border: 1px solid #2a3a5c;
    border-radius: 999px;
    color: #94a3b8;
    padding: 7px 16px;
    font-size: 12px;
    margin: 2px 3px;
}
QPushButton[kind="chip"]:hover { border-color: #3b82f6; color: #e2e8f0; }
QPushButton[kind="chip"]:checked { background-color: #1d4ed8; color: #fff; border-color: #1d4ed8; }

QToolButton#actionButton {
    background-color: #1b2642;
    color: #cbd5e1;
    border: 1px solid #2a3a5c;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}
QToolButton#actionButton:hover { background-color: #253252; color: #ffffff; border-color: #3b82f6; }

QPushButton[kind="mini-status"] {
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid transparent;
}
QPushButton[kind="mini-status"][color="green"] { background-color: #14532d; color: #4ade80; border-color: #166534; }
QPushButton[kind="mini-status"][color="green"]:hover { background-color: #166534; color: #bbf7d0; }
QPushButton[kind="mini-status"][color="yellow"] { background-color: #422006; color: #facc15; border-color: #713f12; }
QPushButton[kind="mini-status"][color="yellow"]:hover { background-color: #713f12; color: #fef08a; }
QPushButton[kind="mini-status"][color="red"] { background-color: #450a0a; color: #f87171; border-color: #7f1d1d; }
QPushButton[kind="mini-status"][color="red"]:hover { background-color: #7f1d1d; color: #fecaca; }

/* ===== Inputs ===== */
QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox,
QTextEdit, QPlainTextEdit {
    background-color: #0f1830;
    border: 1px solid #27365b;
    border-radius: 8px;
    padding: 9px 12px;
    color: #e2e8f0;
    font-size: 13px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #3b82f6;
}
QLineEdit#search { padding-left: 36px; border-radius: 999px; }
QLineEdit#search:focus { border-color: #3b82f6; }
QLineEdit:disabled, QComboBox:disabled { color: #64748b; background-color: #0d1424; }

QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #7d8db0;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #16203a;
    border: 1px solid #2a3a5c;
    border-radius: 8px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
    color: #e2e8f0;
    padding: 4px;
}
QDateEdit::drop-down, QDateTimeEdit::drop-down { border: none; width: 26px; }

QSpinBox::up-button, QDoubleSpinBox::up-button { width: 20px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 20px; border: none; }

QCheckBox { color: #cbd5e1; font-size: 13px; spacing: 6px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #2a3a5c; background: #0f1830; }
QCheckBox::indicator:checked { background-color: #2563eb; border-color: #2563eb; }

QFormLayout Label { padding-top: 4px; }

/* ===== Tables ===== */
QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    alternate-background-color: #111a30;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}
QTableWidget::item { padding: 4px 6px; border-bottom: 1px solid #1b2745; color: #c7d2e8; }
QTableWidget::item:selected { background-color: #1d3a8a; color: #ffffff; }
QTableWidget::item:hover { background-color: rgba(59, 130, 246, 0.12); }
QHeaderView::section {
    background-color: #101a30;
    color: #7d8db0;
    border: none;
    border-bottom: 1px solid #223055;
    padding: 10px 8px;
    font-size: 11px;
    font-weight: 700;
}
QTableCornerButton::section { background-color: #101a30; border: none; }
QTableWidget QTableCornerButton::section { background-color: #101a30; }

/* ===== Menus ===== */
QMenu {
    background-color: #131c33;
    border: 1px solid #2a3a5c;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 8px 20px; border-radius: 6px; color: #cbd5e1; font-size: 12px; }
QMenu::item:selected { background-color: #1d4ed8; color: #ffffff; }
QMenu::separator { height: 1px; background-color: #24324f; margin: 6px 8px; }

/* ===== Scrollbars ===== */
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #2a3a5c; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #2a3a5c; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ===== Guruhlar ro'yxati (zamonaviy) ===== */
#groupsList {
    background-color: #0f1830;
    border: 1px solid #27365b;
    border-radius: 12px;
    padding: 6px;
    font-size: 14px;
    font-weight: 600;
}
#groupsList::item {
    background: transparent;
    color: #cbd5e1;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 12px;
}
#groupsList::item:hover {
    background-color: rgba(59, 130, 246, 0.12);
    border-color: #3b82f6;
}
#groupsList::item:selected {
    background-color: rgba(34, 197, 94, 0.16);
    border: 1px solid #22c55e;
    color: #4ade80;
}
#groupsList::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid #3b82f6;
    background: transparent;
}
#groupsList::indicator:checked {
    background-color: #22c55e;
    border-color: #22c55e;
}

/* ===== Telefon ulash oynasi ===== */
#phoneAvatar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #1e3a8a);
    color: #ffffff;
    border-radius: 23px;
    font-size: 20px;
}
#codeCard {
    background-color: #0f1a33;
    border: 1px solid #23375f;
    border-radius: 14px;
}
#codeValue {
    color: #3b82f6;
    font-size: 46px;
    font-weight: 800;
    letter-spacing: 6px;
    background: transparent;
    border: none;
}
#countPill {
    background-color: rgba(59, 130, 246, 0.16);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.45);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 700;
}
#deviceList {
    background-color: #0f1830;
    border: 1px solid #27365b;
    border-radius: 12px;
    padding: 6px;
    font-size: 13px;
    font-weight: 600;
}
#deviceList::item {
    background: transparent;
    color: #cbd5e1;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 10px 12px;
}
#deviceList::item:hover {
    background-color: rgba(59, 130, 246, 0.12);
    border-color: #3b82f6;
}
#deviceList::item:selected {
    background-color: rgba(239, 68, 68, 0.14);
    border: 1px solid #ef4444;
    color: #fca5a5;
}

/* ===== Register-uslubidagi formalar ===== */
QDialog[formStyle="register"] {
    background-color: #1a1a1a;
    border: 1px solid #333;
}
QPushButton[formSubmit="true"] {
    background-color: #00bfff;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 10px;
    font-size: 16px;
    font-weight: 600;
}
QPushButton[formSubmit="true"]:hover {
    background-color: rgba(0, 191, 255, 150);
}
QPushButton[formSubmit="true"]:pressed {
    background-color: #009acd;
}

/* ===== MessageBox ===== */
QMessageBox { background-color: #141d34; }
QMessageBox QLabel { color: #e2e8f0; font-size: 13px; }
QMessageBox QPushButton { min-width: 90px; }

/* ===== Tooltip ===== */
QToolTip {
    background-color: #1b2642;
    color: #e2e8f0;
    border: 1px solid #2a3a5c;
    border-radius: 6px;
    padding: 6px;
    font-size: 12px;
}

/* QCalendarWidget */
QCalendarWidget QWidget { background-color: #141d34; color: #cbd5e1; }
QCalendarWidget QAbstractItemView:enabled { color: #cbd5e1; selection-background-color: #1d4ed8; selection-color: #ffffff; }

/* QTabWidget */
QTabWidget::pane { border: 1px solid #223055; border-radius: 10px; background: #141d34; top: -1px; }
QTabBar::tab {
    background: transparent; color: #94a3b8; padding: 8px 18px; border: none;
    border-bottom: 2px solid transparent; font-size: 13px; font-weight: 600;
}
QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid #3b82f6; }

QProgressBar { background: #111a30; border: 1px solid #223055; border-radius: 6px; }
QProgressBar::chunk { background: #3b82f6; border-radius: 5px; }
"""


LIGHT_QSS = """
* {
    font-family: 'Segoe UI';
    outline: none;
}
QMainWindow, QDialog, QStackedWidget, #pageRoot {
    background-color: #eef2f8;
    color: #101f36;
}
QLabel {
    color: #33415c;
    background: transparent;
}
#pageRoot { background-color: #eef2f8; }

/* ===== Sidebar ===== */
#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e0e7f2;
}
#sidebarTitle {
    color: #0b1830;
    font-size: 20px;
    font-weight: 800;
}
#sidebarSub {
    color: #8595ad;
    font-size: 11px;
}
#navBox {
    background-color: #e7edf5;
    border-radius: 12px;
}
#navButton {
    background: transparent;
    border: 2px solid transparent;
    border-radius: 10px;
    color: #0b1830;
    font-size: 15px;
    font-weight: 600;
    padding: 10px;
    text-align: left;
}
#navButton:hover {
    border: 2px solid #c2cfe2;
    color: #4c5d78;
}
#navButton:checked {
    background-color: #d7e1ef;
    border: 2px solid #d7e1ef;
    border-left: 5px solid #2f81f7;
    color: #0b1830;
    padding-left: 22px;
}
#updateBtn {
    background: transparent;
    border: 1px solid #d5deec;
    border-radius: 10px;
    color: #8595ad;
    font-size: 13px;
    font-weight: 600;
    padding: 8px;
}
#updateBtn:hover {
    border-color: #3b82f6;
    color: #0b1830;
}
#updateBtn[updateAvailable="true"] {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 700;
}
#updateBtn[updateAvailable="true"]:hover {
    background-color: #1d4ed8;
}
#themeToggle {
    background: transparent;
    border: 1px solid #d5deec;
    border-radius: 10px;
    color: #4c5d78;
    font-size: 13px;
    font-weight: 600;
    padding: 8px;
}
#themeToggle:hover {
    border-color: #3b82f6;
    color: #0b1830;
}
#profileCard {
    background: #eef2f8;
    border: 1px solid #d5deec;
    border-radius: 14px;
}
#profileName { color: #0b1830; font-size: 13px; font-weight: 700; }
#profileRole { color: #8595ad; font-size: 11px; }
#avatarLabel {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #1e3a8a);
    color: #ffffff;
    border-radius: 18px;
    font-weight: 800;
}

/* ===== Cards ===== */
#card {
    background-color: #ffffff;
    border: 1px solid #d5deec;
    border-radius: 14px;
}
#cardAlt {
    background-color: #e7edf5;
    border: 1px solid #d5deec;
    border-radius: 10px;
}
#statTitle { color: #5b6b8c; font-size: 12px; font-weight: 600; }
#statValue { font-size: 26px; font-weight: 800; }
#pageTitle { color: #0b1830; font-size: 22px; font-weight: 800; }
#pageSub { color: #8595ad; font-size: 12px; }
#cardTitle { color: #0b1830; font-size: 15px; font-weight: 700; }
#cardSub { color: #8595ad; font-size: 12px; }
#hintText { color: #8595ad; font-size: 11px; }

/* ===== Buttons ===== */
QPushButton {
    background-color: #1d4ed8;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover { background-color: #2563eb; }
QPushButton:pressed { background-color: #1e40af; }
QPushButton:disabled { background-color: #e2e9f4; color: #8595ad; }

QPushButton[kind="danger"] { background-color: #dc2626; }
QPushButton[kind="danger"]:hover { background-color: #ef4444; }
QPushButton[kind="success"] { background-color: #16a34a; }
QPushButton[kind="success"]:hover { background-color: #22c55e; }
QPushButton[kind="warning"] { background-color: #d97706; }
QPushButton[kind="warning"]:hover { background-color: #f59e0b; }

QPushButton[kind="ghost"] {
    background-color: transparent;
    color: #4c5d78;
    border: 1px solid #c2cfe2;
}
QPushButton[kind="ghost"]:hover {
    background-color: #e2e9f4;
    border-color: #3b82f6;
    color: #0b1830;
}

QPushButton[kind="chip"] {
    background-color: transparent;
    border: 1px solid #c2cfe2;
    border-radius: 999px;
    color: #4c5d78;
    padding: 7px 16px;
    font-size: 12px;
    margin: 2px 3px;
}
QPushButton[kind="chip"]:hover { border-color: #3b82f6; color: #0b1830; }
QPushButton[kind="chip"]:checked { background-color: #1d4ed8; color: #fff; border-color: #1d4ed8; }

QToolButton#actionButton {
    background-color: #e7edf5;
    color: #33415c;
    border: 1px solid #c2cfe2;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}
QToolButton#actionButton:hover { background-color: #dbe3ee; color: #0b1830; border-color: #3b82f6; }

QPushButton[kind="mini-status"] {
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid transparent;
}
QPushButton[kind="mini-status"][color="green"] { background-color: #14532d; color: #4ade80; border-color: #166534; }
QPushButton[kind="mini-status"][color="green"]:hover { background-color: #166534; color: #bbf7d0; }
QPushButton[kind="mini-status"][color="yellow"] { background-color: #422006; color: #facc15; border-color: #713f12; }
QPushButton[kind="mini-status"][color="yellow"]:hover { background-color: #713f12; color: #fef08a; }
QPushButton[kind="mini-status"][color="red"] { background-color: #450a0a; color: #f87171; border-color: #7f1d1d; }
QPushButton[kind="mini-status"][color="red"]:hover { background-color: #7f1d1d; color: #fecaca; }

/* ===== Inputs ===== */
QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox,
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #c2cfe2;
    border-radius: 8px;
    padding: 9px 12px;
    color: #101f36;
    font-size: 13px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #3b82f6;
}
QLineEdit#search { padding-left: 36px; border-radius: 999px; }
QLineEdit#search:focus { border-color: #3b82f6; }
QLineEdit:disabled, QComboBox:disabled { color: #8595ad; background-color: #eef2f8; }

QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #5b6b8c;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #c2cfe2;
    border-radius: 8px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
    color: #101f36;
    padding: 4px;
}
QDateEdit::drop-down, QDateTimeEdit::drop-down { border: none; width: 26px; }

QSpinBox::up-button, QDoubleSpinBox::up-button { width: 20px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 20px; border: none; }

QCheckBox { color: #33415c; font-size: 13px; spacing: 6px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #c2cfe2; background: #ffffff; }
QCheckBox::indicator:checked { background-color: #2563eb; border-color: #2563eb; }

QFormLayout Label { padding-top: 4px; }

/* ===== Tables ===== */
QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    alternate-background-color: #eef3f9;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}
QTableWidget::item { padding: 4px 6px; border-bottom: 1px solid #e0e7f2; color: #33415c; }
QTableWidget::item:selected { background-color: #1d4ed8; color: #ffffff; }
QTableWidget::item:hover { background-color: rgba(43, 127, 255, 0.10); }
QHeaderView::section {
    background-color: #e7edf5;
    color: #5b6b8c;
    border: none;
    border-bottom: 1px solid #d5deec;
    padding: 10px 8px;
    font-size: 11px;
    font-weight: 700;
}
QTableCornerButton::section { background-color: #e7edf5; border: none; }
QTableWidget QTableCornerButton::section { background-color: #e7edf5; }

/* ===== Menus ===== */
QMenu {
    background-color: #ffffff;
    border: 1px solid #c2cfe2;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 8px 20px; border-radius: 6px; color: #101f36; font-size: 12px; }
QMenu::item:selected { background-color: #1d4ed8; color: #ffffff; }
QMenu::separator { height: 1px; background-color: #e0e7f2; margin: 6px 8px; }

/* ===== Scrollbars ===== */
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #c2cfe2; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #c2cfe2; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ===== Guruhlar ro'yxati (zamonaviy, light) ===== */
#groupsList {
    background-color: #ffffff;
    border: 1px solid #c2cfe2;
    border-radius: 12px;
    padding: 6px;
    font-size: 14px;
    font-weight: 600;
}
#groupsList::item {
    background: transparent;
    color: #33415c;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 12px;
}
#groupsList::item:hover {
    background-color: rgba(43, 127, 255, 0.10);
    border-color: #3b82f6;
}
#groupsList::item:selected {
    background-color: rgba(34, 197, 94, 0.14);
    border: 1px solid #16a34a;
    color: #15803d;
}
#groupsList::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid #3b82f6;
    background: transparent;
}
#groupsList::indicator:checked {
    background-color: #16a34a;
    border-color: #16a34a;
}

/* ===== Telefon ulash oynasi (light) ===== */
#phoneAvatar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3b82f6, stop:1 #1e3a8a);
    color: #ffffff;
    border-radius: 23px;
    font-size: 20px;
}
#codeCard {
    background-color: #eef4ff;
    border: 1px solid #c9dbfb;
    border-radius: 14px;
}
#codeValue {
    color: #1d4ed8;
    font-size: 46px;
    font-weight: 800;
    letter-spacing: 6px;
    background: transparent;
    border: none;
}
#countPill {
    background-color: rgba(37, 99, 235, 0.12);
    color: #1d4ed8;
    border: 1px solid rgba(37, 99, 235, 0.4);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 700;
}
#deviceList {
    background-color: #ffffff;
    border: 1px solid #c2cfe2;
    border-radius: 12px;
    padding: 6px;
    font-size: 13px;
    font-weight: 600;
}
#deviceList::item {
    background: transparent;
    color: #33415c;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 10px 12px;
}
#deviceList::item:hover {
    background-color: rgba(43, 127, 255, 0.10);
    border-color: #3b82f6;
}
#deviceList::item:selected {
    background-color: rgba(239, 68, 68, 0.12);
    border: 1px solid #ef4444;
    color: #b91c1c;
}

/* ===== Register-uslubidagi formalar (har doim dark) ===== */
QDialog[formStyle="register"] {
    background-color: #1a1a1a;
    border: 1px solid #333;
}
QPushButton[formSubmit="true"] {
    background-color: #00bfff;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 10px;
    font-size: 16px;
    font-weight: 600;
}
QPushButton[formSubmit="true"]:hover {
    background-color: rgba(0, 191, 255, 150);
}
QPushButton[formSubmit="true"]:pressed {
    background-color: #009acd;
}

/* ===== MessageBox ===== */
QMessageBox { background-color: #ffffff; }
QMessageBox QLabel { color: #101f36; font-size: 13px; }
QMessageBox QPushButton { min-width: 90px; }

/* ===== Tooltip ===== */
QToolTip {
    background-color: #ffffff;
    color: #101f36;
    border: 1px solid #d5deec;
    border-radius: 6px;
    padding: 6px;
    font-size: 12px;
}

/* QCalendarWidget */
QCalendarWidget QWidget { background-color: #ffffff; color: #33415c; }
QCalendarWidget QAbstractItemView:enabled { color: #33415c; selection-background-color: #1d4ed8; selection-color: #ffffff; }

/* QTabWidget */
QTabWidget::pane { border: 1px solid #d5deec; border-radius: 10px; background: #ffffff; top: -1px; }
QTabBar::tab {
    background: transparent; color: #4c5d78; padding: 8px 18px; border: none;
    border-bottom: 2px solid transparent; font-size: 13px; font-weight: 600;
}
QTabBar::tab:selected { color: #0b1830; border-bottom: 2px solid #3b82f6; }

QProgressBar { background: #e2e9f4; border: 1px solid #d5deec; border-radius: 6px; }
QProgressBar::chunk { background: #3b82f6; border-radius: 5px; }
"""