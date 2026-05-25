"""kanal.privileged — subprocess helpers that require root (via pkexec).

All public functions in this module either:
- run ``nixos-rebuild`` directly (already root, called from kanalctl), or
- invoke ``pkexec kanalctl <subcommand>`` to obtain root for a single operation.

The streaming variants (``*_stream``) yield log lines as strings and then a
final ``(None, returncode)`` sentinel so the GUI can update in real time.
"""

from __future__ import annotations

import os
import subprocess

from kanal.constants import (
    DRY_RUN,
    FLAKE_REF,
    KANALCTL_BIN,
    KEY_FEATURE_KIOSK,
    KEY_FEATURE_NVIDIA,
    KEY_FEATURE_RUSTDESK,
    KEY_FEATURE_SSH,
    KEY_FEATURE_CANON_PRINTER,
    KEY_FEATURE_ZFS,
    KEY_FEATURE_TAILSCALE,
    KEY_FEATURE_LOGITECH_WIRELESS,
    KEY_HOSTNAME,
    KEY_KBLAYOUT,
    KEY_LOCALE,
    KEY_STATEVERSION,
    KEY_TIMEZONE,
    KEY_USERDESC,
    KEY_USERNAME,
    LOCAL_FLAKE_ATTR,
    LOCAL_FLAKE_PATH,
    NIX_BIN,
    NIXOS_REBUILD_BIN,
)

# Mapping from machine.nix key to kanalctl --flag
_MACHINE_FLAGS: dict[str, str] = {
    KEY_HOSTNAME:     "--hostname",
    KEY_USERNAME:     "--username",
    KEY_USERDESC:     "--userdesc",
    KEY_TIMEZONE:     "--timezone",
    KEY_LOCALE:       "--locale",
    KEY_KBLAYOUT:     "--kblayout",
    KEY_STATEVERSION: "--stateversion",
}

# ---------------------------------------------------------------------------
# Direct rebuild (already root — called from kanalctl apply / set-machine)
# ---------------------------------------------------------------------------

