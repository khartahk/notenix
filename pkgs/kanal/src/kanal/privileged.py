"""kanal.privileged — subprocess helpers that require root (via pkexec).

All public functions in this module either:
- run ``nixos-rebuild`` directly (already root, called from kanalctl), or
- invoke ``pkexec kanalctl <subcommand>`` to obtain root for a single operation.

The streaming variants (``*_stream``) yield log lines as strings and then a
final ``(None, returncode)`` sentinel so the GUI can update in real time.
"""

from __future__ import annotations

import json
import os
import subprocess

import kanal.constants as _const

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pkexec_stream(cmd: list[str], dry_msg: str):
    """Core: dry-run guard → Popen → yield lines → (None, returncode) sentinel."""
    if _const.DRY_RUN:
        yield f"[kanal dry-run] {dry_msg}\n"
        yield None, 0
        return
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


# {nix_key: cli_flag} — loaded from default.yaml, no hardcoding needed
_MACHINE_FLAGS = _const.MACHINE_KEY_FLAGS

# ---------------------------------------------------------------------------
# Direct rebuild (already root — called from kanalctl apply / save-all)
# ---------------------------------------------------------------------------

def run_upgrade(operation: str) -> int:
    """Update the flake lock file and run ``nixos-rebuild``.

    Streams combined stdout+stderr to our own stdout so the GUI can capture it.
    Returns the nixos-rebuild exit code.
    """
    flake_dir = str(_const.LOCAL_FLAKE_PATH.parent)
    flake_arg = f"path:/etc/nixos#{_const.LOCAL_FLAKE_ATTR}"

    print("Updating flake inputs…", flush=True)
    update = subprocess.Popen(
        [str(_const.NIX_BIN), "flake", "update", "--flake", flake_dir],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for line in update.stdout:
        print(line, end="", flush=True)
    update.wait()
    if update.returncode != 0:
        print(f"nix flake update failed (exit {update.returncode})", flush=True)
        return update.returncode

    proc = subprocess.Popen(
        [str(_const.NIXOS_REBUILD_BIN), operation, "--flake", flake_arg],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for line in proc.stdout:
        print(line, end="", flush=True)
    proc.wait()
    return proc.returncode

# ---------------------------------------------------------------------------
# pkexec helpers — prompt for root once, then run the kanalctl subcommand
# ---------------------------------------------------------------------------

def pkexec_save_all_stream(payload: dict, rebuild: bool = False):
    """Invoke ``pkexec kanalctl save-all`` — one root prompt saves everything.

    payload keys: features (dict[str, bool]), extensions (list[str]),
                  apps (list[str]), machine (dict[str, str]),
                  channel (str), operation (str), preset (str), flake_url (str).
    With rebuild=True also sets the channel and runs nixos-rebuild.
    """
    cmd = ["pkexec", _const.KANALCTL_BIN, "save-all"]
    for tab in _const.TAB_CATALOG:
        tab_id = tab["id"]
        data   = payload.get(tab_id)
        if tab["type"] == "bool_options":
            cmd += [f"--{tab_id}-json", json.dumps(data if data is not None else {})]
        elif data:
            cmd += [f"--{tab_id}", *data]
    for key, flag in _MACHINE_FLAGS.items():
        if payload["machine"].get(key):
            cmd += [flag, payload["machine"][key]]
    if rebuild:
        cmd += ["--rebuild", "--channel", payload["channel"],
                "--operation", payload["operation"]]
        if payload.get("preset"):
            cmd += ["--preset", payload["preset"]]
        if payload.get("flake_url"):
            cmd += ["--flake-url", payload["flake_url"]]
    dry = f"save-all rebuild={rebuild} ch={payload.get('channel')!r} features={payload['features']}"
    yield from _pkexec_stream(cmd, dry)
