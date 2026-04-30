"""Tests for kanal.locales — locale and keyboard layout helpers."""

from __future__ import annotations

from kanal.locales import kbd_default_for_locale, list_locales, list_kbd_layouts


def test_kbd_default_for_us_locale():
    assert kbd_default_for_locale("en_US.UTF-8") == "us"


def test_kbd_default_for_slovenian():
    assert kbd_default_for_locale("sl_SI.UTF-8") == "si"


def test_kbd_default_for_unknown_returns_none_or_str():
    result = kbd_default_for_locale("xx_XX.UTF-8")
    assert result is None or isinstance(result, str)


def test_list_locales_returns_pairs():
    pairs = list_locales()
    assert len(pairs) >= 1
    for code, label in pairs:
        assert isinstance(code, str)
        assert isinstance(label, str)
        assert ".UTF-8" in code or code  # at minimum non-empty


def test_list_locales_sorted():
    pairs = list_locales()
    labels = [label.lower() for _, label in pairs]
    assert labels == sorted(labels)


def test_list_kbd_layouts_returns_pairs():
    pairs = list_kbd_layouts()
    assert len(pairs) >= 1
    for code, label in pairs:
        assert isinstance(code, str)
        assert isinstance(label, str)
