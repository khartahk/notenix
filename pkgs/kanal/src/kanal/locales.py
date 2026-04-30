"""kanal.locales — locale and keyboard-layout discovery.

This module has no side effects at import time and no dependency on any other
kanal module.  All functions are pure or read-only with respect to system files.

Public API
----------
list_locales()              → sorted [(code, label), ...]
list_kbd_layouts()          → sorted [(code, label), ...]
kbd_default_for_locale(s)   → XKB layout code string or None
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Locale → XKB layout mapping
# ---------------------------------------------------------------------------

_LOCALE_TO_KBD: dict[str, str] = {
    "af": "za",    "sq": "al",    "ar": "ara",  "az": "az",
    "be": "by",    "bn": "bd",    "bs": "ba",   "bg": "bg",
    "ca": "es",    "cs": "cz",    "cy": "gb",   "da": "dk",
    "de": "de",    "el": "gr",    "en_US": "us","en_GB": "gb",
    "en_AU": "au", "en_CA": "ca", "eo": "epo",
    "es": "es",    "es_MX": "latam", "es_AR": "latam",
    "et": "ee",    "eu": "es",    "fa": "ir",   "fi": "fi",
    "fr": "fr",    "fr_BE": "be", "fr_CA": "ca",
    "ga": "ie",    "gl": "es",    "gu": "in",
    "he": "il",    "hi": "in",    "hr": "hr",   "hu": "hu",
    "hy": "am",    "id": "us",    "is": "is",   "it": "it",
    "ja": "jp",    "ka": "ge",    "kk": "kz",   "km": "kh",
    "kn": "in",    "ko": "kr",    "ky": "kg",
    "lt": "lt",    "lv": "lv",    "mk": "mk",   "ml": "in",
    "mn": "mn",    "mr": "in",    "ms": "us",
    "nb": "no",    "ne": "np",    "nl": "nl",   "nl_BE": "be",
    "pa": "in",    "pl": "pl",    "pt": "pt",   "pt_BR": "br",
    "ro": "ro",    "ru": "ru",    "sk": "sk",   "sl": "si",
    "sr": "rs",    "sv": "se",
    "ta": "in",    "te": "in",    "th": "th",   "tr": "tr",
    "uk": "ua",    "ur": "pk",    "uz": "uz",
    "vi": "vn",    "zh_CN": "cn", "zh_TW": "tw",
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def kbd_default_for_locale(locale_str: str) -> str | None:
    """Return a likely XKB layout code for *locale_str*.

    Examples: ``'en_US.UTF-8'`` → ``'us'``,  ``'sl_SI.UTF-8'`` → ``'si'``.
    """
    for sep in (".", "@", "_"):
        base = locale_str.split(sep)[0]
        if base in _LOCALE_TO_KBD:
            return _LOCALE_TO_KBD[base]
    return _LOCALE_TO_KBD.get(locale_str[:2])


def list_locales() -> list[tuple[str, str]]:
    """Return sorted ``(code, display_label)`` pairs for all common UTF-8 locales.

    Reads from the path baked in by the Nix build (``KANAL_LOCALE_SUPPORTED``),
    then from well-known system paths, and falls back to a small hardcoded list.
    Labels use native-language names so users can search in their own language.
    """
    _HARDCODED: list[tuple[str, str]] = [
        ("en_US.UTF-8", "English (US)"),
        ("en_GB.UTF-8", "English (UK)"),
        ("sl_SI.UTF-8", "Slovenščina"),
    ]
    _NATIVE: dict[str, str] = {
        code.split(".")[0]: name for code, name in _HARDCODED
    }

    env_path = os.environ.get("KANAL_LOCALE_SUPPORTED", "")
    candidates: list[Path] = (
        [Path(env_path)] if env_path else []
    ) + [
        Path("/run/current-system/sw/share/i18n/SUPPORTED"),
        Path("/usr/share/i18n/SUPPORTED"),
        Path("/etc/locale.gen"),
    ]

    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text()
        # Skip the single-line NixOS stub
        if text.startswith("SUPPORTED-LOCALES=") and text.count("\n") <= 1:
            continue
        seen: set[str] = set()
        pairs: list[tuple[str, str]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            code = line.split()[0]
            if not code.upper().endswith(".UTF-8") and "/UTF-8" not in line:
                continue
            if "/" in code:
                code = code.split("/")[0]
            if code not in seen:
                seen.add(code)
                name = _NATIVE.get(code.split(".")[0], code.split(".")[0])
                pairs.append((code, f"{name}  ({code})"))
        if pairs:
            return sorted(pairs, key=lambda x: x[1].lower())

    return sorted(
        ((code, f"{name}  ({code})") for code, name in _HARDCODED),
        key=lambda x: x[1].lower(),
    )


def list_kbd_layouts() -> list[tuple[str, str]]:
    """Return sorted ``(code, display_label)`` pairs from evdev.xml.

    Falls back to XKB symbol filenames if the XML is absent,
    and to a minimal hardcoded list if the XKB directory is also missing.
    """
    import xml.etree.ElementTree as ET

    env_xml = os.environ.get("KANAL_XKB_EVDEV_XML", "")
    xml_candidates: list[Path] = (
        [Path(env_xml)] if env_xml else []
    ) + [
        Path("/run/current-system/sw/share/X11/xkb/rules/evdev.xml"),
        Path("/usr/share/X11/xkb/rules/evdev.xml"),
    ]

    for xml_path in xml_candidates:
        if not xml_path.exists():
            continue
        try:
            root    = ET.parse(xml_path).getroot()
            results: list[tuple[str, str]] = []
            for layout in root.findall(".//layout"):
                ci = layout.find("configItem")
                if ci is None:
                    continue
                name_el = ci.find("name")
                desc_el = ci.find("description")
                if name_el is None or desc_el is None:
                    continue
                code = name_el.text.strip()
                desc = desc_el.text.strip()
                results.append((code, desc))
                for variant in layout.findall(".//variant"):
                    vci = variant.find("configItem")
                    if vci is None:
                        continue
                    vn = vci.find("name")
                    vd = vci.find("description")
                    if vn is not None and vd is not None:
                        results.append((
                            f"{code}({vn.text.strip()})",
                            vd.text.strip(),
                        ))
            if results:
                return sorted(results, key=lambda x: x[1].lower())
        except Exception:
            pass

    # Fallback: symbol filenames
    xkb_dir = Path("/run/current-system/sw/share/X11/xkb/symbols")
    if xkb_dir.exists():
        codes = sorted(
            f.name for f in xkb_dir.iterdir()
            if f.is_file()
            and not f.name.startswith(".")
            and f.name not in {"CONTRIBUTORS", "README", "Makefile", "compose"}
        )
        return [(c, c) for c in codes]

    return [
        ("us", "English (US)"), ("gb", "English (UK)"),
        ("de", "German"),       ("fr", "French"),
        ("si", "Slovenian"),
    ]
