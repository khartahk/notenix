"""kanal.__main__ — entry point dispatcher.

Invocation behaviour
--------------------
kanal              → open the GTK settings window
kanalctl           → run the CLI (same as kanal --ctl)
kanal --ctl …      → run the CLI with the remaining arguments
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Entry point for the `kanal` binary."""
    # Allow `kanal --ctl <args>` as an alias for kanalctl
    if len(sys.argv) > 1 and sys.argv[1] == "--ctl":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        main_ctl()
        return

    from kanal.gui.window import ChannelApp
    sys.exit(ChannelApp().run_gui())


def main_ctl() -> None:
    """Entry point for the `kanalctl` binary."""
    from kanal.cli import main as cli_main
    sys.exit(cli_main())


if __name__ == "__main__":
    # python -m kanal  →  GUI
    # python -m kanal --ctl …  →  CLI
    invoked_as = Path(sys.argv[0]).name
    if invoked_as == "kanalctl":
        main_ctl()
    else:
        main()
