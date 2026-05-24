"""kanal.backend — compatibility façade.

All symbols are re-exported from their canonical homes so that existing callers
(``cli.py``, ``gui/window.py``) continue to work with no changes:

    from kanal import backend
    backend.read_status()      # still works
    backend.DRY_RUN            # still works
"""

from __future__ import annotations

# Constants
from kanal.constants import (
    ALL_FEATURES,
    DRY_RUN,
    FLATPAK_CATALOG,
    FLAKE_REPO,
    GNOME_EXTENSIONS_CATALOG,
    KEY_FEATURE_KIOSK,
    KEY_FEATURE_NVIDIA,
    KEY_FEATURE_RUSTDESK,
    KEY_FEATURE_SSH,
    KEY_FEATURE_CANON_PRINTER,
    KEY_FEATURE_ZFS,
    KEY_FEATURE_TAILSCALE,
    KEY_FLATPAK_PACKAGES,
    KEY_GNOME_EXTENSIONS,
    KEY_HOSTNAME,
    KEY_KBLAYOUT,
    KEY_LOCALE,
    KEY_OP,
    KEY_PRESET,
    KEY_STATEVERSION,
    KEY_TIMEZONE,
    KEY_USERDESC,
    KEY_USERNAME,
    LOCAL_FLAKE_PATH,
    MACHINE_PATH,
)

# Metadata
from kanal.metadata import (
    Status,
    is_cache_stale,
    load_metadata,
    refresh_metadata,
)

# Nix file read/write
from kanal.nixfiles import read_status, set_channel

# Machine settings
from kanal.machine import read_features, read_machine, save_features, save_machine, read_apps, save_apps, read_extensions, save_extensions

# Locale / keyboard helpers
from kanal.locales import kbd_default_for_locale, list_kbd_layouts, list_locales

# Privileged subprocess helpers
from kanal.privileged import (
    pkexec_apply,
    pkexec_apply_stream,
    pkexec_save_apps_stream,
    pkexec_save_extensions_stream,
    pkexec_save_features_stream,
    pkexec_save_machine,
    pkexec_save_machine_stream,
    pkexec_set,
    run_upgrade,
)

__all__ = [
    # constants
    "ALL_FEATURES", "DRY_RUN", "FLATPAK_CATALOG", "FLAKE_REPO",
    "GNOME_EXTENSIONS_CATALOG",
    "KEY_FEATURE_KIOSK", "KEY_FEATURE_NVIDIA", "KEY_FEATURE_RUSTDESK", "KEY_FEATURE_SSH",
    "KEY_FEATURE_CANON_PRINTER", "KEY_FEATURE_ZFS", "KEY_FEATURE_TAILSCALE",
    "KEY_FLATPAK_PACKAGES", "KEY_GNOME_EXTENSIONS",
    "KEY_HOSTNAME", "KEY_KBLAYOUT", "KEY_LOCALE", "KEY_OP", "KEY_PRESET",
    "KEY_STATEVERSION", "KEY_TIMEZONE", "KEY_USERDESC", "KEY_USERNAME",
    "LOCAL_FLAKE_PATH", "MACHINE_PATH",
    # metadata
    "Status", "is_cache_stale", "load_metadata", "refresh_metadata",
    # nixfiles
    "read_status", "set_channel",
    # machine
    "read_apps", "read_extensions", "read_features", "read_machine",
    "save_apps", "save_extensions", "save_features", "save_machine",
    # locales
    "kbd_default_for_locale", "list_kbd_layouts", "list_locales",
    # privileged
    "pkexec_apply", "pkexec_apply_stream", "pkexec_save_apps_stream",
    "pkexec_save_extensions_stream",
    "pkexec_save_features_stream", "pkexec_save_machine", "pkexec_save_machine_stream",
    "pkexec_set", "run_upgrade",
]
