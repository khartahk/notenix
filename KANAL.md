# Kanal — Settings App

📖 [README](README.md) · 💿 [Install](INSTALL.md) · ⚙️ [Configure](CONFIG.md)

---

**Kanal** is the notenix graphical settings app. It lets you change the most common system settings and apply them with a single click — no terminal needed.

Open it from the app grid or launcher by searching for **Kanal**.

---

## Channel tab

Controls which version of notenix your machine tracks and how updates are applied.

| Setting | What it does |
|---|---|
| **Channel** | The update track. `main` is the stable release; `unstable` gets newer software sooner but with less testing. |
| **Preset** | The software bundle for this machine. See the table below. |
| **Activation** | `After reboot` — updates take effect on next restart (safe default). `Immediately` — applies the update right now without rebooting. |
| **Save** | Saves the channel/preset/activation choice and runs a system update. |

### Presets

| Preset | Desktop | App store | Sound | Bluetooth | Printing |
|---|:---:|:---:|:---:|:---:|:---:|
| Desktop *(default)* | GNOME | ✅ | ✅ | ✅ | ✅ |
| Desktop Lite | Cinnamon | ✅ | ✅ | ✅ | ✅ |
| Minimal | None | ❌ | ❌ | ❌ | ❌ |

---

## Machine tab

Identity settings for this computer. These are normally set during installation and only need changing if you move the machine or rename the user.

| Field | What it sets |
|---|---|
| **Hostname** | The computer's name on the network. |
| **Username** | The login name of the primary user account. |
| **Full name** | The display name shown on the login screen. |
| **Timezone** | System clock timezone (e.g. `Europe/Ljubljana`). |
| **Locale** | Language and date/number format (e.g. `en_US.UTF-8`). |
| **Keyboard layout** | XKB keyboard layout (e.g. `si`, `us`, `de`). |
| **State version** | NixOS state version — set at install time. Do not change unless you know what you are doing. |

Press **Save** to write the settings and rebuild the system.

---

## Features tab

Optional features that can be enabled or disabled at any time.

| Toggle | What it does |
|---|---|
| **SSH** | Allows remote login to this machine over the network. Password authentication is enabled; root login is disabled. |
| **Kiosk mode** | Logs in automatically and disables the screen lock. Intended for shared screens or single-purpose displays. |

Press **Save** to apply changes and rebuild the system.

---

## Log panel

While a save or update is running, a log panel appears below the tabs showing live output. This is useful for diagnosing problems. The panel closes automatically when the operation finishes successfully.
