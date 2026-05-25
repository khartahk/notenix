"""kanal.backend — compatibility façade.

All symbols are re-exported from their canonical homes so that existing callers
(``cli.py``, ``gui/window.py``) continue to work with no changes:

    from kanal import backend
    backend.read_status()      # still works
    backend.DRY_RUN            # still works
"""

from __future__ import annotations

# Constants
import kanal.constants as _const
from kanal.constants import (
    ALL_FEATURES,
    DRY_RUN,
    FEATURE_CATALOG,
    TAB_CATALOG,
    FLAKE_REPO,
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
    MACHINE_FIELDS,
    MACHINE_GROUPS,
    MACHINE_KEY_FLAGS,
    MACHINE_PATH,
    get_feature_catalog,
    get_tab_catalog,
)

# Re-export all KEY_FEATURE_* symbols generated in constants
for _f in FEATURE_CATALOG:
    globals()[f"KEY_FEATURE_{_f['const']}"] = getattr(_const, f"KEY_FEATURE_{_f['const']}")

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
    pkexec_save_all_stream,
    run_upgrade,
)

__all__ = [
    # constants — catalog (YAML-derived)
    "ALL_FEATURES", "DRY_RUN", "FEATURE_CATALOG", "FLAKE_REPO", "TAB_CATALOG",
    *[f"KEY_FEATURE_{f['const']}" for f in FEATURE_CATALOG],
    "get_feature_catalog", "get_tab_catalog",
    "KEY_FLATPAK_PACKAGES", "KEY_GNOME_EXTENSIONS",
    # constants — machine keys (YAML-derived)
    "KEY_HOSTNAME", "KEY_KBLAYOUT", "KEY_LOCALE", "KEY_OP", "KEY_PRESET",
    "KEY_STATEVERSION", "KEY_TIMEZONE", "KEY_USERDESC", "KEY_USERNAME",
    "LOCAL_FLAKE_PATH", "MACHINE_FIELDS", "MACHINE_GROUPS", "MACHINE_KEY_FLAGS", "MACHINE_PATH",
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
    "pkexec_save_all_stream", "run_upgrade",
]
