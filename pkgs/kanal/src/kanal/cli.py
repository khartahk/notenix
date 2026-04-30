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
    if args.hostname:  settings[backend.KEY_HOSTNAME]     = args.hostname
    if args.username:  settings[backend.KEY_USERNAME]     = args.username
    if args.userdesc is not None: settings[backend.KEY_USERDESC] = args.userdesc
    if args.timezone:  settings[backend.KEY_TIMEZONE]     = args.timezone
    if args.locale:    settings[backend.KEY_LOCALE]       = args.locale
    if args.kblayout:  settings[backend.KEY_KBLAYOUT]     = args.kblayout
    if args.stateversion: settings[backend.KEY_STATEVERSION] = args.stateversion
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
    if args.ssh is not None:   features[backend.KEY_FEATURE_SSH]   = args.ssh
    if args.kiosk is not None: features[backend.KEY_FEATURE_KIOSK] = args.kiosk
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
    m.add_argument("--hostname",     default=None)
    m.add_argument("--username",     default=None)
    m.add_argument("--userdesc",     default=None)
    m.add_argument("--timezone",     default=None)
    m.add_argument("--locale",       default=None)
    m.add_argument("--kblayout",     default=None)
    m.add_argument("--stateversion", default=None)
    m.add_argument("--rebuild", action="store_true", help="Run nixos-rebuild after saving")
    m.set_defaults(func=_cmd_set_machine)

    # set-features
    f = sub.add_parser("set-features", help="Enable/disable optional features (requires root)")
    f.add_argument("--ssh",    dest="ssh",   action="store_true",  default=None)
    f.add_argument("--no-ssh", dest="ssh",   action="store_false")
    f.add_argument("--kiosk",    dest="kiosk", action="store_true",  default=None)
    f.add_argument("--no-kiosk", dest="kiosk", action="store_false")
    f.add_argument("--rebuild", action="store_true", help="Run nixos-rebuild after saving")
    f.set_defaults(func=_cmd_set_features)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)
