# Installing notenix

📖 [README](README.md) · ⚙️ [Configure](CONFIG.md) · 🖥️ [Kanal app](KANAL.md)

---

## What you need

- A USB stick (4 GB or larger)
- The target computer connected to the internet (ethernet recommended, Wi-Fi works too)
- About 20–30 minutes

---

## Step 1 — Download and flash the USB stick

1. Download the **NixOS minimal ISO** from [nixos.org/download](https://nixos.org/download) (choose the minimal installer, x86_64).
2. Flash it to your USB stick:
   - **Windows**: use [Rufus](https://rufus.ie) or [balenaEtcher](https://etcher.balena.io)
   - **macOS / Linux**: use [balenaEtcher](https://etcher.balena.io)

---

## Step 2 — Boot from the USB stick

1. Plug the USB stick into the target computer.
2. Restart and enter the boot menu (usually **F12**, **F9**, **Esc**, or **Del** at the logo screen — it varies by manufacturer).
3. Choose the USB stick from the boot menu.
4. Wait for the NixOS live environment to start. You will land at a terminal prompt.

---

## Step 3 — Connect to the internet

**Ethernet**: plugs in and works automatically.

**Wi-Fi**: run the following and use the arrow keys to find and connect to your network:

```bash
nmtui
```

Check that you're online:

```bash
ping -c 2 1.1.1.1
```

---

## Step 4 — Run the notenix installer

Copy and paste this single command:

```bash
nix run github:n1x05/notenix \
  --extra-experimental-features "nix-command flakes" \
  --no-write-lock-file
```

> If you see a warning about experimental features, that is normal — it only applies during installation.

The installer will ask you:

| Question | Notes |
|---|---|
| **Disk** | Choose the disk to install onto. All data on it will be erased. |
| **Timezone** | Scroll to find your region and city (e.g. `Europe/Ljubljana`). |
| **Locale** | System language and date/number format (e.g. `en_US.UTF-8`). |
| **Keyboard layout** | XKB layout code (e.g. `us`, `gb`, `si`, `de`). |
| **Hostname** | A name for this computer (letters, numbers, hyphens only). |
| **Username** | Your login name (lowercase, no spaces). |
| **Full name** | Your display name — shown on the login screen (optional). |

A **summary screen** shows all your choices before anything is touched. Confirm with **Yes** to proceed.

The installer will then:
1. Partition and format the selected disk
2. Install the system
3. Ask you to set a password for your account

The whole process takes 10–20 minutes depending on your internet speed.

---

## Step 5 — Reboot

```bash
sudo reboot
```

Remove the USB stick when the screen goes blank.

---

## First boot

Your desktop will appear after a short setup. On the first login, any apps declared in the configuration will begin installing automatically in the background via Flatpak — this may take a few minutes.

---

## Alternative: Manual installation

If the interactive installer fails (e.g., NVMe not detected, or you prefer full control), use this manual path.

### Step 1 — Create a disk config

```bash
cat > nvme-disk.nix << 'EOF'
{
  disko.devices = {
    disk.main = {
      device = "/dev/nvme0n1";  # your NVMe drive
      type = "disk";
      content = {
        type = "gpt";
        partitions = {
          ESP = {
            size = "512M";
            type = "EF00";
            content = {
              type = "filesystem";
              format = "vfat";
              mountpoint = "/boot";
              mountOptions = [ "umask=0077" ];
            };
          };
          root = {
            size = "100%";
            content = {
              type = "filesystem";
              format = "ext4";
              mountpoint = "/";
            };
          };
        };
      };
    };
  };
}
EOF
```

### Step 2 — Partition and format the disk

```bash
sudo nix run github:nix-community/disko/latest \
  --extra-experimental-features "nix-command flakes" \
  -- --mode disko --root-mountpoint /mnt nvme-disk.nix
```

### Step 3 — Create a machine config

```bash
cat > machine.nix << 'EOF'
# /etc/nixos/machine.nix — machine-specific NixOS configuration.
# kanal rewrites notenix.preset when you change profile in the app.
{ lib, ... }: {
  imports = [ ./hardware-configuration.nix ];
  notenix.preset                         = lib.mkForce "desktop";
  notenix.disk.device                    = lib.mkForce "/dev/nvme0n1";
  notenix.system.autoupgrade.flakeRepo   = lib.mkForce "path:/etc/nixos";
  notenix.system.autoupgrade.hostName    = lib.mkForce "notenix";
  notenix.system.install.hostName        = lib.mkForce "mymachine";
  notenix.system.install.userName        = lib.mkForce "primoz";
  notenix.system.install.userDescription = lib.mkForce "Primoz";
  notenix.system.install.timeZone        = lib.mkForce "Europe/Ljubljana";
  notenix.system.install.locale          = lib.mkForce "en_US.UTF-8";
  notenix.system.install.keyboardLayout  = lib.mkForce "si";
  system.stateVersion                    = "25.11";
}
EOF
```

### Step 4 — Generate hardware config and install

```bash
# Generate hardware-configuration.nix for the target system
sudo nixos-generate-config --root /mnt

# Install using your machine.nix as an additional module
# Option A: Pass it directly to nixos-install (works with newer nixos-install-tools)
sudo nixos-install --no-root-passwd \
  --flake .#notenix
```

> **Note:** `--extra-config` passes your `machine.nix` as an additional module on top of the notenix flake configuration. This is how your custom settings (hostname, user, disk device, etc.) get applied.

### Step 5 — Reboot

```bash
sudo reboot
```

---

## Troubleshooting

**The installer command fails immediately** — your network may not be up yet. Try `ping 1.1.1.1` and wait a moment.

**Wi-Fi is not listed in `nmtui`** — some Wi-Fi chips need proprietary firmware. Connect via ethernet for installation and enable Wi-Fi after.

**Boot menu key not working** — try holding the key immediately after pressing the power button, before the manufacturer logo appears.

**NVMe drive not detected** — the live ISO may not auto-load NVMe drivers. Try:
```bash
sudo modprobe nvme
sudo modprobe ahci
lsblk
```
If the drive still doesn't appear, check BIOS settings — Intel RST/RAID mode hides NVMe from Linux. Switch SATA mode from RAID to AHCI in BIOS.

**Disko fails with "experimental Nix feature" error** — add `--extra-experimental-features "nix-command flakes"` to the `nix run` command.

**Disko fails with "disk-config.nix" usage error** — ensure you're passing the config file path correctly: `-- --mode disko --root-mountpoint /mnt nvme-disk.nix` (note the `--` separator before disko options).
