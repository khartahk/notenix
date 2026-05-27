"""kanal.nixfiles — read and write Nix configuration files.

This module contains:
- Pure string helpers that parse and patch Nix file content
  (``_get_value``, ``_upsert_value``, ``_upsert_bool``, ``_remove_key``,
  ``_get_flake_url``, ``_set_flake_url``)
- High-level functions that read/write the actual files on disk
  (``read_status``, ``set_channel``)

The string helpers are pure functions with no I/O — easy to unit-test.
``read_status`` and ``set_channel`` are the only functions that touch the
filesystem; they require root for writes (called via ``pkexec kanalctl``).
"""

from __future__ import annotations

import re

import kanal.constants as _const
from kanal.metadata import Status, channels, load_metadata, presets_for

# ---------------------------------------------------------------------------
# Nix flake.nix templates
# ---------------------------------------------------------------------------

_CORRECT_OUTPUTS = (
    "  outputs = {{ notenix, ... }}: {{\n"
    "    nixosConfigurations.notenix =\n"
    "      notenix.lib.mkMachineSystem {{ modules = [ ./machine.nix ]; }};\n"
    "  }};\n"
)

_CANONICAL_FLAKE = (
    "{{\n"
    "  inputs.notenix.url = \"{url}\";\n"
    + _CORRECT_OUTPUTS
    + "}}\n"
)

_DEFAULT_FLAKE = (
    "{\n"
    "  inputs.notenix.url = \"github:n1x05/notenix\";\n"
    "  outputs = { notenix, ... }: {\n"
    "    nixosConfigurations.notenix =\n"
    "      notenix.lib.mkMachineSystem { modules = [ ./machine.nix ]; };\n"
    "  };\n"
    "}\n"
)

_DEFAULT_MACHINE = "{ lib, ... }:\n{\n}\n"

# ---------------------------------------------------------------------------
# Pure string helpers — no I/O
# ---------------------------------------------------------------------------

def _get_flake_url(contents: str) -> str | None:
    """Extract the notenix input URL from flake.nix text."""
    for line in contents.splitlines():
        t = line.strip()
        if t.startswith("inputs.notenix.url"):
            m = re.search(r'"([^"]+)"', t)
            if m:
                return m.group(1)
    return None


