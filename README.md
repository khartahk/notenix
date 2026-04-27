# notenix

Hands off computer system with user friendly interface. It features automatic updates
like a Chrombook but gives users more flexibility.

> The goal is similar to [nixbook](https://github.com/mkellyxp/nixbook) but with a more
modern desktop environment. It should require no Linux knowledge to maintain, and keeps
personal config completely separate from the system.

## Features

- Modern desktop **GNOME** (minimal - heavy default apps removed, Mac like dock).
- Default browser **Firefox** a more privacy focused option then Chrome or Edge.
- Integrated software store **GNOME Software**.
- Office suite **LibreOffice**.
- **Daily auto-update** *never reboots automatically*, updates available after user reboots. 

---

## Installation (single command from the live USB)

### 1 — Boot the NixOS minimal ISO

Download the [NixOS minimal ISO](https://nixos.org/download), flash it to a USB
stick, and boot the target machine from it.

### 2 — Connect to the internet

Ethernet connects automatically. For Wi-Fi:

```bash
nmtui
```

### 3 — Run the installer

```bash
nix run github:n1x05/notenix \
  --extra-experimental-features "nix-command flakes" \
  --no-write-lock-file
```

The script opens a `dialog`-based TUI and walks you through:

| Step | What you choose | Source of options |
|---|---|---|
| **Disk** | Which disk to install onto | `lsblk` — lists all real disks with size and model |
| **Timezone** | Your timezone | Full list from tzdata (`zone1970.tab`) |
| **Locale** | System language/format | UTF-8 locales from glibc (`SUPPORTED`) |
| **Keyboard** | XKB keyboard layout | From xkeyboard-config (`evdev.lst`) with human-readable names |
| **Hostname** | Machine name | Free text input, default `notenix` |
| **Username** | Primary user login | Free text input, default `user` |
| **Full name** | Display name for the user | Free text input, optional |

A final **Yes/No summary screen** shows all choices before anything is touched.
Then it partitions + installs + prompts for a password, all in one run.

### 4 — Reboot

```bash
sudo reboot
```

> Apps declared in `notenix.applications.flatpak.packages` are installed 
  automatically via Flatpak once the network comes up on the first boot.

---

## Customise for your own machine

1. Fork or clone this repo.
2. Edit `hosts/notenix/configuration.nix` — update the **machine identity** block:
   ```nix
   notenix.system.install.hostName        = "yourhostname";
   notenix.system.install.userName        = "youruser";
   notenix.system.install.userDescription = "Your Name";
   notenix.system.install.timeZone        = "Europe/Ljubljana";
   notenix.system.install.locale          = "sl_SI.UTF-8";
   notenix.system.install.keyboardLayout  = "si";
   ```
   Also adjust:
   - `notenix.system.autoupgrade.flakeRepo` → `github:<you>/<repo>`
   - `notenix.system.autoupgrade.hostName` → `<yourhostname>`
   - `notenix.applications.flatpak.packages` to add/replace apps
3. Update the `nixosConfigurations` key in `flake.nix` to match your hostname.
4. Push and install with the TUI installer, or via nixos-anywhere for remote targets:
   ```bash
   nix run github:nix-community/nixos-anywhere \
     --extra-experimental-features "nix-command flakes" \
     -- \
     --flake github:<you>/<repo>#<yourhostname> \
     root@<target-ip>
   ```

---

## Repository layout

```
flake.nix                        # inputs, nixosConfigurations, packages
hosts/notenix/
  configuration.nix              # machine identity + feature toggles
  disk.nix                       # disko GPT/ext4 layout
modules/                         # self-contained notenix NixOS modules
  default.nix                    # imports all categories
  system/
    install.nix                  # hostname, user, locale, keyboard
    nix.nix                      # flakes, GC, store optimisation
    autoupgrade.nix              # daily nixos-rebuild via systemd
  boot/
    systemd-boot.nix             # EFI boot loader
  desktop/
    gnome.nix                    # GNOME + GDM + extensions + dconf
  applications/
    flatpak.nix                  # Flathub remote + declarative app installs
  network/
    networkmanager.nix           # NetworkManager + Wi-Fi firmware
  hardware/
    bluetooth.nix                # Bluetooth + blueman
    printing.nix                 # CUPS + Avahi
    sound.nix                    # PipeWire
  security/
    sudo.nix                     # wheel sudo policy
```

---

## Module reference

All options live in `modules/` inside this repo under the `notenix.*` namespace.

| Option | Default | Description |
|---|---|---|
| `notenix.system.install.enable` | `false` | Machine identity (hostname, user, locale, keyboard) |
| `notenix.system.install.hostName` | `"nixos"` | Machine hostname |
| `notenix.system.install.userName` | `"user"` | Primary user account name |
| `notenix.system.install.timeZone` | `"Europe/Ljubljana"` | System timezone |
| `notenix.system.install.locale` | `"sl_SI.UTF-8"` | Default locale |
| `notenix.system.install.keyboardLayout` | `"us"` | XKB keyboard layout |
| `notenix.system.install.consoleKeyMap` | `"us"` | Console keymap (loadkeys) |
| `notenix.boot.systemd-boot.enable` | `false` | systemd-boot EFI bootloader |
| `notenix.boot.systemd-boot.kernelPackages` | `null` | Kernel package set (null = NixOS default) |
| `notenix.desktop.gnome.enable` | `false` | GNOME + GDM + extensions |
| `notenix.desktop.gnome.dockFixed` | `true` | Always-visible dock |
| `notenix.desktop.gnome.favoriteApps` | firefox, nautilus, console, calculator | Dock favourite app IDs |
| `notenix.desktop.gnome.extraPackages` | `[]` | Extra packages added to the desktop |
| `notenix.desktop.gnome.excludePackages` | see module | GNOME apps to remove |
| `notenix.applications.flatpak.enable` | `false` | Flatpak + Flathub + daily updates |
| `notenix.applications.flatpak.packages` | `[]` | App IDs to install from Flathub |
| `notenix.system.nix.enable` | `true` | Flakes, GC, store optimisation, allowUnfree |
| `notenix.system.nix.gcDays` | `"weekly"` | GC schedule (systemd.time format) |
| `notenix.system.autoupgrade.enable` | `false` | Daily flake rebuild via `nixos-upgrade.service` |
| `notenix.system.autoupgrade.flakeRepo` | `"github:n1x05/notenix"` | Flake URL for nixos-rebuild |
| `notenix.system.autoupgrade.hostName` | *(networking.hostName)* | Flake output name (`#<hostName>`) |
| `notenix.system.autoupgrade.dates` | `"weekly"` | systemd calendar string |
| `notenix.system.autoupgrade.operation` | `"boot"` | `"boot"` (next reboot) or `"switch"` (immediate) |
| `notenix.network.networkmanager.enable` | `false` | NetworkManager + Wi-Fi firmware |
| `notenix.security.sudo.wheelNeedsPassword` | `false` | Require password for `wheel` group sudo |
| `notenix.hardware.bluetooth.enable` | `false` | Bluetooth + blueman |
| `notenix.hardware.printing.enable` | `false` | CUPS + Avahi network printing |
| `notenix.hardware.sound.enable` | `false` | PipeWire with PulseAudio compat |

---

## Testing with QEMU VMs

```bash
# Headless smoke-test (serial console, user/notenix)
nix run .#vm

# Full GNOME desktop (opens a QEMU window)
nix run .#vm-gnome
```

---

## Checking update status

```bash
# See when the last auto-update ran and whether it succeeded
systemctl status nixos-upgrade.service

# Watch the update log live
journalctl -u nixos-upgrade.service -f

# Check when the next update is scheduled
systemctl list-timers nixos-upgrade.timer

# List all system generations
sudo nix-env --list-generations --profile /nix/var/nix/profiles/system

# Roll back to the previous generation
sudo nixos-rebuild switch --rollback
```