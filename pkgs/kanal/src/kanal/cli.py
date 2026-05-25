"""kanal.cli — kanalctl terminal interface.

Subcommands
-----------
status [--json]
    Print current channel and operation.
set <channel> [boot|switch]
    Write channel (and optionally operation) to flake.nix / machine.nix.
    Must be run as root (pkexec kanalctl set …).
apply <channel> <boot|switch>
    Write channel + operation, then run nixos-rebuild directly.
    Must be run as root (pkexec kanalctl apply …).
set-machine --hostname H --username U --userdesc D --timezone T --locale L --kblayout K
    Write machine-specific settings to machine.nix.
    Must be run as root (pkexec kanalctl set-machine …).
"""

from __future__ import annotations

import argparse
import json
import sys

from kanal import backend


def _cmd_status(args: argparse.Namespace) -> int:
    status = backend.read_status()
    if args.json:
        print(status.to_json())
    else:
        print(f"Channel  : {status.channel} ({status.flake_output})")
        print(f"Operation: {status.operation}")
        print(f"File     : {status.overrides_path}")
        print(f"Preset   : {status.preset}")
    return 0


def _cmd_set(args: argparse.Namespace) -> int:
    try:
        backend.set_channel(args.channel, args.operation, args.preset,
                            flake_url=getattr(args, "flake_url", None))
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Channel set to {args.channel}")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    try:
        backend.set_channel(args.channel, args.operation, args.preset,
                            flake_url=getattr(args, "flake_url", None))
    except (ValueError, OSError) as exc:
        print(f"Error saving: {exc}", file=sys.stderr)
        return 1

    print(f"Channel set to {args.channel} — running nixos-rebuild {args.operation}", flush=True)
    rc, _err = backend.run_upgrade(args.channel, args.operation)
    if rc == 0:
        print("Done.", flush=True)
    else:
        print(f"nixos-rebuild failed (exit {rc})", file=sys.stderr, flush=True)
    return rc


def _cmd_set_machine(args: argparse.Namespace) -> int:
    settings = {}
    for mf in backend.MACHINE_FIELDS:
        dest = mf["cli_flag"][2:].replace("-", "_")
        val = getattr(args, dest, None)
        if val is not None:
            settings[mf["nix_key"]] = val
    try:
        backend.save_machine(settings)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Machine settings saved.", flush=True)
    if args.rebuild:
        status = backend.read_status()
        print(f"Running nixos-rebuild {status.operation}…", flush=True)
        rc, _ = backend.run_upgrade(status.channel, status.operation)
        if rc != 0:
            print(f"nixos-rebuild failed (exit {rc})", file=sys.stderr, flush=True)
        return rc
    return 0


def _cmd_set_features(args: argparse.Namespace) -> int:
    features: dict[str, bool] = {}
    for f in backend.FEATURE_CATALOG:
        dest = f["id"].replace("-", "_")
        val = getattr(args, dest, None)
        if val is not None:
            features[f["key"]] = val
    try:
        backend.save_features(features)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Feature flags saved.", flush=True)
    if args.rebuild:
        status = backend.read_status()
        print(f"Running nixos-rebuild {status.operation}…", flush=True)
        rc, _ = backend.run_upgrade(status.channel, status.operation)
        if rc != 0:
            print(f"nixos-rebuild failed (exit {rc})", file=sys.stderr, flush=True)
        return rc
    return 0


def _cmd_set_apps(args: argparse.Namespace) -> int:
    app_ids: list[str] = args.apps or []
    try:
        backend.save_apps(app_ids)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("Flatpak app list saved.", flush=True)
    if args.rebuild:
        status = backend.read_status()
        print(f"Running nixos-rebuild {status.operation}…", flush=True)
        rc, _ = backend.run_upgrade(status.channel, status.operation)
        if rc != 0:
            print(f"nixos-rebuild failed (exit {rc})", file=sys.stderr, flush=True)
        return rc
    return 0


def _cmd_set_extensions(args: argparse.Namespace) -> int:
    ext_ids: list[str] = args.extensions or []
    try:
        backend.save_extensions(ext_ids)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("GNOME extension list saved.", flush=True)
    if args.rebuild:
        status = backend.read_status()
        print(f"Running nixos-rebuild {status.operation}…", flush=True)
        rc, _ = backend.run_upgrade(status.channel, status.operation)
        if rc != 0:
            print(f"nixos-rebuild failed (exit {rc})", file=sys.stderr, flush=True)
        return rc
    return 0


