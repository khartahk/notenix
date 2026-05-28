## Unreleased


- chore(dev): chore bumps PATCH version
- chore(dev): update CHANGELOG, make release refactor

## v0.6.1 (2026-05-28)


- bump: version → v0.6.1
- fix: pressing reload now always checks for new versions

## v0.6.0 (2026-05-28)


- bump: version → v0.6.0
- feat: show kanal rev when not using release version

## v0.5.0 (2026-05-28)


- bump: version → v0.5.0
- feat: show new updates when using releases
- feat(nix): add n1x05.cachix.org substituter and public key

## v0.4.2 (2026-05-27)


- bump: version → v0.4.2
- fix(dev): use plain version_files for flake.nix; no search pattern needed

## v0.4.1 (2026-05-27)


- bump: version → v0.4.1
- fix(dev): sync flake.nix version to 0.4.0
- fix(kanal): reload button also refreshes release list; dropdown updated after check_update
- docs: regenerate CHANGELOG with correct v0.3.0 and v0.4.0 sections

## v0.4.0 (2026-05-27)


- bump: version 0.3.0 → 0.4.0
- feat(kanal): release+branch dropdowns with mutual deselection and i18n
- - Add release ComboRow showing all GitHub releases (newest first)
  with currently pinned tag marked ★ (current); placeholder at index 0
