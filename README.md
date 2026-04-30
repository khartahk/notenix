# notenix

**A Linux computer that takes care of itself** — automatic updates, modern desktop, no command line required.

---

📖 [Install](INSTALL.md) · ⚙️ [Configure](CONFIG.md) · 🖥️ [Kanal app](KANAL.md)

---

## What is notenix?

notenix is a ready-to-use Linux system built on [NixOS](https://nixos.org). It works like a Chromebook — it keeps itself up to date silently in the background and never breaks — but gives you the full power of a real desktop PC.

You do not need to know Linux. You do not need to use a terminal. Just install and use.

## What you get

| | |
|---|---|
| 🔄 **Automatic updates** | Downloads and applies system updates daily. Updates take effect after your next reboot — the system never restarts on its own. |
| 🖥️ **Modern desktop** | GNOME desktop with a clean dock, similar to macOS. Lightweight alternative available (Cinnamon). |
| 🌐 **Firefox** | Privacy-focused browser pre-installed. |
| 📦 **App store** | GNOME Software for installing additional apps from Flathub. |
| 🖨️ **Printing** | Network and USB printers work out of the box. |
| 🔵 **Bluetooth** | Connect headphones, keyboards, mice without extra setup. |
| 🔊 **Sound** | Audio works immediately, including HDMI and USB audio. |
| 🔒 **Can't break** | Every update is atomic. If something goes wrong, one command rolls back to the previous working state. |

## Optional features

These can be turned on or off at any time:

| Feature | What it does |
|---|---|
| **SSH access** | Log in to the machine remotely over the network. |
| **Kiosk mode** | Auto-login to a single fullscreen app — ideal for shared screens or displays. |

→ See [CONFIG.md](CONFIG.md) for all options, including how to change preset, hostname, locale and keyboard.

→ Many of these can be changed graphically through the **Kanal** settings app — see [KANAL.md](KANAL.md).

## Installation

Boot from a USB stick and run one command. The installer asks you a few questions (disk, timezone, keyboard, username) and handles the rest.

→ Full step-by-step instructions: [INSTALL.md](INSTALL.md)

## Rolling back an update

If anything ever goes wrong after an update:

```bash
sudo nixos-rebuild switch --rollback
```

Or choose the previous entry from the boot menu at startup.