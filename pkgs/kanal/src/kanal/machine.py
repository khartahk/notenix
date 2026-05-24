"""kanal.machine — read and write machine-specific settings in machine.nix.

Covers identity (hostname, username, full name), locale, timezone, keyboard
layout, state version, and optional feature flags.

Public API
----------
read_machine()          → dict of current settings (no root needed)
save_machine(settings)  → write settings to machine.nix   (root required)
read_features()         → dict of feature-flag booleans   (no root needed)
save_features(features) → write feature flags             (root required)
"""

from __future__ import annotations

import os
from pathlib import Path

from kanal.constants import (
    ALL_FEATURES,
    DRY_RUN,
    KEY_FEATURE_TAILSCALE,
    KEY_FLATPAK_PACKAGES,
    KEY_GNOME_EXTENSIONS,
    KEY_HOSTNAME,
    KEY_KBLAYOUT,
    KEY_LOCALE,
    KEY_STATEVERSION,
    KEY_TIMEZONE,
    KEY_USERDESC,
    KEY_USERNAME,
    MACHINE_PATH,
    TAILSCALE_EXT_ID,
)
from kanal.nixfiles import _get_value, _get_list, _remove_key, _upsert_bool, _upsert_list, _upsert_value

_DEFAULT_MACHINE = "{ lib, ... }:\n{\n}\n"

# ---------------------------------------------------------------------------
# Live-system fallbacks (used when machine.nix fields are empty)
# ---------------------------------------------------------------------------

def _env_fallbacks() -> dict[str, str]:
    """Best-effort values read from the running system — never raises."""
    import pwd
    import socket

    fallbacks: dict[str, str] = {}

    try:
        fallbacks[KEY_HOSTNAME] = socket.gethostname()
    except Exception:
        pass

    try:
        pw = pwd.getpwuid(os.getuid())
        # Never fall back to root — pkexec/kanalctl runs as uid 0 and we must
        # not propagate "root" as the machine username into machine.nix.
        if pw.pw_name != "root":
            fallbacks[KEY_USERNAME] = pw.pw_name
            fallbacks[KEY_USERDESC] = pw.pw_gecos.split(",")[0] or pw.pw_name
    except Exception:
        pass

    try:
        tz_path = Path("/etc/localtime").resolve()
        idx = str(tz_path).find("zoneinfo/")
        if idx != -1:
            fallbacks[KEY_TIMEZONE] = str(tz_path)[idx + len("zoneinfo/"):]
    except Exception:
        pass

    try:
        locale_str = os.environ.get("LANG") or os.environ.get("LC_ALL", "")
        if locale_str:
            fallbacks[KEY_LOCALE] = locale_str
    except Exception:
        pass

    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("VERSION_ID="):
                fallbacks[KEY_STATEVERSION] = line.split("=", 1)[1].strip('"')
                break
    except Exception:
        pass

    return fallbacks

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_machine() -> dict[str, str]:
    """Return machine-specific settings from machine.nix (no root required).

    Any field absent from the file is filled in from the live system.
    """
    keys = [
        KEY_HOSTNAME, KEY_USERNAME, KEY_USERDESC,
        KEY_TIMEZONE, KEY_LOCALE, KEY_KBLAYOUT, KEY_STATEVERSION,
    ]
    result: dict[str, str] = {k: "" for k in keys}

    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
        for k in keys:
            v = _get_value(contents, k)
            if v is not None:
                result[k] = v

    for k, v in _env_fallbacks().items():
        if not result.get(k):
            result[k] = v

    return result


def save_machine(settings: dict[str, str]) -> None:
    """Write *settings* to machine.nix (must be called as root).

    Keys absent from *settings* are left unchanged in the file.
    """
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
    else:
        contents = _DEFAULT_MACHINE
    for key, value in settings.items():
        if value:
            contents = _upsert_value(contents, key, value)

    if DRY_RUN:
        print(f"[kanal dry-run] would write to {MACHINE_PATH}:\n{contents}", flush=True)
        return

    MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACHINE_PATH.write_text(contents)


def read_features() -> dict[str, bool]:
    """Return ``{KEY_FEATURE_*: bool}`` from machine.nix (no root required)."""
    result = {k: False for k in ALL_FEATURES}
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
        for k in ALL_FEATURES:
            if _get_value(contents, k) == "true":
                result[k] = True
    return result


def save_features(features: dict[str, bool]) -> None:
    """Write feature flags to machine.nix (must be called as root)."""
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
    else:
        contents = _DEFAULT_MACHINE
    for key, enabled in features.items():
        if enabled:
            contents = _upsert_bool(contents, key, True)
        else:
            contents = _remove_key(contents, key)

    # Sync tailscale-status into the GNOME extensions list automatically.
    if KEY_FEATURE_TAILSCALE in features:
        exts = _get_list(contents, KEY_GNOME_EXTENSIONS) or []
        tailscale_on = features[KEY_FEATURE_TAILSCALE]
        if tailscale_on and TAILSCALE_EXT_ID not in exts:
            exts = exts + [TAILSCALE_EXT_ID]
            contents = _upsert_list(contents, KEY_GNOME_EXTENSIONS, exts)
        elif not tailscale_on and TAILSCALE_EXT_ID in exts:
            exts = [e for e in exts if e != TAILSCALE_EXT_ID]
            if exts:
                contents = _upsert_list(contents, KEY_GNOME_EXTENSIONS, exts)
            else:
                contents = _remove_key(contents, KEY_GNOME_EXTENSIONS)

    if DRY_RUN:
        print(f"[kanal dry-run] would write features to {MACHINE_PATH}:\n{contents}", flush=True)
        return

    MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACHINE_PATH.write_text(contents)


def read_apps() -> list[str]:
    """Return the list of Flatpak app IDs from machine.nix (no root required)."""
    if MACHINE_PATH.exists():
        result = _get_list(MACHINE_PATH.read_text(), KEY_FLATPAK_PACKAGES)
        if result is not None:
            return result
    return []


def save_apps(app_ids: list[str]) -> None:
    """Write Flatpak package list to machine.nix (must be called as root)."""
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
    else:
        contents = _DEFAULT_MACHINE

    if app_ids:
        contents = _upsert_list(contents, KEY_FLATPAK_PACKAGES, app_ids)
    else:
        contents = _remove_key(contents, KEY_FLATPAK_PACKAGES)

    if DRY_RUN:
        print(f"[kanal dry-run] would write apps to {MACHINE_PATH}:\n{contents}", flush=True)
        return

    MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACHINE_PATH.write_text(contents)


def read_extensions() -> list[str]:
    """Return the list of enabled GNOME extension IDs from machine.nix (no root required)."""
    if MACHINE_PATH.exists():
        result = _get_list(MACHINE_PATH.read_text(), KEY_GNOME_EXTENSIONS)
        if result is not None:
            return result
    return []


def save_extensions(ext_ids: list[str]) -> None:
    """Write GNOME extensions list to machine.nix (must be called as root)."""
    if MACHINE_PATH.exists():
        contents = MACHINE_PATH.read_text()
    else:
        contents = _DEFAULT_MACHINE

    if ext_ids:
        contents = _upsert_list(contents, KEY_GNOME_EXTENSIONS, ext_ids)
    else:
        contents = _remove_key(contents, KEY_GNOME_EXTENSIONS)

    if DRY_RUN:
        print(f"[kanal dry-run] would write extensions to {MACHINE_PATH}:\n{contents}", flush=True)
        return

    MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACHINE_PATH.write_text(contents)
