"""Formalarni tekshirish (validation) yordamchilari."""

from __future__ import annotations

import re

NON_DIGIT = re.compile(r"\D")


def validate_full_name(value: str) -> str | None:
    """F.I.Sh bo'sh bo'lsa xabar qaytaradi."""
    value = (value or "").strip()
    if not value:
        return "F.I.Sh kiritilishi kerak."
    if len(value) < 3:
        return "F.I.Sh juda qisqa kiritildi."
    if not any(ch.isalpha() for ch in value):
        return "F.I.Sh faqat harflardan iborat bo'lishi kerak."
    return None


def validate_phone(value: str) -> str | None:
    """Telefon raqami noto'g'ri bo'lsa xabar qaytaradi."""
    value = (value or "").strip()
    digits = NON_DIGIT.sub("", value)
    if not digits:
        return "Telefon raqamini to'g'ri kiriting."
    # Faqat raqamlar sonini tekshiramiz
    if len(digits) < 9 or len(digits) > 15:
        return "Telefon raqamini to'g'ri kiriting."
    return None


def validate_course_selected(course_id) -> str | None:
    """Kurs tanlanmagan bo'lsa xabar qaytaradi."""
    if course_id is None:
        return "Kursni tanlang."
    return None