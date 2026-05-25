"""kanal.constants — all paths, NixOS option keys, and environment-driven flags.

Nothing in this module has side effects beyond reading environment variables at
import time.  Every other module imports from here; nothing imports back.
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

LOCAL_FLAKE_PATH  = Path("/etc/nixos/flake.nix")
MACHINE_PATH      = Path("/etc/nixos/machine.nix")
LOCAL_FLAKE_ATTR  = "notenix"          # nixosConfigurations.<attr>
FLAKE_REPO        = "path:/etc/nixos"   # autoupgrade always builds from local flake
NIXOS_REBUILD_BIN = Path("/run/current-system/sw/bin/nixos-rebuild")
NIX_BIN           = Path("/run/current-system/sw/bin/nix")

# ---------------------------------------------------------------------------
# NixOS option keys written to machine.nix
# ---------------------------------------------------------------------------

KEY_OP        = "notenix.system.autoupgrade.operation"
KEY_FLAKEREPO = "notenix.system.autoupgrade.flakeRepo"
KEY_PRESET    = "notenix.preset"

# ---------------------------------------------------------------------------
# Tab catalog — loaded from default.yaml bundled in the package.
# Drives all dynamic tabs (features, extensions, apps) in the GUI.
# ---------------------------------------------------------------------------

def _load_catalog() -> dict:
    ref = importlib.resources.files("kanal").joinpath("default.yaml")
    with importlib.resources.as_file(ref) as p:
        return yaml.safe_load(p.read_text())


_CATALOG: dict = _load_catalog()

TAB_CATALOG: list[dict] = _CATALOG["tabs"]

# Convenience lookup by tab id
_TABS_BY_ID: dict[str, dict] = {t["id"]: t for t in TAB_CATALOG}

FEATURE_CATALOG: list[dict] = _TABS_BY_ID["features"]["items"]

ALL_FEATURES: list[str] = [f["key"] for f in FEATURE_CATALOG]

# Backward-compat per-feature constants: KEY_FEATURE_SSH, KEY_FEATURE_KIOSK, ...
for _f in FEATURE_CATALOG:
    globals()[f"KEY_FEATURE_{_f['const']}"] = _f["key"]

# Backward-compat catalog dicts (dict format expected by existing callers)
GNOME_EXTENSIONS_CATALOG: dict[str, tuple[str, str]] = {
    item["id"]: (item["title"], item["subtitle"])
    for item in _TABS_BY_ID["extensions"]["items"]
}

FLATPAK_CATALOG: dict[str, tuple[str, str]] = {
    item["id"]: (item["title"], item["subtitle"])
    for item in _TABS_BY_ID["apps"]["items"]
}

KEY_FLATPAK_PACKAGES: str = _TABS_BY_ID["apps"]["nix_key"]
KEY_GNOME_EXTENSIONS: str = _TABS_BY_ID["extensions"]["nix_key"]


def get_tab_catalog() -> list[dict]:
    """Return the full ordered tab catalog from default.yaml."""
    return TAB_CATALOG


def get_feature_catalog() -> list[dict]:
    """Return feature items (bool_options tab). Backward compat."""
    return FEATURE_CATALOG


KEY_HOSTNAME     = "notenix.system.install.hostName"
KEY_USERNAME     = "notenix.system.install.userName"
KEY_USERDESC     = "notenix.system.install.userDescription"
KEY_TIMEZONE     = "notenix.system.install.timeZone"
KEY_LOCALE       = "notenix.system.install.locale"
KEY_KBLAYOUT     = "notenix.system.install.keyboardLayout"
KEY_STATEVERSION = "system.stateVersion"

# ---------------------------------------------------------------------------
# Runtime flags (injected by the Nix build via makeWrapper)
# ---------------------------------------------------------------------------

# Path to the kanalctl binary; falls back to PATH for local development.
KANALCTL_BIN = os.environ.get("KANALCTL_BIN", "kanalctl")

# Flake ref used for nix eval to fetch metadata; baked in by the Nix build.
FLAKE_REF = os.environ.get("KANAL_FLAKE_REF", "github:n1x05/notenix")

# Set KANAL_DRY_RUN=1 to skip all file writes (useful for UI development).
DRY_RUN = os.environ.get("KANAL_DRY_RUN", "") not in ("", "0", "false")
