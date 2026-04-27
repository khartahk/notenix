"""kanal.gui.window — GTK4/libadwaita preferences window."""

from __future__ import annotations

import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from kanal import backend


class ChannelWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Software Channel")
        self.set_search_enabled(False)
        self.set_default_size(480, -1)
        self.set_can_navigate_back(False)

        status = backend.read_status()

        page = Adw.PreferencesPage()
        self.add(page)

        # ── Channel ────────────────────────────────────────────────────────
        channel_group = Adw.PreferencesGroup()
        channel_group.set_title("Update Channel")
        channel_group.set_description(
            "Choose which channel this machine tracks for automatic system updates."
        )
        page.add(channel_group)

        self._stable_radio = Gtk.CheckButton()
        stable_row = Adw.ActionRow()
        stable_row.set_title("Stable")
        stable_row.set_subtitle("Recommended · follows the current NixOS stable release")
        stable_row.add_suffix(self._stable_radio)
        stable_row.set_activatable_widget(self._stable_radio)
        channel_group.add(stable_row)

        self._unstable_radio = Gtk.CheckButton()
        self._unstable_radio.set_group(self._stable_radio)
        unstable_row = Adw.ActionRow()
        unstable_row.set_title("Unstable")
        unstable_row.set_subtitle("Testing · follows the next NixOS release (may be less stable)")
        unstable_row.add_suffix(self._unstable_radio)
        unstable_row.set_activatable_widget(self._unstable_radio)
        channel_group.add(unstable_row)

        if status.channel == "unstable":
            self._unstable_radio.set_active(True)
        else:
            self._stable_radio.set_active(True)

        # ── Activation ────────────────────────────────────────────────────
        op_group = Adw.PreferencesGroup()
        op_group.set_title("Activation")
        page.add(op_group)

        self._op_row = Adw.ComboRow()
        self._op_row.set_title("When to activate")
        self._op_row.set_subtitle("How the new channel is applied after the next upgrade")
        self._op_row.set_model(
            Gtk.StringList.new([
                "On next reboot after upgrade (safe)",
                "Immediately after upgrade (switch)",
            ])
        )
        self._op_row.set_selected(1 if status.operation == "switch" else 0)
        op_group.add(self._op_row)

        # ── Preset ──────────────────────────────────────────────────
        preset_group = Adw.PreferencesGroup()
        preset_group.set_title("Preset")
        preset_group.set_description("Feature set enabled by default on this machine.")
        page.add(preset_group)

        self._preset_row = Adw.ComboRow()
        self._preset_row.set_title("Configuration preset")
        self._preset_row.set_model(Gtk.StringList.new([
            "Desktop (GNOME, Flatpak, sound, bluetooth, printing)",
            "Minimal (no desktop, essentials only)",
        ]))
        self._preset_row.set_selected(1 if status.preset == "minimal" else 0)
        preset_group.add(self._preset_row)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_group = Adw.PreferencesGroup()
        page.add(btn_group)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(4)
        btn_box.set_margin_bottom(12)

        self._save_btn = Gtk.Button(label="Save")
        self._save_btn.add_css_class("pill")
        self._save_btn.connect("clicked", self._on_save_clicked)
        btn_box.append(self._save_btn)

        self._save_apply_btn = Gtk.Button(label="Save & Apply")
        self._save_apply_btn.add_css_class("suggested-action")
        self._save_apply_btn.add_css_class("pill")
        self._save_apply_btn.connect("clicked", self._on_save_apply_clicked)
        btn_box.append(self._save_apply_btn)

        btn_group.add(btn_box)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _selection(self) -> tuple[str, str, str]:
        channel = "unstable" if self._unstable_radio.get_active() else "stable"
        op      = "switch" if self._op_row.get_selected() == 1 else "boot"
        preset  = "minimal" if self._preset_row.get_selected() == 1 else "desktop"
        return channel, op, preset

    def _set_busy(self, busy: bool, save_label="Save", apply_label="Save & Apply"):
        self._save_btn.set_sensitive(not busy)
        self._save_apply_btn.set_sensitive(not busy)
        self._save_btn.set_label(save_label)
        self._save_apply_btn.set_label(apply_label)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_save_clicked(self, _btn):
        channel, op, preset = self._selection()
        self._set_busy(True, save_label="Saving…")
        threading.Thread(target=self._worker, args=(channel, op, preset, False), daemon=True).start()

    def _on_save_apply_clicked(self, _btn):
        channel, op, preset = self._selection()
        self._set_busy(True, apply_label="Applying…")
        threading.Thread(target=self._worker, args=(channel, op, preset, True), daemon=True).start()

    def _worker(self, channel: str, op: str, preset: str, apply: bool):
        if not apply:
            rc, err = backend.pkexec_set(channel, op, preset)
            if rc == 0:
                GLib.idle_add(self._done, "Changes saved", None)
            else:
                GLib.idle_add(self._done, "Failed to save", err or f"pkexec exited {rc}")
        else:
            rc, err = backend.pkexec_apply(channel, op, preset)
            if rc == 0:
                GLib.idle_add(self._done, "Changes saved and applied", None)
            else:
                GLib.idle_add(self._done, "Upgrade failed", err or f"kanalctl apply exited {rc}")

    def _done(self, message: str, error: str | None = None):
        self._set_busy(False)
        if error:
            print(f"[kanal] error: {error}", file=sys.stderr, flush=True)
            dialog = Adw.AlertDialog.new("Error", error)
            dialog.add_response("ok", "OK")
            dialog.present(self)
        else:
            self.add_toast(Adw.Toast.new(message))
        return GLib.SOURCE_REMOVE


class ChannelApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="si.n1x05.notenix.kanal")
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        ChannelWindow(application=self).present()

    def run_gui(self) -> int:
        return self.run(sys.argv)