- Add branch ComboRow (experimental only) filtered to main/unstable/feat/*
  branches; no forced capitalization
- Mutual deselection: selecting a release clears branch to placeholder
  and vice versa
- Add _branch_label() static method returning branch name as-is
- Add get_all_releases() to releases.py returning non-draft non-prerelease
  releases from cache, sorted newest first
- Add Slovenian translations: '— select release —' and '— select branch —'
- fix(dev): fix version_files pattern for flake.nix semicolon; sync flake.nix to 0.3.0

## v0.3.0 (2026-05-27)


- bump: version → v0.3.0
- feat(releases): stable release track, apply-release, hide channel row unless experimental
- feat(gnome): add minimize/maximize window buttons via dconf
- fix(kanal): sync flake.nix version to 0.2.2, add version_files to cz config
- fix(releases): filter draft releases; add KANAL_VERSION dev override; import os
- fix(dev): push lightweight tag explicitly; --follow-tags skips them

## v0.2.2 (2026-05-27)


- bump: version → v0.2.2
- fix(dev): rewrite release targets using define+shell for correct post-bump tag
- fix(dev): use --files-only bump + manual tag to keep tag on correct commit

## v0.2.1 (2026-05-27)


- bump: version 0.2.0 → 0.2.1
- fix(dev): run cz changelog separately after bump to ensure CHANGELOG.md is written

## v0.2.0 (2026-05-27)


- bump: version 0.1.0 → 0.2.0
- fix(dev): run cz from pkgs/kanal so pep621 provider finds pyproject.toml
- fix(dev): pass --repo to gh release create since origin is Gitea
- feat(dev): add changelog target, auto-update via pre-commit, fix changelog path
- feat(dev): add gh CLI to devShell, GitHub release creation in Makefile
- fix(dev): remove --quiet flag unsupported by this pre-commit version
- chore(dev): auto-install pre-commit hooks via direnv shellHook
- feat(releases): add update notification with GitHub release notes, commitizen versioning, and Makefile release targets
- feat(features): add steam feature flag with gamescope and remote play
- fix(gnome): remove postPatch shell-version hack; add build-time compat warning
- Instead of patching metadata.json to lie about supported GNOME versions,
read the extension's actual shell-version list at eval time and emit a
lib.warn if the running GNOME major version is not declared supported.
- This surfaces incompatibilities clearly during nixos-rebuild without
silently shipping a broken extension.
- fix(gnome): patch upstream-main ding metadata.json to include GNOME 49 shell-version
- fix(features): add missing notenix.features.experimental option
- feat(kanal): add experimental package sources for extensions
- - Add 'experimental' feature flag to default.yaml; gates source pickers in UI
- Add sources metadata to gtk4-desktop-icons-ng-ding: stable/unstable/upstream-main
- Add dingSource + dingSourceHash options to notenix.desktop.gnome (gnome.nix)
  - upstream-main uses builtins.fetchTarball + overrideAttrs
- Add EXT_SOURCE_ITEMS to constants.py (auto-derived from YAML)
- Add read/save_extension_sources/hashes to machine.py
- Add prefetch_hash_stream to privileged.py (nix-prefetch-url --unpack, no root)
- Extend pkexec_save_all_stream + cli save-all with --ext-sources/hashes-json
- GUI: ComboRow source pickers shown only when experimental enabled,
  upstream-main selection triggers background hash prefetch
- Update AGENTS.md: replace stale 7-file manual process with yaml-only workflow,
  document sources field pattern, document gtk4-ding GNOME 49 crash
- fix(kanal/i18n): use ASCII ... instead of U+2026 ellipsis to fix translation lookup
- fix(autoupgrade): add --upgrade to default flags so service updates flake inputs
- fix(kanal): remove locale.setlocale causing crash in restricted environments
- feat(kanal): add Slovenian i18n via gettext
- - Wire bindtextdomain/textdomain in __init__.py, expose _()
- Wrap all UI strings in window.py with _()
- Add po/extract_yaml.py to extract translatable YAML strings
- Generate po/kanal.pot template
- Add po/sl.po with full Slovenian translation (~60 strings)
- Compile .mo and install to share/locale in flake.nix
- Set TEXTDOMAINDIR + LOCALE_ARCHIVE in wrapProgram
- fix(kanal): disable Save when Apply is clicked
- feat(kanal): Apply button always visible; label Update/Apply by dirty state
- - No changes: button shows 'Update' (rebuild with current saved config)
- Changes pending: button shows 'Apply' (save + rebuild)
- Save button still only enabled when dirty
- _done_action restores correct post-action state via _update_buttons
- feat(kanal): disable Save/Apply buttons until something changes
- - Both buttons start insensitive at window open
- _connect_change_signals() wires all interactive widgets
  (channel, preset, op radio, machine entry/dropdowns, all switch rows)
  to _update_buttons()
- _update_buttons() enables both buttons iff current payload != initial
- _done_action() resets _initial_payload on success → buttons re-disabled
  on failed save buttons stay enabled so user can retry
- refactor(kanal): unify constants imports + drop dead code
- constants.py:
- remove _MACHINE_FIELDS alias; use MACHINE_FIELDS directly in loop
- fix MACHINE_KEY_FLAGS comprehension to use MACHINE_FIELDS
- privileged.py, nixfiles.py, machine.py, metadata.py:
- switch from explicit 'from kanal.constants import ...' to
  'import kanal.constants as _const'; no import list to maintain
  when adding new constants
- privileged.py:
- remove unused channel param from run_upgrade signature
- simplify return type tuple[int, str] → int (second element was always '')
- cli.py:
- update run_upgrade call sites to match new int return type
- refactor(kanal): make all remaining code fully data-driven from default.yaml
- default.yaml:
- machine.groups: new list [{id, title}] for Machine page group generation
- machine.fields: add label, group, widget (entry/dropdown_locale/dropdown_kbd/readonly),
  optional subtitle per field
- constants.py:
- export MACHINE_GROUPS from machine.groups
- backend.py:
- import + re-export MACHINE_GROUPS
- machine.py:
- remove unused KEY_KBLAYOUT, MACHINE_KEY_FLAGS imports
- window.py:
- Machine page: replace ~70 hardcoded lines with loop over MACHINE_GROUPS +
  MACHINE_FIELDS; widget dispatch on field widget type
- _machine_settings(): loop over MACHINE_FIELDS instead of 6 hardcoded KEY_* refs
- _collect_all_payload(): loop over TAB_CATALOG instead of hardcoded
  features/extensions/apps string keys
- privileged.py:
- import TAB_CATALOG
- pkexec_save_all_stream: loop over TAB_CATALOG to build --{id}-json / --{id}
  args; removes hardcoded --features-json/--apps/--extensions
- cli.py:
- build_parser save-all: loop over TAB_CATALOG instead of 3 hardcoded args
- _cmd_save_all: loop over TAB_CATALOG for tab_args instead of hardcoded dict
- Adding a new tab to default.yaml now propagates automatically to GUI, CLI,
privileged subprocess, and save-all — zero Python changes needed.
- refactor(kanal): deduplicate machine.py, backend.py, window.py, cli.py
- machine.py:
- extract _load_machine(): read file or return default skeleton
- extract _write_machine(contents, label): dry-run guard + write, one place
- extract _read_list_key(key): replaces duplicate bodies of read_apps/read_extensions
- extract _save_list_key(key, ids, label): replaces duplicate bodies of save_apps/save_extensions
- save_machine, save_features, save_apps, save_extensions all use helpers
- read_machine: derive key list from MACHINE_FIELDS (YAML) instead of hardcoded tuple
- backend.py:
- drop 8 hardcoded KEY_FEATURE_* imports; generate via loop over FEATURE_CATALOG
- __all__: replace 8 literal strings with *[f'KEY_FEATURE_{f[const]}' ...]
- window.py:
- extract _dispatch_save(btn, label, rebuild): shared body of Apply + Save handlers
- _on_apply_clicked / _on_save_all_clicked each reduced to 1 line
- cli.py:
- _cmd_save_all: use _TAB_SAVE_FN dispatch loop instead of 3 manual save calls
- refactor(kanal): generate set-* subcommands from TAB_CATALOG loop
- Remove _cmd_set_features, _cmd_set_apps, _cmd_set_extensions.
Add:
- _TAB_SAVE_FN: dispatch dict {save_cmd -> backend.save_fn} built from TAB_CATALOG
- _collect_tab_data(tab, args): bool_options -> dict, list_option -> list
- _make_tab_handler(tab): closure returning generic handler via _save_and_rebuild
- build_parser: replace 3 hardcoded parser blocks with single loop over TAB_CATALOG.
Adding a new tab to default.yaml now auto-generates its CLI subcommand.
- refactor(kanal): deduplicate cli.py handlers with shared helpers
- Extract:
- _collect_machine(args): MACHINE_FIELDS loop → {nix_key: val}, used in
  _cmd_set_machine and _cmd_save_all
- _do_rebuild(): identical 4-line nixos-rebuild block extracted from 4 cmds
- _save_and_rebuild(save_fn, data, msg, args): collapses save + print +
  optional rebuild into one call
- _cmd_set_machine, _cmd_set_features, _cmd_set_apps, _cmd_set_extensions
each reduced to 1-2 lines; rebuild block no longer duplicated
- refactor(kanal): derive CLI feature flags and machine args from default.yaml
- constants.py:
- expose MACHINE_FIELDS as public alias for _MACHINE_FIELDS
- backend.py:
- import and re-export MACHINE_FIELDS
- cli.py:
- _cmd_set_features: loop over FEATURE_CATALOG instead of 8 hardcoded KEY_FEATURE_* checks
- _cmd_set_machine: loop over MACHINE_FIELDS instead of 7 hardcoded KEY_* checks
- _cmd_save_all: same loop for machine settings; also fixes missing --stateversion
- build_parser set-features: generate --{id}/--no-{id} flag pairs from FEATURE_CATALOG
- build_parser set-machine: generate --{flag} args from MACHINE_FIELDS
- build_parser save-all: same for machine args
- refactor(kanal): move machine field keys + flags into default.yaml
- default.yaml:
- add machine.fields list: each entry has id, nix_key, cli_flag
- replaces 7 hardcoded KEY_* Python strings and _MACHINE_FLAGS dict
- constants.py:
- load _MACHINE_FIELDS from _CATALOG['machine']['fields']
- generate KEY_HOSTNAME, KEY_USERNAME … dynamically (globals() loop)
- expose MACHINE_KEY_FLAGS = {nix_key: cli_flag} for privileged.py/cli.py
- remove GNOME_EXTENSIONS_CATALOG, FLATPAK_CATALOG (unused outside module)
- remove hardcoded KEY_HOSTNAME … KEY_STATEVERSION string literals
- privileged.py:
- import MACHINE_KEY_FLAGS instead of 7 KEY_* constants
- replace _MACHINE_FLAGS dict literal with alias: _MACHINE_FLAGS = MACHINE_KEY_FLAGS
- backend.py:
- import MACHINE_KEY_FLAGS, drop FLATPAK_CATALOG, GNOME_EXTENSIONS_CATALOG
- __all__: add MACHINE_KEY_FLAGS, remove FLATPAK/GNOME_EXTENSIONS catalogs
- machine.py:
- add MACHINE_KEY_FLAGS to imports (available for future use)
- refactor(kanal): remove all dead pkexec_* functions
- Now that save-all handles everything in one root call, the individual
pkexec_* helpers are unreachable from the GUI and not needed as a public
API either.
- privileged.py:
- remove pkexec_set, pkexec_apply, pkexec_apply_stream
- remove pkexec_save_machine, pkexec_save_machine_stream
- remove pkexec_save_features_stream, pkexec_save_apps_stream,
  pkexec_save_extensions_stream
- remove KEY_FEATURE_* imports (only needed by save_features_stream)
- move pkexec_save_all_stream next to run_upgrade (single public section)
- guard apps/extensions with 'if payload.get(...)' to tolerate empty lists
- backend.py:
- import only pkexec_save_all_stream + run_upgrade from privileged
- __all__: drop all removed symbols
- feat(kanal): unified Apply + Save buttons replacing per-tab saves
- cli.py:
- add import json
- add _cmd_save_all: saves features/apps/extensions/machine in one
  root process; with --rebuild also sets channel + runs nixos-rebuild
- add save-all parser: --features-json JSON, --apps, --extensions,
  machine flags, --rebuild, --channel, --operation, --preset, --flake-url
- privileged.py:
- add import json
- add pkexec_save_all_stream(payload, rebuild): builds save-all cmd,
  delegates to _pkexec_stream
- backend.py:
- export pkexec_save_all_stream
- window.py:
- remove per-tab Save buttons, Machine Save, channel Activate
- add Apply button (header right, suggested-action) → save-all --rebuild
- add Save button (action bar) → save-all without rebuild
- add _collect_all_payload(): single dict with features/extensions/apps/
  machine/channel/operation/preset/flake_url from current UI state
- add _on_apply_clicked, _on_save_all_clicked: both spawn thread with
  _run_stream_worker + pkexec_save_all_stream
- add _done_action(msg, err, btn, label): unified result callback
- remove _on_tab_changed, _on_activate_clicked, _on_save_clicked,
  _on_tab_save_clicked, _worker_activate, _worker_save,
  _done_activate, _done_save, _done_tab_save, _SAVE_STREAMS, _tab_payload
- fix(kanal): bundle update-symbolic icon and register icon search path
- - copy assets/update-symbolic.svg into package at
  src/kanal/icons/hicolor/scalable/actions/
- add icons glob to pyproject.toml package-data
- ChannelApp._on_activate: register icons/ dir with Gtk.IconTheme
  so the reload button icon renders correctly in devShell and installed
- refactor(kanal): extract stream/worker helpers, remove worker duplication
- privileged.py:
- extract _pkexec_stream(cmd, dry_msg) base generator
- all *_stream functions collapse to cmd-build + yield from _pkexec_stream
- window.py:
- add _reset_log() — shared 4-line log-panel reset
- add _run_stream_worker(stream_fn, success_msg, dry_msg, cmd_name, done_cb)
- add _tab_payload(tab, rows) — collect row states into dict|list
- add _SAVE_STREAMS dispatch table keyed by save_cmd
- _on_tab_save_clicked: pure dispatch via _SAVE_STREAMS, no tab_id conditions
- collapse _worker_save_features/_worker_save_apps/_worker_save_extensions
- _worker_activate and _worker_save delegate to _run_stream_worker
- IDEA.md: park YAML-driven features.nix generation plan
- feat: in progress refactor app
- refactor(kanal): unify all dynamic tabs under default.yaml tabs catalog
- - default.yaml restructured: top-level 'tabs' list with type,
  nix_key, save_cmd, items; extensions + apps moved in from constants.py
- constants.py: single _load_catalog(); derives FEATURE_CATALOG,
  GNOME_EXTENSIONS_CATALOG, FLATPAK_CATALOG, KEY_FLATPAK_PACKAGES,
  KEY_GNOME_EXTENSIONS from YAML; exposes get_tab_catalog()
- window.py: single generic loop builds all catalog tabs (features,
  extensions, apps); _tab_rows/tab_save_btns keyed by tab id;
  _on_tab_save_clicked dispatches to correct worker by tab type;
  _done_tab_save replaces 3 separate done_* callbacks
- backend.py: expose TAB_CATALOG + get_tab_catalog
- Adding a new tab now requires only an entry in default.yaml.
- refactor(kanal): data-driven feature catalog via default.yaml
- - Add default.yaml bundled in package with all 8 features (key, title,
  subtitle, default, optional extra side-effects)
- constants.py: load catalog at import time; derive ALL_FEATURES and
  KEY_FEATURE_* constants dynamically; expose get_feature_catalog()
- machine.py: save_features dispatches extra side-effects generically;
  removes hardcoded tailscale/GNOME extension logic
- window.py: Features tab builds SwitchRows in a catalog loop;
  save handler collects state via dict comprehension
- backend.py: expose FEATURE_CATALOG and get_feature_catalog
- pyproject.toml: include *.yaml in package-data
- flake.nix: add pyyaml dependency
- Adding a new feature now requires only: one entry in default.yaml +
one mkOption/mkIf block in features.nix.
- fix(features): grant uinput access for Solaar device remapping
- fix(features): enable Solaar graphical app for logitechWireless
- feat(features): add logitech wireless (Solaar) feature flag
- - modules/system/features.nix: logitechWireless option using
  hardware.logitech.wireless.enable (includes Solaar + udev rules)
- constants.py: KEY_FEATURE_LOGITECH_WIRELESS + ALL_FEATURES
- backend.py, privileged.py, cli.py, window.py: full kanal wiring
- AGENTS.md: document how to add a feature flag across all 7 layers
- fix(features): sync tailscale-status extension into machine.nix via save_features
- fix(features): enable tailscale-status via dconf directly, avoid mkForce collision
- feat(features): add Tailscale feature with tailscale-status GNOME extension
- fix(features): use pkgs.zfs.kernelModuleAttribute for dynamic ZFS module resolution
- fix(features): ZFS tools only, no kernel module at boot to avoid auto-import panic
- fix(features): use pkgs.zfs.kernelModuleAttribute for extraModulePackages
- fix(features): load ZFS as post-boot module only, avoid initrd scan panic
- feat(features): add ZFS support option (6.12 LTS kernel, hostId)
- fix(features): add pkgs to module args for canon-cups-ufr2
- feat(features): add Canon UFR II printer driver option
- Adds notenix.features.canonPrinter — enables CUPS + canon-cups-ufr2
for Canon LBP/MF series printers (LBP633CDW etc).
Wired through all kanal layers: nix module, constants, backend, cli,
privileged pkexec, and GUI Features tab.
- fix(kanal): wire nvidia feature through cli and pkexec flag map
- fix(kanal): export KEY_FEATURE_NVIDIA from backend
- feat(features): add nvidia proprietary driver option
- Adds notenix.features.nvidia boolean that enables hardware.nvidia with
modesetting and the stable driver package. Exposed in Kanal Features tab.
- fix(autoupgrade): use path:/etc/nixos as flakeRepo default
- nixos-upgrade was building from github:n1x05/notenix directly, which
excludes machine.nix, wiping the user config on every upgrade.
- Fix: flakeRepo defaults to path:/etc/nixos so autoupgrade always builds
the local flake (which includes machine.nix). Channel branch is
controlled by inputs.notenix.url in /etc/nixos/flake.nix, which kanal
already updates correctly when switching channels.
- fix(kanal): never use root as username fallback in _env_fallbacks
- fix(gnome): use TEXTDOMAINDIR to find xdg-user-dirs translations in Nix store
- fix(desktop): use --flake flag for nix flake update in launchers
- fix(gnome): use --force in xdg-user-dirs-update to always apply locale
- fix(gnome): run xdg-user-dirs-update on login to init localized folders
- fix(desktop): update launcher done message to reflect kgx close behaviour
- fix(desktop): update flake.lock before rebuild in launchers
- fix(gnome): use pkgs-unstable for gtk4-desktop-icons-ng-ding extension
- fix(kanal): add missing _cmd_set_extensions function to cli.py
- feat(gnome/kanal): user-configurable GNOME extensions via Kanal Extensions tab
- - gnome.nix: add notenix.desktop.gnome.extensions option (list of IDs);
  extension packages and dconf UUIDs derived dynamically; gtk4-ding
  settings applied via lib.optionalAttrs when that extension is enabled
- constants.py: add KEY_GNOME_EXTENSIONS + GNOME_EXTENSIONS_CATALOG
  (appindicator, dash-to-dock, gsconnect, gtk4-desktop-icons-ng-ding)
- machine.py: read_extensions() / save_extensions()
- cli.py: set-extensions subcommand
- privileged.py: pkexec_save_extensions_stream()
- backend.py: re-export all new symbols
- window.py: Extensions tab with SwitchRow per extension, Save button
- feat(desktop): add --refresh to rebuild launchers to fetch latest flake
- fix(desktop): use standard freedesktop icon names for rebuild launchers
- feat(kanal): add RustDesk to Flatpak catalog
- feat(kanal): add Chromium to Flatpak catalog
- feat(kanal): Apps tab — Flatpak app picker with checkboxes
- fix(install): use --no-filesystems instead of fragile sed to strip fileSystems
- fix(install): stub hardware-configuration.nix before disko evaluates flake
- feat: add Apply Update desktop launchers with user-friendly EN/SL text
- fix: Cinnamon dconf/icons, GNOME GDM cursor, kanal forces boot on DM switch
- feat: add Firefox + apps to Cinnamon taskbar favorites via dconf
- fix: remove icon-theme overrides, keep only cursor-theme fix
- fix: remove cursor-theme override from Cinnamon, use default
- fix: lock Adwaita cursor-theme in GNOME user dconf to survive DM switches
- feat: silent boot with Plymouth splash
- feat: add RustDesk feature + open GSConnect firewall ports in GNOME
- feat: change RustDesk to unstable
- fix: lock icon-theme=Adwaita in GNOME user dconf to survive Cinnamon switches
- feat: install rustdesk from nixpkgs-unstable
- fix: import pkgs-unstable with allowUnfree=true for rustdesk/libsciter
- fix: install script
- kanal: refactor into src layout with focused modules
- - Split 905-line backend.py monolith into six focused modules:
  constants.py (paths, keys, env flags), metadata.py (Status,
  cache, GitHub/nix-eval refresh), nixfiles.py (pure Nix file
  parsers + read_status/set_channel), machine.py (identity,
  locale, feature flags), locales.py (locale + XKB discovery),
  privileged.py (pkexec / nixos-rebuild subprocess helpers)
- backend.py kept as a re-export façade so cli.py and gui/window.py
  need zero import changes
- Migrate to src/ layout (pyproject.toml: package-dir = src)
- Add tests/ with 21 passing unit tests for pure functions
  (nixfiles, machine, locales) — no root or GTK required
- Add pytest to devShell packages in flake.nix
- Fix mkdir-before-dry-run bug in set_channel and save_machine
- Assisted-by: GitHub Copilot:claude-sonnet-4-6
- docs: add assisted-by llm info
- feat: desktop-lite, vm, documentation
- - Properly configured initial desktop-lite preset
- Cleaned up vm config, optimized for better performance
- Updated documentation, cleaned it up and move to sepparate files
- initial commit
- initial commit
