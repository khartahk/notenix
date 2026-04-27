# notenix — Portable NixOS GNOME Desktop Flake

A standalone, minimal, auto-updating NixOS configuration for laptops/desktops.
All NixOS modules live in this repo under the `notenix.*` option namespace.
No external module frameworks — nixpkgs and disko are the only flake inputs.

## Repo structure

```
flake.nix               — nixosConfigurations (notenix, vm-headless, vm-gnome) + install package
modules/                — all NixOS option modules, imported as nixosModules.default
  default.nix           — imports all category modules below
  system/
    install.nix         — notenix.system.install.* (hostname, user, locale, keyboard)
    nix.nix             — notenix.system.nix.* (flakes, GC, unfree, fast shutdown)
    autoupgrade.nix     — notenix.system.autoupgrade.* (daily flake rebuild + notify)
  boot/
    systemd-boot.nix    — notenix.boot.systemd-boot.* (EFI boot, kernel)
  desktop/
    gnome.nix           — notenix.desktop.gnome.* (GNOME, GDM, extensions, dconf)
  applications/
    flatpak.nix         — notenix.applications.flatpak.* (Flathub, package list)
  network/
    networkmanager.nix  — notenix.network.networkmanager.*
  hardware/
    bluetooth.nix       — notenix.hardware.bluetooth.*
    printing.nix        — notenix.hardware.printing.*
    sound.nix           — notenix.hardware.sound.*
  security/
    sudo.nix            — notenix.security.sudo.wheelNeedsPassword
hosts/notenix/
  configuration.nix     — reference host; all notenix.* options for the machine
  disk.nix              — disko disk layout
_files/                 — helper scripts (notify-users.sh)
```

## Flake inputs

| Input | Purpose |
|-------|---------|
| `nixpkgs` | nixos-25.11 |
| `disko` | disk partitioning for install |

## Option namespace

All module options live under `notenix.*`. Example:

```nix
notenix.system.install = {
  enable          = true;
  hostName        = "mymachine";
  userName        = "youruser";
  userDescription = "Your Name";
  timeZone        = "Europe/Ljubljana";
  locale          = "sl_SI.UTF-8";
  keyboardLayout  = "si";
};
notenix.boot.systemd-boot.enable        = true;
notenix.desktop.gnome.enable            = true;
notenix.applications.flatpak.enable     = true;
notenix.system.nix.enable               = true;
notenix.system.autoupgrade.enable       = true;
notenix.system.autoupgrade.flakeRepo    = "github:yourusername/yourrepo";
notenix.network.networkmanager.enable   = true;
notenix.hardware.bluetooth.enable       = true;
notenix.hardware.printing.enable        = true;
notenix.hardware.sound.enable           = true;
```

## nixosConfigurations

| Name | Purpose |
|------|---------|
| `notenix` | Reference configuration for the real laptop; used by `nixos-rebuild` |
| `vm-headless` | Minimal headless VM for smoke-testing (user: `user` / pass: `notenix`) |
| `vm-gnome` | Full GNOME desktop VM for visual/interactive testing |

Run VMs:
```bash
nix run .#vm          # headless
nix run .#vm-gnome    # GNOME desktop (needs QEMU display)
```

## Adding a new host

1. Copy `hosts/notenix/` to `hosts/<yourhostname>/`
2. Edit `hosts/<yourhostname>/configuration.nix` — update identity and module options
3. Register in `flake.nix` under `nixosConfigurations`:
   ```nix
   <yourhostname> = lib.nixosSystem {
     inherit system;
     modules = [
       self.nixosModules.default
       disko.nixosModules.disko
       ./hosts/<yourhostname>/configuration.nix
       ./hosts/<yourhostname>/disk.nix
     ];
   };
   ```

## Install on a real machine

Boot NixOS minimal ISO, then:

```bash
nix run github:khartahk/notenix \
  --extra-experimental-features "nix-command flakes" \
  --no-write-lock-file
```

## Deploying changes to the running laptop

```bash
nixos-rebuild boot --sudo --ask-sudo-password \
  --flake .#notenix \
  --target-host uporabnik@<ip>
```

Use `switch` instead of `boot` to activate immediately without reboot.

## Checking auto-update status

```bash
systemctl status nixos-upgrade.service
journalctl -u nixos-upgrade.service -f
systemctl list-timers nixos-upgrade.timer
sudo nix-env --list-generations --profile /nix/var/nix/profiles/system
sudo nixos-rebuild switch --rollback
```
