"""kanal.constants — all paths, NixOS option keys, and environment-driven flags.

Nothing in this module has side effects beyond reading environment variables at
import time.  Every other module imports from here; nothing imports back.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

LOCAL_FLAKE_PATH  = Path("/etc/nixos/flake.nix")
MACHINE_PATH      = Path("/etc/nixos/machine.nix")
LOCAL_FLAKE_ATTR  = "notenix"          # nixosConfigurations.<attr>
FLAKE_REPO        = "github:n1x05/notenix"
NIXOS_REBUILD_BIN = Path("/run/current-system/sw/bin/nixos-rebuild")
NIX_BIN           = Path("/run/current-system/sw/bin/nix")

# ---------------------------------------------------------------------------
# NixOS option keys written to machine.nix
# ---------------------------------------------------------------------------

KEY_OP           = "notenix.system.autoupgrade.operation"
KEY_FLAKEREPO    = "notenix.system.autoupgrade.flakeRepo"
KEY_PRESET       = "notenix.preset"

KEY_FEATURE_SSH      = "notenix.features.ssh"
KEY_FEATURE_KIOSK    = "notenix.features.kiosk"
KEY_FEATURE_RUSTDESK = "notenix.features.rustdesk"

ALL_FEATURES: list[str] = [KEY_FEATURE_SSH, KEY_FEATURE_KIOSK, KEY_FEATURE_RUSTDESK]

KEY_FLATPAK_PACKAGES = "notenix.applications.flatpak.packages"

# Curated list of Flatpak apps shown as checkboxes in the GUI.
# Format: { flatpak_id: (display_name, subtitle) }
FLATPAK_CATALOG: dict[str, tuple[str, str]] = {
    "org.chromium.Chromium":          ("Chromium",        "Web browser"),
    "org.signal.Signal":              ("Signal",          "Encrypted messaging"),
    "org.nextcloud.Nextcloud":        ("Nextcloud",       "Sync files and folders with Nextcloud"),
    "org.libreoffice.LibreOffice":    ("LibreOffice",     "Full office suite — Writer, Calc, Impress"),
    "com.vscodium.codium":            ("VSCodium",        "Code editor"),
    "com.obsproject.Studio":          ("OBS Studio",      "Screen recording and streaming"),
    "org.videolan.VLC":               ("VLC",             "Media player"),
    "com.github.tchx84.Flatseal":     ("Flatseal",        "Manage Flatpak permissions"),
}

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