def run_upgrade(channel: str, operation: str) -> tuple[int, str]:
    """Update the flake lock file and run ``nixos-rebuild``.

    Streams combined stdout+stderr to our own stdout so the GUI can capture it.
    Returns ``(returncode, "")``.
    """
    flake_dir = str(LOCAL_FLAKE_PATH.parent)
    flake_arg = f"path:/etc/nixos#{LOCAL_FLAKE_ATTR}"

    print("Updating flake inputs…", flush=True)
    update = subprocess.Popen(
        [str(NIX_BIN), "flake", "update", "--flake", flake_dir],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for line in update.stdout:
        print(line, end="", flush=True)
    update.wait()
    if update.returncode != 0:
        print(f"nix flake update failed (exit {update.returncode})", flush=True)
        return update.returncode, ""

    proc = subprocess.Popen(
        [str(NIXOS_REBUILD_BIN), operation, "--flake", flake_arg],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for line in proc.stdout:
        print(line, end="", flush=True)
    proc.wait()
    return proc.returncode, ""

# ---------------------------------------------------------------------------
# pkexec helpers — prompt for root once, then run the kanalctl subcommand
# ---------------------------------------------------------------------------

def pkexec_set(
    channel: str,
    operation: str | None,
    preset: str | None = None,
    flake_url: str | None = None,
) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl set`` — saves channel/preset/operation only."""
    if DRY_RUN:
        print(f"[kanal dry-run] pkexec_set({channel!r}, {operation!r}, {preset!r}, url={flake_url!r})", flush=True)
        return 0, ""
    cmd = ["pkexec", KANALCTL_BIN, "set", channel]
    if operation is not None:
        cmd.append(operation)
    if preset is not None:
        cmd += ["--preset", preset]
    if flake_url is not None:
        cmd += ["--flake-url", flake_url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stderr.strip() or r.stdout.strip()


def pkexec_apply(
    channel: str,
    operation: str,
    preset: str | None = None,
    flake_url: str | None = None,
) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl apply`` — saves + runs nixos-rebuild."""
    if DRY_RUN:
        print(f"[kanal dry-run] pkexec_apply({channel!r}, {operation!r}, {preset!r}, url={flake_url!r})", flush=True)
        return 0, ""
    cmd = ["pkexec", KANALCTL_BIN, "apply", channel, operation]
    if preset is not None:
        cmd += ["--preset", preset]
    if flake_url is not None:
        cmd += ["--flake-url", flake_url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.returncode, r.stderr.strip() or r.stdout.strip()


def pkexec_apply_stream(
    channel: str,
    operation: str,
    preset: str | None = None,
    flake_url: str | None = None,
):
    """Like ``pkexec_apply`` but yields log lines, then ``(None, returncode)``."""
    if DRY_RUN:
        yield f"[kanal dry-run] pkexec_apply({channel!r}, {operation!r}, {preset!r}, url={flake_url!r})\n"
        yield None, 0
        return
    cmd = ["pkexec", KANALCTL_BIN, "apply", channel, operation]
    if preset is not None:
        cmd += ["--preset", preset]
    if flake_url is not None:
        cmd += ["--flake-url", flake_url]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


def pkexec_save_machine(settings: dict[str, str]) -> tuple[int, str]:
    """Invoke ``pkexec kanalctl set-machine`` — saves machine.nix only."""
    if DRY_RUN:
        print(f"[kanal dry-run] pkexec_save_machine({settings!r})", flush=True)
        return 0, ""
    cmd = ["pkexec", KANALCTL_BIN, "set-machine"]
    for key, flag in _MACHINE_FLAGS.items():
        if settings.get(key):
            cmd += [flag, settings[key]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stderr.strip() or r.stdout.strip()


def pkexec_save_machine_stream(settings: dict[str, str]):
    """Invoke ``pkexec kanalctl set-machine --rebuild`` and stream output."""
    if DRY_RUN:
        yield f"[kanal dry-run] pkexec_save_machine({settings!r})\n"
        yield None, 0
        return
    cmd = ["pkexec", KANALCTL_BIN, "set-machine", "--rebuild"]
    for key, flag in _MACHINE_FLAGS.items():
        if settings.get(key):
            cmd += [flag, settings[key]]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


def pkexec_save_features_stream(features: dict[str, bool], rebuild: bool = True):
    """Invoke ``pkexec kanalctl set-features`` and stream output."""
    if DRY_RUN:
        yield f"[kanal dry-run] set-features: {features!r}\n"
        yield None, 0
        return
    cmd = ["pkexec", KANALCTL_BIN, "set-features"]
    for key, enabled in features.items():
        flag = {KEY_FEATURE_SSH: "--ssh", KEY_FEATURE_KIOSK: "--kiosk", KEY_FEATURE_RUSTDESK: "--rustdesk", KEY_FEATURE_NVIDIA: "--nvidia", KEY_FEATURE_CANON_PRINTER: "--canon-printer", KEY_FEATURE_ZFS: "--zfs", KEY_FEATURE_TAILSCALE: "--tailscale", KEY_FEATURE_LOGITECH_WIRELESS: "--logitech-wireless"}.get(key)
        if flag:
            cmd.append(flag if enabled else flag.replace("--", "--no-"))
    if rebuild:
        cmd.append("--rebuild")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


def pkexec_save_apps_stream(app_ids: list[str], rebuild: bool = True):
    """Invoke ``pkexec kanalctl set-apps`` and stream output."""
    if DRY_RUN:
        yield f"[kanal dry-run] set-apps: {app_ids!r}\n"
        yield None, 0
        return
    cmd = ["pkexec", KANALCTL_BIN, "set-apps"] + app_ids
    if rebuild:
        cmd.append("--rebuild")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode


def pkexec_save_extensions_stream(ext_ids: list[str], rebuild: bool = True):
    """Invoke ``pkexec kanalctl set-extensions`` and stream output."""
    if DRY_RUN:
        yield f"[kanal dry-run] set-extensions: {ext_ids!r}\n"
        yield None, 0
        return
    cmd = ["pkexec", KANALCTL_BIN, "set-extensions"] + ext_ids
    if rebuild:
        cmd.append("--rebuild")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    for line in proc.stdout:
        yield line
    proc.wait()
    yield None, proc.returncode
