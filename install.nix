# Interactive TUI installer — called via `nix run .#install` (or just `nix run`).
# Takes the flake-level inputs so it can reference disko and nixpkgs packages.
{ nixpkgs, disko, system }:

let
  pkgs = nixpkgs.legacyPackages.${system};
in
pkgs.writeShellApplication {
  name = "notenix-install";

  runtimeInputs = [
    disko.packages.${system}.disko-install
    pkgs.util-linux        # lsblk
    pkgs.dialog            # TUI menus
    pkgs.tzdata            # zone1970.tab
    pkgs.xkeyboard_config  # evdev.lst
    pkgs.glibcLocales      # SUPPORTED locales
    pkgs.gawk
    pkgs.gnugrep
  ];

  text = ''
    set -euo pipefail

    FLAKE="github:n1x05/notenix"
    BACKTITLE="notenix installer"
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT

    # Helper: run dialog, return selected value or exit on Cancel
    pick() {
      local title="$1"; shift
      local result
      if ! result=$(dialog \
            --backtitle "$BACKTITLE" \
            --title "$title" \
            "$@" 3>&1 1>&2 2>&3); then
        clear; echo "Installation cancelled."; exit 1
      fi
      echo "$result"
    }

    # ── 1. Disk ───────────────────────────────────────────────────────
    DISK_ITEMS=""
    while IFS= read -r line; do
      NAME=$(echo "$line" | awk '{print $1}')
      SIZE=$(echo "$line" | awk '{print $2}')
      MODEL=$(echo "$line" | awk '{$1=$2=""; print $0}' | sed 's/^ *//')
      [ -z "$MODEL" ] && MODEL="—"
      DISK_ITEMS="$DISK_ITEMS /dev/$NAME \"$SIZE  $MODEL\" off"
    done < <(lsblk -d -o NAME,SIZE,MODEL --noheadings | grep -v "^loop")

    DISK=$(eval dialog \
      --backtitle '"'"$BACKTITLE"'"' \
      --title '"Select installation disk"' \
      --radiolist '"ALL DATA ON THE SELECTED DISK WILL BE ERASED.\n\nUse arrow keys + Space to select, Enter to confirm."' \
      20 70 10 \
      "$DISK_ITEMS" \
      3\>'\&'1 1\>'\&'2 2\>'\&'3) || { clear; echo "Cancelled."; exit 1; }

    # ── 2. Timezone ───────────────────────────────────────────────────
    TZ_ITEMS=""
    while IFS=$'\t' read -r _cc _coords tz _comment; do
      TZ_ITEMS="$TZ_ITEMS $tz \"\" off"
    done < <(grep -v '^#' "${pkgs.tzdata}/share/zoneinfo/zone1970.tab")

    TIMEZONE=$(eval dialog \
      --backtitle '"'"$BACKTITLE"'"' \
      --title '"Select timezone"' \
      --radiolist '"Use arrow keys + Space to select (type to filter in some terminals)"' \
      25 60 18 \
      "$TZ_ITEMS" \
      3\>'\&'1 1\>'\&'2 2\>'\&'3) || { clear; echo "Cancelled."; exit 1; }

    # ── 3. Locale ─────────────────────────────────────────────────────
    LOCALE_ITEMS=""
    while IFS= read -r entry; do
      loc=$(echo "$entry" | awk '{print $1}' | sed 's|/.*||')
      [[ "$loc" == *"UTF-8"* ]] || continue
      LOCALE_ITEMS="$LOCALE_ITEMS $loc \"\" off"
    done < <(grep -v '^#' "${pkgs.glibcLocales}/share/i18n/SUPPORTED" \
             | tr ' ' '\n' | grep -v '^$' | grep -v '\\')

    LOCALE=$(eval dialog \
      --backtitle '"'"$BACKTITLE"'"' \
      --title '"Select default locale"' \
      --radiolist '"UTF-8 locales only. This sets the language/format for the whole system."' \
      25 60 18 \
      "$LOCALE_ITEMS" \
      3\>'\&'1 1\>'\&'2 2\>'\&'3) || { clear; echo "Cancelled."; exit 1; }

    # ── 4. Keyboard layout ────────────────────────────────────────────
    KB_ITEMS=""
    in_layout=0
    while IFS= read -r line; do
      if echo "$line" | grep -q "^! layout"; then in_layout=1; continue; fi
      if echo "$line" | grep -q "^!"; then in_layout=0; fi
      if [ "$in_layout" -eq 1 ] && [ -n "$line" ]; then
        code=$(echo "$line" | awk '{print $1}')
        desc=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^ *//')
        KB_ITEMS="$KB_ITEMS $code \"$desc\" off"
      fi
    done < "${pkgs.xkeyboard_config}/share/X11/xkb/rules/evdev.lst"

    KBLAYOUT=$(eval dialog \
      --backtitle '"'"$BACKTITLE"'"' \
      --title '"Select keyboard layout"' \
      --radiolist '"Keyboard layout for console and graphical session."' \
      25 65 18 \
      "$KB_ITEMS" \
      3\>'\&'1 1\>'\&'2 2\>'\&'3) || { clear; echo "Cancelled."; exit 1; }

    # ── 5. Preset ─────────────────────────────────────────────────────
    PRESET=$(pick "Configuration preset" \
      --menu "Choose the default feature set for this machine:" 12 65 2 \
      "desktop" "Full GNOME desktop (Flatpak, sound, bluetooth, printing)" \
      "minimal" "Minimal headless system (no desktop, essentials only)")

    # ── 6. Hostname ───────────────────────────────────────────────────
    HOSTNAME=$(pick "Machine hostname" \
      --inputbox "Enter a hostname for this machine:" 8 50 "notenix")

    # ── 7. Username & full name ───────────────────────────────────────
    USERNAME=$(pick "Primary user" \
      --inputbox "Enter the primary username:" 8 50 "user")

    USERDESC=$(pick "Full name (optional)" \
      --inputbox "Enter the full name for '$USERNAME' (or leave blank):" 8 60 "")

    # ── 8. Summary & confirmation ─────────────────────────────────────
    clear
    MSG="Please review your choices:\n\n"
    MSG+="  Disk     : $DISK\n"
    MSG+="  Preset   : $PRESET\n"
    MSG+="  Hostname : $HOSTNAME\n"
    MSG+="  Username : $USERNAME\n"
    MSG+="  Full name: $USERDESC\n"
    MSG+="  Timezone : $TIMEZONE\n"
    MSG+="  Locale   : $LOCALE\n"
    MSG+="  Keyboard : $KBLAYOUT\n\n"
    MSG+="⚠️  ALL DATA ON $DISK WILL BE ERASED."

    dialog \
      --backtitle "$BACKTITLE" \
      --title "Confirm installation" \
      --yesno "$MSG" 20 65 || { clear; echo "Cancelled."; exit 1; }
    clear

    # ── 9. Write machine-specific flake and config ───────────────────
    mkdir -p "$TMP/etc/nixos"

    # flake.nix — points to upstream notenix; kanal only ever rewrites
    # the inputs.notenix.url line to switch branches.
    cat > "$TMP/etc/nixos/flake.nix" <<'FLAKE'
# /etc/nixos/flake.nix — machine entry point.
# inputs.notenix.url is rewritten by kanal to switch branches.
# Edit machine.nix for machine-specific settings.
{
  inputs.notenix.url = "github:n1x05/notenix";
  outputs = { notenix, ... }:
    notenix.lib.mkMachineSystem { modules = [ ./machine.nix ]; };
}
FLAKE

    # machine.nix — NixOS module with machine-specific settings.
    # Written once by the installer; kanal only rewrites notenix.preset.
    cat > "$TMP/etc/nixos/machine.nix" <<EOF
# /etc/nixos/machine.nix — machine-specific NixOS configuration.
# Written by the notenix installer. Safe to edit manually.
# kanal rewrites notenix.preset when you change profile in the app.
{ lib, ... }: {
  notenix.preset                         = lib.mkForce "$PRESET";
  notenix.system.autoupgrade.flakeRepo   = lib.mkForce "path:/etc/nixos";
  notenix.system.autoupgrade.hostName    = lib.mkForce "notenix";
  notenix.system.install.hostName        = lib.mkForce "$HOSTNAME";
  notenix.system.install.userName        = lib.mkForce "$USERNAME";
  notenix.system.install.userDescription = lib.mkForce "$USERDESC";
  notenix.system.install.timeZone        = lib.mkForce "$TIMEZONE";
  notenix.system.install.locale          = lib.mkForce "$LOCALE";
  notenix.system.install.keyboardLayout  = lib.mkForce "$KBLAYOUT";
  system.stateVersion                    = "25.11";
}
EOF

    # ── 10. Partition, format, install ────────────────────────────────
    echo ""
    echo "→ Partitioning $DISK and installing NixOS…"
    echo "  (this will take a while — fetching from GitHub)"
    echo ""

    disko-install \
      --flake "$FLAKE" \
      --disk main "$DISK" \
      --write-efi-boot-entries \
      --extra-files "$TMP"

    # ── 11. Set password ──────────────────────────────────────────────
    echo ""
    echo "✓ Installation complete."
    echo ""
    echo "Set a password for '$USERNAME':"
    nixos-enter --root /mnt -- passwd "$USERNAME"

    echo ""
    echo "All done. Run: sudo reboot"
  '';
}
