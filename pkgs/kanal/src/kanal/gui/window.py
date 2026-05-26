"""kanal.gui.window — GTK4/libadwaita preferences window."""

from __future__ import annotations

import importlib.resources
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from kanal import _
from kanal import backend
from kanal import releases as _releases


class ChannelWindow(Adw.Window):
    _RELOAD_COOLDOWN_SECS = 30

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("kanal")
        self.set_default_size(700, 500)

        meta    = backend.load_metadata()
        status  = backend.read_status()
        machine = backend.read_machine()

        ext_sources_state = backend.read_extension_sources()
        ext_hashes_state  = backend.read_extension_source_hashes()
        # Mutable dict updated by background prefetch and included in every payload
        self._ext_source_hashes: dict[str, str] = dict(ext_hashes_state)
        # {ext_id: (ComboRow, [source_ids], item_dict)}
        self._ext_source_rows: dict[str, tuple] = {}
        # Reference to the experimental feature SwitchRow (wired after tab rendering)
        self._experimental_row: Adw.SwitchRow | None = None

        # ── Header bar ────────────────────────────────────────────────────
        self._reload_btn = Gtk.Button()
        self._reload_btn.set_icon_name("update-symbolic")
        self._reload_btn.set_tooltip_text("Reload available channels")
        self._reload_btn.connect("clicked", self._on_reload_clicked)
        self._reload_cooldown = 0

        self._cooldown_label = Gtk.Label(label="")
        self._cooldown_label.add_css_class("dim-label")
        self._cooldown_label.set_visible(False)

        reload_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        reload_box.append(self._reload_btn)
        reload_box.append(self._cooldown_label)

        # ── View stack ────────────────────────────────────────────────────
        self._stack = Gtk.Stack()
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)

        header = Adw.HeaderBar()
        header.pack_start(reload_box)

        # ══ Channel page ══════════════════════════════════════════════════
        channel_page = Adw.PreferencesPage()

        self._channel_meta = meta["channels"]
        self._channel_ids = sorted(
            self._channel_meta.keys(),
            key=lambda k: (not self._channel_meta[k].get("default", False), k),
        )
        channel_labels = [self._channel_friendly(k, self._channel_meta[k].get("default", False)) for k in self._channel_ids]

        main_group = Adw.PreferencesGroup()
        channel_page.add(main_group)

        self._channel_row = Adw.ComboRow()
        self._channel_row.set_title(_("Update channel"))
        self._channel_row.set_model(Gtk.StringList.new(channel_labels))
        selected_ch = self._channel_ids.index(status.channel) if status.channel in self._channel_ids else 0
        self._channel_row.set_selected(selected_ch)
        main_group.add(self._channel_row)

        self._preset_row = Adw.ComboRow()
        self._preset_row.set_title(_("Configuration preset"))
        self._preset_row.set_subtitle(_("Feature set enabled by default on this machine"))
        main_group.add(self._preset_row)

        self._update_preset_model(self._channel_ids[selected_ch], current_preset=status.preset)
        self._current_preset = status.preset
        self._channel_row.connect("notify::selected", self._on_channel_changed)
        self._preset_row.connect("notify::selected", self._on_preset_changed)

        op_row = Adw.ActionRow()
        op_row.set_title(_("Automatic upgrade activation"))
        op_row.set_subtitle(_("Applies to manual Save and the automatic upgrade service"))
        self._op_row = op_row

        self._op_reboot_btn = Gtk.CheckButton(label=_("After reboot"))
        self._op_now_btn    = Gtk.CheckButton(label=_("Immediately"))
        self._op_now_btn.set_group(self._op_reboot_btn)

        if status.operation == "switch":
            self._op_now_btn.set_active(True)
        else:
            self._op_reboot_btn.set_active(True)

        radio_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        radio_box.set_valign(Gtk.Align.CENTER)
        radio_box.append(self._op_reboot_btn)
        radio_box.append(self._op_now_btn)
        op_row.add_suffix(radio_box)
        main_group.add(op_row)

        self._stack.add_titled(channel_page, "channel", _("Channel"))

        # ══ Machine page ═════════════════════════════════════════════════════════════
        machine_page = Adw.PreferencesPage()
        self._machine_widgets: dict = {}

        _mgroups: dict[str, Adw.PreferencesGroup] = {}
        for g in backend.MACHINE_GROUPS:
            grp = Adw.PreferencesGroup()
            grp.set_title(_(g["title"]))
            machine_page.add(grp)
            _mgroups[g["id"]] = grp

        _cur_locale        = ""
        self._kbd_user_set = False
        self._kbd_syncing  = False
        for mf in backend.MACHINE_FIELDS:
            grp = _mgroups[mf["group"]]
            wt  = mf["widget"]
            cur = machine.get(mf["nix_key"], "")

            if wt == "entry":
                row = Adw.EntryRow()
                row.set_title(_(mf["label"]))
                row.set_text(cur)
                grp.add(row)
                self._machine_widgets[mf["id"]] = row

            elif wt == "dropdown_locale":
                locale_pairs     = backend.list_locales()
                self._locale_ids = [p[0] for p in locale_pairs]
                _cur_locale      = cur
                row = Adw.ComboRow()
                row.set_title(_(mf["label"]))
                row.set_model(Gtk.StringList.new([p[1] for p in locale_pairs]))
                row.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
                row.set_enable_search(True)
                row.set_selected(self._locale_ids.index(cur) if cur in self._locale_ids else 0)
                row.connect("notify::selected", self._on_locale_changed)
                grp.add(row)
                self._locale_drop = row
                self._machine_widgets[mf["id"]] = row

            elif wt == "dropdown_kbd":
                kbd_pairs        = backend.list_kbd_layouts()
                self._kbd_codes  = [p[0] for p in kbd_pairs]
                row = Adw.ComboRow()
                row.set_title(_(mf["label"]))
                row.set_model(Gtk.StringList.new([p[1] for p in kbd_pairs]))
                row.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
                row.set_enable_search(True)
                row.set_selected(self._kbd_codes.index(cur) if cur in self._kbd_codes else 0)
                self._kbd_user_set = bool(cur and cur in self._kbd_codes)
                row.connect("notify::selected", self._on_kbd_manually_changed)
                grp.add(row)
                self._kbd_drop = row
                self._machine_widgets[mf["id"]] = row

            elif wt == "readonly":
                row = Adw.ActionRow()
                row.set_title(_(mf["label"]))
                if mf.get("subtitle"):
                    row.set_subtitle(_(mf["subtitle"]))
                lbl = Gtk.Label(label=cur)
                lbl.add_css_class("dim-label")
                lbl.set_valign(Gtk.Align.CENTER)
                row.add_suffix(lbl)
                grp.add(row)

        if not self._kbd_user_set:
            self._sync_kbd_from_locale(_cur_locale)

        self._stack.add_titled(machine_page, "machine", _("Machine"))

        # ══ Dynamic catalog tabs (features / extensions / apps) ═══════════
        # All tabs defined in default.yaml are rendered generically here.
        # _tab_rows: { tab_id: { item_key_or_id: SwitchRow } }
        self._tab_rows: dict[str, dict[str, Adw.SwitchRow]] = {}

        features_state   = backend.read_features()
        extensions_state = set(backend.read_extensions())
        apps_state       = set(backend.read_apps())
        is_experimental  = features_state.get("notenix.features.experimental", False)

        for tab in backend.get_tab_catalog():
            tab_id = tab["id"]
            page   = Adw.PreferencesPage()
            group  = Adw.PreferencesGroup()
            group.set_title(_(tab["title"]))
            group.set_description(_(tab["description"]))
            page.add(group)

            rows: dict[str, Adw.SwitchRow] = {}

            if tab["type"] == "bool_options":
                for item in tab["items"]:
                    row = Adw.SwitchRow()
                    row.set_title(item["title"])
                    row.set_subtitle(item["subtitle"])
                    row.set_active(features_state.get(item["key"], item["default"]))
                    group.add(row)
                    rows[item["key"]] = row
                    # Keep a reference to the experimental row for gating source pickers
                    if item["key"] == "notenix.features.experimental":
                        self._experimental_row = row

            elif tab["type"] == "list_option":
                if tab_id == "extensions":
                    active_ids = extensions_state if extensions_state else {
                        item["id"] for item in tab["items"] if item["default"]
                    }
                else:
                    active_ids = apps_state
                for item in tab["items"]:
                    row = Adw.SwitchRow()
                    row.set_title(_(item["title"]))
                    row.set_subtitle(_(item["subtitle"]))
                    row.set_active(item["id"] in active_ids)
                    group.add(row)
                    rows[item["id"]] = row

                    # Source picker — only for extension items that declare sources
                    if tab_id == "extensions" and "sources" in item:
                        src_ids    = [s["id"]    for s in item["sources"]]
                        src_labels = [_(s["label"]) for s in item["sources"]]
                        src_key    = item.get("nix_source_key")
                        default_src = next(
                            (s["id"] for s in item["sources"] if s.get("default")),
                            src_ids[0],
                        )
                        cur_src = ext_sources_state.get(src_key) if src_key else None
                        sel_idx = (src_ids.index(cur_src)
                                   if cur_src and cur_src in src_ids
                                   else src_ids.index(default_src))
                        combo = Adw.ComboRow()
                        combo.set_title(_("Package source"))
                        combo.set_model(Gtk.StringList.new(src_labels))
                        combo.set_selected(sel_idx)
                        # Visible only when experimental is ON
                        combo.set_visible(is_experimental)
                        group.add(combo)
                        self._ext_source_rows[item["id"]] = (combo, src_ids, item)

            self._tab_rows[tab_id] = rows
            self._stack.add_titled(page, tab_id, _(tab["title"]))

        # ── Apply (header right) + Save (action bar) ──────────────────────
        self._apply_btn = Gtk.Button(label=_("Update"))
        self._apply_btn.add_css_class("suggested-action")
        self._apply_btn.add_css_class("pill")
        self._apply_btn.set_tooltip_text(_("Save all changes and rebuild"))
        self._apply_btn.connect("clicked", self._on_apply_clicked)
        header.pack_end(self._apply_btn)

        self._save_btn = Gtk.Button(label=_("Save"))
        self._save_btn.add_css_class("pill")
        self._save_btn.set_tooltip_text(_("Write all changes to config files (no rebuild)"))
        self._save_btn.set_sensitive(False)
        self._save_btn.connect("clicked", self._on_save_all_clicked)

        action_bar = Gtk.ActionBar()
        action_bar.pack_end(self._save_btn)

        # ── Layout ────────────────────────────────────────────────────────
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self._stack)
        sidebar.set_size_request(160, -1)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)

        content_scroll = Gtk.ScrolledWindow()
        content_scroll.set_child(self._stack)
        content_scroll.set_hexpand(True)
        content_scroll.set_vexpand(True)
        content_scroll.set_propagate_natural_height(True)

        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.append(sidebar)
        content_box.append(sep)
        content_box.append(content_scroll)

        # ── Log view ──────────────────────────────────────────────────────
        self._log_buf  = Gtk.TextBuffer()
        log_view       = Gtk.TextView(buffer=self._log_buf)
        log_view.set_editable(False)
        log_view.set_monospace(True)
        log_view.add_css_class("view")
        log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        log_view.set_top_margin(6)
        log_view.set_bottom_margin(6)
        log_view.set_left_margin(8)
        log_view.set_right_margin(8)
        self._log_scroll = Gtk.ScrolledWindow()
        self._log_scroll.set_child(log_view)
        self._log_scroll.set_min_content_height(140)
        self._log_scroll.set_max_content_height(200)
        self._log_scroll.set_vexpand(False)

        self._log_revealer = Gtk.Revealer()
        self._log_revealer.set_child(self._log_scroll)
        self._log_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._log_revealer.set_reveal_child(False)

        self._show_more_btn = Gtk.Button(label=_("Show more"))
        self._show_more_btn.add_css_class("flat")
        self._show_more_btn.set_visible(False)
        self._show_more_btn.connect("clicked", self._on_show_more_clicked)
        show_more_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        show_more_box.set_halign(Gtk.Align.CENTER)
        show_more_box.append(self._show_more_btn)

        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        log_box.append(show_more_box)
        log_box.append(self._log_revealer)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(content_box)
        toolbar_view.add_bottom_bar(action_bar)
        toolbar_view.add_bottom_bar(log_box)

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(toolbar_view)

        # ── Release banner (hidden until an update is found) ───────────────
        self._release_banner = Adw.Banner()
        self._release_banner.set_revealed(False)
        self._release_banner.set_button_label(_("What's new"))
        self._release_banner.connect("button-clicked", self._on_release_banner_clicked)
        self._release_newer: list[dict] = []

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer_box.append(self._release_banner)
        outer_box.append(self._toast_overlay)
        self.set_content(outer_box)

        self._initial_payload = self._collect_all_payload()
        self._connect_change_signals()

        if backend.is_cache_stale():
            self._start_refresh()
        self._start_release_check()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _connect_change_signals(self) -> None:
        """Wire all interactive widgets to _update_buttons."""
        cb = lambda *_: self._update_buttons()  # noqa: E731
        self._channel_row.connect("notify::selected", cb)
        self._preset_row.connect("notify::selected", cb)
        self._op_now_btn.connect("notify::active", cb)
        for mf in backend.MACHINE_FIELDS:
            w = self._machine_widgets.get(mf["id"])
            if w is None:
                continue
            if mf["widget"] == "entry":
                w.connect("notify::text", cb)
            elif mf["widget"] in ("dropdown_locale", "dropdown_kbd"):
                w.connect("notify::selected", cb)
        for rows in self._tab_rows.values():
            for row in rows.values():
                row.connect("notify::active", cb)
        for _ext_id, (combo, _src_ids, _item) in self._ext_source_rows.items():
            combo.connect("notify::selected", cb)
            combo.connect("notify::selected", self._on_ext_source_combo_changed)
        # Wire experimental toggle → show/hide source pickers
        if self._experimental_row:
            self._experimental_row.connect("notify::active", self._on_experimental_toggled)

    def _update_buttons(self) -> None:
        """Save enabled only when dirty. Apply always enabled; label Apply/Update."""
        changed = self._collect_all_payload() != self._initial_payload
        self._save_btn.set_sensitive(changed)
        self._apply_btn.set_label(_("Apply") if changed else _("Update"))
        self._apply_btn.set_tooltip_text(
            _("Save all changes and rebuild") if changed else _("Rebuild with current saved config")
        )

    def _toast(self, message: str, timeout: int = 4) -> None:
        t = Adw.Toast.new(message)
        t.set_timeout(timeout)
        self._toast_overlay.add_toast(t)

    def _start_refresh(self) -> None:
        self._reload_btn.set_sensitive(False)
        self._reload_btn.set_tooltip_text(_("Checking for updates..."))
        spinner = Gtk.Spinner()
        spinner.start()
        self._reload_btn.set_child(spinner)
        threading.Thread(
            target=backend.refresh_metadata,
            kwargs={"callback": lambda data: GLib.idle_add(self._on_metadata_refreshed, data)},
            daemon=True,
        ).start()
        self._start_release_check()

    def _on_metadata_refreshed(self, new_meta: dict, *, error: bool = False) -> None:
        img = Gtk.Image.new_from_icon_name("update-symbolic")
        self._reload_btn.set_child(img)
        self._reload_cooldown = self._RELOAD_COOLDOWN_SECS
        self._update_cooldown_label()
        GLib.timeout_add_seconds(1, self._tick_cooldown)
        self._channel_meta = new_meta["channels"]

        cur_ch_idx = self._channel_row.get_selected()
        cur_ch     = self._channel_ids[cur_ch_idx] if cur_ch_idx < len(self._channel_ids) else None
        cur_preset = self._preset_ids[self._preset_row.get_selected()] if getattr(self, "_preset_ids", None) else None

        self._channel_ids = sorted(
            self._channel_meta.keys(),
            key=lambda k: (not self._channel_meta[k].get("default", False), k),
        )
        labels = [self._channel_friendly(k, self._channel_meta[k].get("default", False)) for k in self._channel_ids]
        self._channel_row.set_model(Gtk.StringList.new(labels))
        new_idx = self._channel_ids.index(cur_ch) if cur_ch in self._channel_ids else 0
        self._channel_row.set_selected(new_idx)
        self._update_preset_model(self._channel_ids[new_idx], current_preset=cur_preset)

        self._toast(_("Channel list updated"))
        return GLib.SOURCE_REMOVE

    @staticmethod
    def _channel_friendly(branch: str, is_default: bool = False) -> str:
        label = {"main": _("Stable"), "unstable": _("Testing")}.get(branch, branch.capitalize())
        return f"{label} ★" if is_default else label

    def _update_cooldown_label(self) -> None:
        self._cooldown_label.set_label(f"{self._reload_cooldown}s")
        self._cooldown_label.set_visible(True)

    def _tick_cooldown(self) -> bool:
        self._reload_cooldown -= 1
        if self._reload_cooldown <= 0:
            self._reload_btn.set_sensitive(True)
            self._reload_btn.set_tooltip_text(_("Reload available channels"))
            self._cooldown_label.set_visible(False)
            return GLib.SOURCE_REMOVE
        self._update_cooldown_label()
        return GLib.SOURCE_CONTINUE

    def _update_preset_model(self, channel_id: str, current_preset: str | None = None) -> None:
        presets = self._channel_meta.get(channel_id, {}).get("presets", [])
        self._preset_ids  = [p["id"] for p in presets]
        preset_labels     = [f"{_(p['label'])} ({_(p['subtitle'])})" for p in presets]
        self._preset_row.set_model(Gtk.StringList.new(preset_labels))
        if current_preset and current_preset in self._preset_ids:
            self._preset_row.set_selected(self._preset_ids.index(current_preset))
        else:
            self._preset_row.set_selected(0)

    def _on_channel_changed(self, row, _param) -> None:
        idx        = row.get_selected()
        channel_id = self._channel_ids[idx] if idx < len(self._channel_ids) else self._channel_ids[0]
        self._update_preset_model(channel_id)

    _DM_GROUP: dict[str, str] = {
        "desktop":      "gdm",
        "desktop-lite": "lightdm",
        "minimal":      "none",
    }

    def _on_preset_changed(self, row, _param) -> None:
        idx = row.get_selected()
        new_preset = self._preset_ids[idx] if idx < len(self._preset_ids) else None
        old_dm = self._DM_GROUP.get(self._current_preset or "", "")
        new_dm = self._DM_GROUP.get(new_preset or "", "")
        if old_dm and new_dm and old_dm != new_dm:
            self._op_reboot_btn.set_active(True)
            self._op_now_btn.set_sensitive(False)
            self._op_row.set_subtitle(
                _("Changing desktop environment requires a reboot — "
                  "'Immediately' is disabled")
            )
        else:
            self._op_now_btn.set_sensitive(True)
            self._op_row.set_subtitle(_("Applies to manual Save and the automatic upgrade service"))

    def _channel_selection(self) -> tuple[str, str, str, str]:
        ch_idx    = self._channel_row.get_selected()
        channel   = self._channel_ids[ch_idx] if ch_idx < len(self._channel_ids) else self._channel_ids[0]
        op        = "switch" if self._op_now_btn.get_active() else "boot"
        idx       = self._preset_row.get_selected()
        preset    = self._preset_ids[idx] if idx < len(self._preset_ids) else self._preset_ids[0]
        flake_url = self._channel_meta.get(channel, {}).get("flake", "")
        return channel, op, preset, flake_url

    def _machine_settings(self) -> dict[str, str]:
        result = {}
        for mf in backend.MACHINE_FIELDS:
            widget = self._machine_widgets.get(mf["id"])
            if widget is None:
                continue
            wt = mf["widget"]
            if wt == "entry":
                result[mf["nix_key"]] = widget.get_text()
            elif wt == "dropdown_locale":
                idx = widget.get_selected()
                result[mf["nix_key"]] = self._locale_ids[idx] if idx < len(self._locale_ids) else ""
            elif wt == "dropdown_kbd":
                idx = widget.get_selected()
                result[mf["nix_key"]] = self._kbd_codes[idx] if idx < len(self._kbd_codes) else ""
        return result

    def _on_locale_changed(self, drop, _param) -> None:
        if self._kbd_user_set:
            return
        idx = drop.get_selected()
        locale_code = self._locale_ids[idx] if idx < len(self._locale_ids) else ""
        self._sync_kbd_from_locale(locale_code)

    def _on_kbd_manually_changed(self, _drop, _param) -> None:
        if not self._kbd_syncing:
            self._kbd_user_set = True

    def _sync_kbd_from_locale(self, locale_str: str) -> None:
        suggestion = backend.kbd_default_for_locale(locale_str)
        if suggestion and suggestion in self._kbd_codes:
            self._kbd_syncing = True
            self._kbd_drop.set_selected(self._kbd_codes.index(suggestion))
            self._kbd_syncing = False

    def _on_show_more_clicked(self, _btn) -> None:
        revealed = self._log_revealer.get_reveal_child()
        self._log_revealer.set_reveal_child(not revealed)
        self._show_more_btn.set_label(_("Show less") if not revealed else _("Show more"))

    def _append_log(self, text: str) -> None:
        end = self._log_buf.get_end_iter()
        self._log_buf.insert(end, text)
        adj = self._log_scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _set_busy(self, busy: bool, btn: Gtk.Button | None = None, label: str = "") -> None:
        if btn:
            btn.set_sensitive(not busy)
            if label:
                btn.set_label(label)

    def _reset_log(self) -> None:
        """Clear log panel and reset Show-more button state (call from main thread)."""
        GLib.idle_add(self._log_buf.set_text, "")
        GLib.idle_add(self._show_more_btn.set_visible, True)
        GLib.idle_add(self._log_revealer.set_reveal_child, False)
        GLib.idle_add(self._show_more_btn.set_label, _("Show more"))

    def _run_stream_worker(
        self,
        stream_fn,
        success_msg: str,
        dry_msg: str,
        cmd_name: str,
        done_cb,
    ) -> None:
        """Consume a pkexec stream generator; call done_cb(message, error) when done.

        Must be called from a worker thread.
        """
        self._reset_log()
        try:
            rc = 0
            for item in stream_fn():
                if item is None:
                    break
                if isinstance(item, tuple):
                    _, rc = item
                    break
                GLib.idle_add(self._append_log, item)
            msg = dry_msg if backend.DRY_RUN else success_msg
            if rc == 0:
                GLib.idle_add(done_cb, msg, None)
            else:
                GLib.idle_add(done_cb, _("Save failed"), f"{cmd_name} exited {rc}")
        except Exception as exc:  # noqa: BLE001
            import traceback
            GLib.idle_add(done_cb, _("Save failed"), str(exc))
            print(traceback.format_exc(), file=sys.stderr, flush=True)

    def _collect_all_payload(self) -> dict:
        """Gather current UI state from all tabs + machine form + extension sources."""
        channel, op, preset, flake_url = self._channel_selection()
        payload: dict = {}
        for tab in backend.TAB_CATALOG:
            rows = self._tab_rows.get(tab["id"], {})
            if tab["type"] == "bool_options":
                payload[tab["id"]] = {key: row.get_active() for key, row in rows.items()}
            else:
                payload[tab["id"]] = [k for k, row in rows.items() if row.get_active()]
        ext_sources: dict[str, str] = {}
        for ext_id, (combo, src_ids, item) in self._ext_source_rows.items():
            src_key = item.get("nix_source_key")
            if src_key:
                idx = combo.get_selected()
                ext_sources[src_key] = src_ids[idx] if idx < len(src_ids) else src_ids[0]
        return {**payload, "machine": self._machine_settings(),
                "ext_sources": ext_sources,
                "ext_hashes":  dict(self._ext_source_hashes),
                "channel": channel, "operation": op, "preset": preset, "flake_url": flake_url}

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_experimental_toggled(self, row: Adw.SwitchRow, _param) -> None:
        """Show/hide source pickers and reset to default when experimental is disabled."""
        is_exp = row.get_active()
        for ext_id, (combo, src_ids, item) in self._ext_source_rows.items():
            if is_exp:
                combo.set_visible(True)
            else:
                # Reset to the YAML default source and hide the picker
                default_src = next(
                    (s["id"] for s in item["sources"] if s.get("default")),
                    src_ids[0],
                )
                combo.set_selected(src_ids.index(default_src) if default_src in src_ids else 0)
                combo.set_visible(False)

    def _on_ext_source_combo_changed(self, combo: Adw.ComboRow, _param) -> None:
        """When a source ComboRow changes, kick off hash prefetch if needed."""
        for ext_id, (c, src_ids, item) in self._ext_source_rows.items():
            if c is not combo:
                continue
            idx    = combo.get_selected()
            src_id = src_ids[idx] if idx < len(src_ids) else src_ids[0]
            src_def = next((s for s in item["sources"] if s["id"] == src_id), None)
            hash_key = item.get("nix_hash_key")
            if src_def and "fetch_url" in src_def and hash_key:
                # Prefetch only if hash not already cached for this URL
                cached = self._ext_source_hashes.get(hash_key, "")
                if not cached:
                    self._start_prefetch(ext_id, src_def["fetch_url"], hash_key)
            break

    def _start_prefetch(self, ext_id: str, fetch_url: str, hash_key: str) -> None:
        self._toast(_("Fetching package hash\u2026"), timeout=15)
        threading.Thread(
            target=self._prefetch_worker,
            args=(ext_id, fetch_url, hash_key),
            daemon=True,
        ).start()

    def _prefetch_worker(self, ext_id: str, fetch_url: str, hash_key: str) -> None:
        hash_val = ""
        rc       = 0
        for item in backend.prefetch_hash_stream(fetch_url):
            if isinstance(item, tuple):
                _, rc = item
                break
            if item:
                line = item.strip()
                # Hash is the last non-empty, non-"path is" line
                if line and not line.startswith("path"):
                    hash_val = line
        GLib.idle_add(self._on_prefetch_done, ext_id, hash_key,
                      hash_val if rc == 0 else "", rc)

    def _on_prefetch_done(self, ext_id: str, hash_key: str, hash_val: str, rc: int):
        if rc == 0 and hash_val:
            self._ext_source_hashes[hash_key] = hash_val
            self._update_buttons()
            self._toast(_("Package hash fetched \u2014 save to apply"))
        else:
            self._toast(_("Failed to fetch package hash \u2014 reverting to default"))
            # Revert combo to default source
            if ext_id in self._ext_source_rows:
                combo, src_ids, item = self._ext_source_rows[ext_id]
                default_src = next(
                    (s["id"] for s in item["sources"] if s.get("default")),
                    src_ids[0],
                )
                combo.set_selected(src_ids.index(default_src) if default_src in src_ids else 0)
        return GLib.SOURCE_REMOVE

    def _on_reload_clicked(self, _btn):
        self._start_refresh()

    def _dispatch_save(self, btn, label: str, rebuild: bool) -> None:
        payload    = self._collect_all_payload()
        busy_label = _("Applying\u2026") if rebuild else _("Saving\u2026")
        success    = _("All changes saved and applied") if rebuild else _("All changes saved")
        dry_msg    = (
            f"[Dry run] Would save all & apply: {payload['channel']}, {payload['operation']}, {payload['preset']}"
            if rebuild else "[Dry run] Would save all settings"
        )
        self._set_busy(True, btn, busy_label)
        self._save_btn.set_sensitive(False)
        done_cb = lambda msg, err: self._done_action(msg, err, btn, label)  # noqa: E731
        threading.Thread(
            target=self._run_stream_worker,
            args=(lambda: backend.pkexec_save_all_stream(payload, rebuild=rebuild),
                  success, dry_msg, "kanalctl save-all", done_cb),
            daemon=True,
        ).start()

    def _on_apply_clicked(self, _btn):
        self._dispatch_save(self._apply_btn, self._apply_btn.get_label(), rebuild=True)

    def _on_save_all_clicked(self, _btn):
        self._dispatch_save(self._save_btn, _("Save"), rebuild=False)

    # ── Release notification ──────────────────────────────────────────────

    def _start_release_check(self) -> None:
        """Fetch newer releases in the background; update banner when done."""
        threading.Thread(
            target=lambda: GLib.idle_add(
                self._on_release_checked, _releases.check_update()
            ),
            daemon=True,
        ).start()

    def _on_release_checked(self, newer: list[dict] | None) -> None:
        if not newer:
            self._release_banner.set_revealed(False)
            return GLib.SOURCE_REMOVE
        self._release_newer = newer
        latest = newer[0]["tag_name"]
        self._release_banner.set_title(_(f"Update available: {latest}"))
        self._release_banner.set_revealed(True)
        return GLib.SOURCE_REMOVE

    def _on_release_banner_clicked(self, _banner) -> None:
        """Show What's New dialog with all pending release notes."""
        dialog = Adw.Dialog()
        dialog.set_title(_("What's New"))
        dialog.set_content_width(560)
        dialog.set_content_height(480)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        notes_box.set_margin_top(12)
        notes_box.set_margin_bottom(12)
        notes_box.set_margin_start(18)
        notes_box.set_margin_end(18)

        for rel in self._release_newer:
            heading = Gtk.Label(label=rel["tag_name"])
            heading.add_css_class("title-2")
            heading.set_halign(Gtk.Align.START)
            notes_box.append(heading)

            body = Gtk.Label(label=rel["body"] or _("No release notes."))
            body.set_wrap(True)
            body.set_halign(Gtk.Align.START)
            body.set_selectable(True)
            notes_box.append(body)

        scroll.set_child(notes_box)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        toolbar.set_content(scroll)
        dialog.set_child(toolbar)
        dialog.present(self)

    # ── Result callbacks ──────────────────────────────────────────────────

    def _done_action(self, message: str, error: str | None, btn: Gtk.Button, label: str = "Save"):
        if not error:
            self._initial_payload = self._collect_all_payload()
        # Apply: sensitivity+label managed by _update_buttons; Save: restore label manually
        if btn is self._save_btn:
            self._set_busy(False, btn, label)
        else:
            btn.set_sensitive(True)
        self._update_buttons()
        self._show_result(message, error)

    def _show_result(self, message: str, error: str | None = None):
        if error:
            print(f"[kanal] error: {error}", file=sys.stderr, flush=True)
            dialog = Adw.AlertDialog.new(_("Error"), error)
            dialog.add_response("ok", _("OK"))
            dialog.present(self)
        else:
            self._toast(message)
        return GLib.SOURCE_REMOVE


class ChannelApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="si.n1x05.notenix.kanal")
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        icons_dir = str(importlib.resources.files("kanal").joinpath("icons"))
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(icons_dir)
        ChannelWindow(application=self).present()

    def run_gui(self) -> int:
        return self.run(sys.argv)