def _set_flake_url(contents: str, url: str) -> str:
    """Patch ``inputs.notenix.url`` in flake.nix text.

    Rewrites the entire outputs block to the canonical form when the existing
    file predates the ``nixosConfigurations`` output (old machines).
    """
    if "nixosConfigurations" not in contents:
        return _CANONICAL_FLAKE.format(url=url)

    new_line = f'  inputs.notenix.url = "{url}";'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().startswith("inputs.notenix.url"):
            lines[i] = new_line + "\n"
            return "".join(lines)
    # Key not found — insert before the first closing brace
    joined = "".join(lines)
    pos = joined.find("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _get_value(contents: str, key: str) -> str | None:
    """Extract the value from a ``key = lib.mkForce "value";`` line."""
    for line in contents.splitlines():
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            after = t.split("=", 1)[1].strip()
            after = re.sub(r"^lib\.mkForce\s*", "", after)
            return after.strip('" ;')
    return None


def _upsert_value(contents: str, key: str, value: str) -> str:
    """Replace an existing string assignment or insert one before the last ``}``."""
    new_line = f'  {key} = lib.mkForce "{value}";'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            lines[i] = new_line + "\n"
            return "".join(lines)
    joined = "".join(lines)
    pos = joined.rfind("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _upsert_bool(contents: str, key: str, value: bool) -> str:
    """Like ``_upsert_value`` but writes a bare Nix boolean (``true``/``false``)."""
    nix_val  = "true" if value else "false"
    new_line = f'  {key} = lib.mkForce {nix_val};'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            lines[i] = new_line + "\n"
            return "".join(lines)
    joined = "".join(lines)
    pos = joined.rfind("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"


def _remove_key(contents: str, key: str) -> str:
    """Remove a key assignment line (resets option to the module default)."""
    return "".join(
        ln for ln in contents.splitlines(keepends=True)
        if not (
            ln.strip().startswith(key)
            and ln.strip()[len(key):].lstrip().startswith("=")
        )
    )


def _get_list(contents: str, key: str) -> list[str] | None:
    """Extract a Nix list value from ``key = lib.mkForce [ "a" "b" ];``.

    Returns ``None`` if the key is absent, or an empty list ``[]`` if the key
    is present but the list is empty (``[ ]``).  Only single-line lists are
    supported — multi-line lists are treated as absent.
    """
    for line in contents.splitlines():
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            after = t.split("=", 1)[1].strip()
            after = re.sub(r"^lib\.mkForce\s*", "", after).strip().rstrip(";").strip()
            if after.startswith("[") and after.endswith("]"):
                inner = after[1:-1].strip()
                if not inner:
                    return []
                return re.findall(r'"([^"]*)"', inner)
    return None


def _upsert_list(contents: str, key: str, values: list[str]) -> str:
    """Replace or insert a Nix list assignment for *key*.

    Writes a single-line ``key = lib.mkForce [ "a" "b" ];`` form.
    If *values* is empty the list is written as ``[ ]``.
    """
    items = " ".join(f'"{v}"' for v in values)
    new_line = f'  {key} = lib.mkForce [ {items}];'
    lines = contents.splitlines(keepends=True)
    for i, line in enumerate(lines):
        t = line.strip()
        if t.startswith(key) and t[len(key):].lstrip().startswith("="):
            lines[i] = new_line + "\n"
            return "".join(lines)
    joined = "".join(lines)
    pos = joined.rfind("}")
    if pos >= 0:
        return joined[:pos] + new_line + "\n" + joined[pos:]
    return joined + "\n" + new_line + "\n"

# ---------------------------------------------------------------------------
# High-level read — no root required
# ---------------------------------------------------------------------------

def read_status() -> Status:
    """Read the current channel/preset/operation from flake.nix + machine.nix."""
    meta     = load_metadata()
    ch_map   = meta["channels"]

    default_channel = next(
        (k for k, v in ch_map.items() if v.get("default")),
        next(iter(ch_map), "main"),
    )
    default_presets = presets_for(default_channel)
    default_preset  = default_presets[0] if default_presets else "desktop"

    channel   = default_channel
    preset    = default_preset
    operation = "boot"

    # Determine active channel from inputs.notenix.url in flake.nix
    if _const.LOCAL_FLAKE_PATH.exists():
        raw_url = _get_flake_url(_const.LOCAL_FLAKE_PATH.read_text())
        if raw_url:
            # Check if URL contains a tag ref (?ref=vX.Y.Z or /vX.Y.Z)
            tag_match = re.search(r'[/?]ref=(v?[\d]+\.[\d]+[^&"\s]*)', raw_url) or \
                        re.search(r'/(v\d+\.\d+[^/"]*)"?$', raw_url)
            if tag_match:
                channel = "stable"
            else:
                matched = next(
                    (k for k, v in ch_map.items() if v["flake"] == raw_url), None
                )
                if matched:
                    channel = matched

    # Determine preset and operation from machine.nix
    if _const.MACHINE_PATH.exists():
        mc = _const.MACHINE_PATH.read_text()
        raw_op     = _get_value(mc, _const.KEY_OP)
        raw_preset = _get_value(mc, _const.KEY_PRESET)

        if raw_op in ("boot", "switch"):
            operation = raw_op
        ch_presets = presets_for(channel)
        if raw_preset in ch_presets:
            preset = raw_preset
        elif ch_presets:
            preset = ch_presets[0]

    flake_url = ch_map.get(channel, {}).get("flake", _const.FLAKE_REF)
    return Status(
        channel        = channel,
        flake_output   = flake_url,
        preset         = preset,
        operation      = operation,
        overrides_path = str(_const.MACHINE_PATH),
    )

# ---------------------------------------------------------------------------
# High-level write — must be called as root (via pkexec kanalctl set/apply)
# ---------------------------------------------------------------------------

def set_channel(
    channel: str,
    operation: str | None = None,
    preset: str | None = None,
    flake_url: str | None = None,
) -> None:
    """Write channel to flake.nix and preset/operation to machine.nix.

    Raises ``ValueError`` for unknown channel/operation; ``OSError`` on I/O failure.
    """
    if operation is not None and operation not in ("boot", "switch"):
        raise ValueError(f"Unknown operation: {operation!r}. Valid: boot, switch")

    if not flake_url:
        ch_map = channels()
        if channel not in ch_map:
            raise ValueError(f"Unknown channel: {channel!r}. Valid: {list(ch_map)}")
        flake_url = ch_map[channel]

    # --- flake.nix ---
    flake_contents = (
        _const.LOCAL_FLAKE_PATH.read_text()
        if _const.LOCAL_FLAKE_PATH.exists()
        else _DEFAULT_FLAKE
    )
    flake_contents = _set_flake_url(flake_contents, flake_url)

    # --- machine.nix ---
    machine_contents = (
        _const.MACHINE_PATH.read_text()
        if _const.MACHINE_PATH.exists()
        else _DEFAULT_MACHINE
    )
    if preset is not None:
        machine_contents = _upsert_value(machine_contents, _const.KEY_PRESET, preset)
    if operation is not None:
        machine_contents = _upsert_value(machine_contents, _const.KEY_OP, operation)
    else:
        machine_contents = _remove_key(machine_contents, _const.KEY_OP)
    # Always ensure flakeRepo points to local flake so nixos-upgrade builds
    # with machine.nix included. Branch is controlled by inputs.notenix.url above.
    machine_contents = _upsert_value(machine_contents, _const.KEY_FLAKEREPO, _const.FLAKE_REPO)

    if _const.DRY_RUN:
        print(f"[kanal dry-run] would write to {_const.LOCAL_FLAKE_PATH}:\n{flake_contents}", flush=True)
        print(f"[kanal dry-run] would write to {_const.MACHINE_PATH}:\n{machine_contents}", flush=True)
        return

    _const.LOCAL_FLAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _const.LOCAL_FLAKE_PATH.write_text(flake_contents)
    _const.MACHINE_PATH.write_text(machine_contents)


def apply_release(tag: str) -> None:
    """Pin flake.nix to a specific release tag.

    Writes ``inputs.notenix.url = "github:n1x05/notenix?ref=vX.Y.Z"``
    so the next ``nix flake update`` resolves exactly that tag.
    The autoupgrade service will then rebuild to the pinned release.

    Raises ``OSError`` on I/O failure.
    """
    tag = tag.lstrip("v")
    flake_url = f"{_const.FLAKE_REF}?ref=v{tag}"

    flake_contents = (
        _const.LOCAL_FLAKE_PATH.read_text()
        if _const.LOCAL_FLAKE_PATH.exists()
        else _DEFAULT_FLAKE
    )
    flake_contents = _set_flake_url(flake_contents, flake_url)

    if _const.DRY_RUN:
        print(f"[kanal dry-run] would pin release v{tag} → {flake_url}", flush=True)
        print(f"[kanal dry-run] would write to {_const.LOCAL_FLAKE_PATH}:\n{flake_contents}", flush=True)
        return

    _const.LOCAL_FLAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _const.LOCAL_FLAKE_PATH.write_text(flake_contents)