def _cmd_save_all(args: argparse.Namespace) -> int:
    """Save features, apps, extensions, and machine settings in one root call."""
    features = json.loads(args.features_json) if args.features_json else {}
    app_ids  = args.apps       if args.apps       is not None else []
    ext_ids  = args.extensions if args.extensions is not None else []
    settings: dict[str, str] = {}
    for mf in backend.MACHINE_FIELDS:
        dest = mf["cli_flag"][2:].replace("-", "_")
        val = getattr(args, dest, None)
        if val is not None:
            settings[mf["nix_key"]] = val
    try:
        if features:  backend.save_features(features)
        backend.save_apps(app_ids)
        backend.save_extensions(ext_ids)
        if settings: backend.save_machine(settings)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print("All settings saved.", flush=True)
    if args.rebuild:
        try:
            backend.set_channel(args.channel, args.operation, args.preset,
                                flake_url=getattr(args, "flake_url", None))
        except (ValueError, OSError) as exc:
            print(f"Error setting channel: {exc}", file=sys.stderr)
            return 1
        print(f"Running nixos-rebuild {args.operation}\u2026", flush=True)
        rc, _ = backend.run_upgrade(args.channel, args.operation)
        if rc != 0:
            print(f"nixos-rebuild failed (exit {rc})", file=sys.stderr, flush=True)
        return rc
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kanalctl",
        description="Manage the notenix update channel.",
    )
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    # status
    st = sub.add_parser("status", help="Show current channel and operation")
    st.add_argument("--json", action="store_true", help="Output as JSON")
    st.set_defaults(func=_cmd_status)

    # set
    s = sub.add_parser("set", help="Set the channel (requires root)")
    s.add_argument("channel")
    s.add_argument("operation", choices=["boot", "switch"], nargs="?", default=None,
                   help="Omit to keep existing / use module default")
    s.add_argument("--preset", default=None,
                   help="Preset id (validated per-channel)")
    s.add_argument("--flake-url", dest="flake_url", default=None,
                   help="Explicit flake URL (bypasses metadata cache)")
    s.set_defaults(func=_cmd_set)

    # apply
    a = sub.add_parser("apply", help="Set channel and run nixos-rebuild now (requires root)")
    a.add_argument("channel")
    a.add_argument("operation", choices=["boot", "switch"])
    a.add_argument("--preset", default=None,
                   help="Preset id (validated per-channel)")
    a.add_argument("--flake-url", dest="flake_url", default=None,
                   help="Explicit flake URL (bypasses metadata cache)")
    a.set_defaults(func=_cmd_apply)

    # set-machine
    m = sub.add_parser("set-machine", help="Save machine-specific settings (requires root)")
    for mf in backend.MACHINE_FIELDS:
        m.add_argument(mf["cli_flag"], default=None)
    m.add_argument("--rebuild", action="store_true", help="Run nixos-rebuild after saving")
    m.set_defaults(func=_cmd_set_machine)

    # set-features
    f = sub.add_parser("set-features", help="Enable/disable optional features (requires root)")
    for feat in backend.FEATURE_CATALOG:
        flag = feat["id"].replace("_", "-")
        dest = feat["id"]
        f.add_argument(f"--{flag}",    dest=dest, action="store_true",  default=None)
        f.add_argument(f"--no-{flag}", dest=dest, action="store_false")
    f.add_argument("--rebuild", action="store_true", help="Run nixos-rebuild after saving")
    f.set_defaults(func=_cmd_set_features)

    # set-apps
    ap = sub.add_parser("set-apps", help="Set Flatpak app list (requires root)")
    ap.add_argument("apps", nargs="*", metavar="APP_ID",
                    help="Flatpak app IDs to install (replaces current list; omit all to clear)")
    ap.add_argument("--rebuild", action="store_true", help="Run nixos-rebuild after saving")
    ap.set_defaults(func=_cmd_set_apps)

    # set-extensions
    ex = sub.add_parser("set-extensions", help="Set enabled GNOME extensions (requires root)")
    ex.add_argument("extensions", nargs="*", metavar="EXT_ID",
                    help="Extension IDs to enable (replaces current list; omit all to clear)")
    ex.add_argument("--rebuild", action="store_true", help="Run nixos-rebuild after saving")
    ex.set_defaults(func=_cmd_set_extensions)

    # save-all
    sa = sub.add_parser("save-all", help="Save all settings atomically (requires root)")
    sa.add_argument("--features-json", dest="features_json", default=None,
                    help="JSON object mapping feature keys to booleans")
    sa.add_argument("--apps",       nargs="*", default=None, metavar="APP_ID")
    sa.add_argument("--extensions", nargs="*", default=None, metavar="EXT_ID")
    for mf in backend.MACHINE_FIELDS:
        sa.add_argument(mf["cli_flag"], default=None)
    sa.add_argument("--rebuild",   action="store_true", help="Save + run nixos-rebuild")
    sa.add_argument("--channel",   default=None)
    sa.add_argument("--operation", choices=["boot", "switch"], default=None)
    sa.add_argument("--preset",    default=None)
    sa.add_argument("--flake-url", dest="flake_url", default=None)
    sa.set_defaults(func=_cmd_save_all)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)
