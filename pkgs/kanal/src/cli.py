"""kanal.cli — kanalctl terminal interface.

Subcommands
-----------
status [--json]
    Print current channel and operation.
set <stable|unstable> [boot|switch]
    Write channel (and optionally operation) to the overrides file.
    Must be run as root (pkexec kanalctl set …).
apply <stable|unstable> <boot|switch>
    Write channel + operation, then trigger nixos-upgrade.service via systemctl.
    systemctl start uses polkit for privilege escalation automatically.
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
        backend.set_channel(args.channel, args.operation, args.preset)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Channel set to {args.channel} ({backend.CHANNELS[args.channel]})")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    try:
        backend.set_channel(args.channel, args.operation, args.preset)
    except (ValueError, OSError) as exc:
        print(f"Error saving: {exc}", file=sys.stderr)
        return 1

    print(f"Channel set to {args.channel} — running nixos-rebuild {args.operation}…")
    rc, err = backend.run_upgrade(args.channel, args.operation)
    if rc == 0:
        print("Done.")
    else:
        print(f"nixos-rebuild failed:\n{err}", file=sys.stderr)
    return rc


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
    s.add_argument("channel",   choices=["stable", "unstable"])
    s.add_argument("operation", choices=["boot", "switch"], nargs="?", default=None,
                   help="Omit to keep existing / use module default")
    s.add_argument("--preset", choices=backend.PRESETS, default=None)
    s.set_defaults(func=_cmd_set)

    # apply
    a = sub.add_parser("apply", help="Set channel and run nixos-rebuild now (requires root)")
    a.add_argument("channel",   choices=["stable", "unstable"])
    a.add_argument("operation", choices=["boot", "switch"])
    a.add_argument("--preset", choices=backend.PRESETS, default=None)
    a.set_defaults(func=_cmd_apply)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)
