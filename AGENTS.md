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

## Adding a feature flag

Feature flags live in `modules/system/features.nix` and are exposed as `notenix.features.<name>` booleans. Kanal reads/writes them via machine.nix. Adding a new feature requires touching **7 files** in order:

### 1. `modules/system/features.nix`
Add the option and its config block:
```nix
myFeature = mkOption {
  type        = types.bool;
  default     = false;
  description = "One-line description.";
};
```
Then inside `config = mkMerge [`:
```nix
(mkIf cfg.myFeature {
  # NixOS config here
})
```

### 2. `pkgs/kanal/src/kanal/constants.py`
```python
KEY_FEATURE_MY_FEATURE = "notenix.features.myFeature"
# Add to ALL_FEATURES list:
ALL_FEATURES: list[str] = [..., KEY_FEATURE_MY_FEATURE]
```

### 3. `pkgs/kanal/src/kanal/backend.py`
Add to the `from kanal.constants import (...)` block:
```python
KEY_FEATURE_MY_FEATURE,
```

### 4. `pkgs/kanal/src/kanal/privileged.py`
Import the constant, then add to the flag map dict:
```python
KEY_FEATURE_MY_FEATURE: "--my-feature",
```

### 5. `pkgs/kanal/src/kanal/cli.py`
In `_cmd_set_features`:
```python
if args.my_feature is not None: features[backend.KEY_FEATURE_MY_FEATURE] = args.my_feature
```
In `build_parser()` under `set-features`:
```python
f.add_argument("--my-feature",    dest="my_feature", action="store_true",  default=None)
f.add_argument("--no-my-feature", dest="my_feature", action="store_false")
```

### 6. `pkgs/kanal/src/kanal/gui/window.py`
In the features page setup block (after the last `feat_group.add(...)`):
```python
self._my_feature_row = Adw.SwitchRow()
self._my_feature_row.set_title("My Feature")
self._my_feature_row.set_subtitle("Short description shown in GUI")
self._my_feature_row.set_active(features.get(backend.KEY_FEATURE_MY_FEATURE, False))
feat_group.add(self._my_feature_row)
```
In the `features = {...}` save dict:
```python
backend.KEY_FEATURE_MY_FEATURE: self._my_feature_row.get_active(),
```

### 7. Test the build
```bash
cd /path/to/notenix
nix build path:.#nixosConfigurations.notenix.config.system.build.toplevel
```
Build must succeed before committing.

---

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
