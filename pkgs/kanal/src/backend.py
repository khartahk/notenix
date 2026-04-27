"""kanal.backend — file editing and status logic.

This module owns all reads/writes to the overrides file and is the single
source of truth for channel→flake-output mapping.  Neither the GUI nor the
CLI call subprocesses directly for file operations; they go through here.

The nixos-rebuild invocation (privileged) is intentionally kept here too so
both callers share identical argument lists.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OVERRIDES_PATH    = Path("/etc/nixos/notenix-install-overrides.nix")
FLAKE_REPO        = "github:n1x05/notenix"
NIXOS_REBUILD_BIN = Path("/run/current-system/sw/bin/nixos-rebuild")
NIX_BIN           = Path("/run/current-system/sw/bin/nix")

# Flake URLs per channel — unstable uses the /unstable branch, stable uses main (default)
CHANNELS: dict[str, str] = {
    "stable":   "github:n1x05/notenix",
    "unstable": "github:n1x05/notenix/unstable",
}

KEY_FLAKE  = "notenix.system.autoupgrade.flakeRepo"
KEY_OP     = "notenix.system.autoupgrade.operation"
KEY_PRESET = "notenix.preset"

PRESETS: list[str] = ["desktop", "minimal"]

# Injected by the Nix build via makeWrapper --set KANALCTL_BIN <store-path>.
# Falls back to PATH for local development.
_SELF = os.environ.get("KANALCTL_BIN", "kanalctl")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Status:
    channel:        str   # "stable" | "unstable"
    flake_output:   str   # full flake URL for this channel
    preset:         str   # "desktop" | "minimal"
    operation:      str   # "boot" | "switch"
    overrides_path: str

    def to_dict(self) -> dict:
        return {
            "channel":        self.channel,
            "flake_output":   self.flake_output,
            "preset":         self.preset,
            "operation":      self.operation,
            "overrides_path": self.overrides_path,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ---------------------------------------------------------------------------
# File helpers (no root required — read-only)
# ---------------------------------------------------------------------------

def _get_value(contents: str, key: str) -> str | None:
    """Extract the value from a  key = lib.mkForce "value";  line."""
    for line in contents.splitlines():
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            after = t.split("=", 1)[1].strip()
            after = re.sub(r"^lib\.mkForce\s*", "", after)
            return after.strip('" ;')
    return None


def _upsert_value(contents: str, key: str, value: str) -> str:
    """Replace an existing assignment or insert one before the closing }."""
    new_line = f'  {key} = lib.mkForce "{value}";'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            lines[i] = new_line + "\n"
            return "".join(lines)
    # Not found — insert before last }
    joined = "".join(lines)
    pos = joined.rfind("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _remove_key(contents: str, key: str) -> str:
    """Remove a key assignment (reset to module default)."""
    lines = [
        ln for ln in contents.splitlines(keepends=True)
        if not (ln.strip().startswith(key) and
                ln.strip()[len(key):].lstrip().startswith("="))
    ]
    return "".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_status() -> Status:
    """Read current channel/operation from the overrides file (no root)."""
    path = OVERRIDES_PATH
    channel   = "stable"
    preset    = "desktop"
    operation = "boot"

    if path.exists():
        contents  = path.read_text()
        raw_flake  = _get_value(contents, KEY_FLAKE)
        raw_op     = _get_value(contents, KEY_OP)
        raw_preset = _get_value(contents, KEY_PRESET)

        if raw_flake == CHANNELS["unstable"]:
            channel = "unstable"
        if raw_op in ("boot", "switch"):
            operation = raw_op
        if raw_preset in PRESETS:
            preset = raw_preset

    return Status(
        channel        = channel,
        flake_output   = CHANNELS[channel],
        preset         = preset,
        operation      = operation,
        overrides_path = str(path),
    )


def set_channel(channel: str, operation: str | None = None, preset: str | None = None) -> None:
    """Write channel, preset and optionally operation to the overrides file.

    Must be called as root (e.g. via ``pkexec kanalctl set …``).
    Raises RuntimeError on failure.
    """
    if channel not in CHANNELS:
        raise ValueError(f"Unknown channel: {channel!r}. Valid: {list(CHANNELS)}")
    if operation is not None and operation not in ("boot", "switch"):
        raise ValueError(f"Unknown operation: {operation!r}. Valid: boot, switch")
    if preset is not None and preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset!r}. Valid: {PRESETS}")

    path = OVERRIDES_PATH
    if path.exists():
        contents = path.read_text()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        contents = "{ lib, ... }:\n{\n}\n"

    contents = _upsert_value(contents, KEY_FLAKE, CHANNELS[channel])

    if preset is not None:
        contents = _upsert_value(contents, KEY_PRESET, preset)

    if operation is not None:
        contents = _upsert_value(contents, KEY_OP, operation)
    else:
        contents = _remove_key(contents, KEY_OP)

    path.write_text(contents)


def run_upgrade(channel: str, operation: str) -> tuple[int, str]:
    """Trigger nixos-upgrade.service (already root via pkexec kanalctl apply).

    Returns (returncode, error_output).
    """
    result = subprocess.run(
        ["/run/current-system/sw/bin/systemctl", "start", "nixos-upgrade.service"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    err = result.stderr.strip() or result.stdout.strip()
    return result.returncode, err


def pkexec_set(channel: str, operation: str | None, preset: str | None = None) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl set`` — one password prompt, saves only."""
    cmd = ["pkexec", _SELF, "set", channel]
    if operation is not None:
        cmd.append(operation)  # positional arg
    if preset is not None:
        cmd += ["--preset", preset]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stderr.strip() or r.stdout.strip()


def pkexec_apply(channel: str, operation: str, preset: str | None = None) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl apply`` — one password prompt, saves + upgrades."""
    cmd = ["pkexec", _SELF, "apply", channel, operation]
    if preset is not None:
        cmd += ["--preset", preset]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stderr.strip() or r.stdout.strip())
