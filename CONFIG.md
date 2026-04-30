# Configuring notenix

📖 [README](README.md) · 💿 [Install](INSTALL.md) · 🖥️ [Kanal app](KANAL.md)

---

Many settings can be changed through the **Kanal** graphical settings app without touching any files — see [KANAL.md](KANAL.md).

For anything not covered by Kanal, edit `/etc/nixos/machine.nix` and run:

```bash
sudo nixos-rebuild switch --flake path:/etc/nixos#notenix
```

---

## Presets

Presets are named bundles of software and hardware support. Choose one that fits your use case.

| Preset | Desktop | App store (Flatpak) | Sound | Bluetooth | Printing |
|---|:---:|:---:|:---:|:---:|:---:|
| `desktop` *(default)* | GNOME | ✅ | ✅ | ✅ | ✅ |
| `desktop-lite` | Cinnamon | ✅ | ✅ | ✅ | ✅ |
| `minimal` | None | ❌ | ❌ | ❌ | ❌ |

**Set in Kanal**: Channel tab → Preset selector \
**Set manually** in `machine.nix`:
```nix
notenix.preset = lib.mkForce "desktop-lite";
```

---

## Machine identity

These are set once during installation and rarely need changing.

| Option | What it controls | Kanal |
|---|---|:---:|
| `notenix.system.install.hostName` | Computer name on the network | ✅ |
| `notenix.system.install.userName` | Login username | ✅ |
| `notenix.system.install.userDescription` | Display name shown on login screen | ✅ |
| `notenix.system.install.timeZone` | System timezone (e.g. `Europe/Ljubljana`) | ✅ |
| `notenix.system.install.locale` | Language and date/number format (e.g. `en_US.UTF-8`) | ✅ |
| `notenix.system.install.keyboardLayout` | Keyboard layout (XKB code, e.g. `si`, `us`, `de`) | ✅ |
| `system.stateVersion` | NixOS state version — set at install, do not change | ✅ |

---

## Optional features

Features are off by default. Enable only what you need.

| Feature | Option | What it does | Kanal |
|---|---|---|:---:|
| **SSH access** | `notenix.features.ssh` | Allows remote login over the network. Password login enabled, root login disabled. | ✅ |
| **Kiosk mode** | `notenix.features.kiosk` | Auto-login, no screen lock. Ideal for a shared screen or a single-purpose display. | ✅ |

**Set in Kanal**: Features tab \
**Set manually** in `machine.nix`:
```nix
notenix.features.ssh   = lib.mkForce true;
notenix.features.kiosk = lib.mkForce false;
```

---

## Automatic updates

| Option | Default | What it controls |
|---|---|---|
| `notenix.system.autoupgrade.enable` | `true` | Enable/disable daily auto-update |
| `notenix.system.autoupgrade.operation` | `"boot"` | `"boot"` = apply on next reboot; `"switch"` = apply immediately |
| `notenix.system.autoupgrade.dates` | `"weekly"` | How often to check (systemd calendar string) |
| `notenix.system.autoupgrade.flakeRepo` | `"github:n1x05/notenix"` | Source flake for updates |

**Activation mode** (boot vs switch) is available in Kanal — see [KANAL.md](KANAL.md).

---

## Flatpak apps

Apps installed from Flathub can be declared in the configuration so they are automatically present after every install:

```nix
notenix.applications.flatpak.packages = [
  "org.libreoffice.LibreOffice"
  "org.gimp.GIMP"
  "com.spotify.Client"
];
```

You can also install apps at any time through **GNOME Software** without editing any files.

---

## Checking update status

```bash
# See when the last update ran
systemctl status nixos-upgrade.service

# Watch update output live
journalctl -u nixos-upgrade.service -f

# List all system generations
sudo nix-env --list-generations --profile /nix/var/nix/profiles/system

# Roll back to the previous generation
sudo nixos-rebuild switch --rollback
```
