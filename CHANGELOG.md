## Unreleased

### Feat

- **dev**: add changelog target, auto-update via pre-commit, fix changelog path
- **dev**: add gh CLI to devShell, GitHub release creation in Makefile
- **releases**: add update notification with GitHub release notes, commitizen versioning, and Makefile release targets
- **features**: add steam feature flag with gamescope and remote play
- **kanal**: add experimental package sources for extensions
- **kanal**: add Slovenian i18n via gettext
- **kanal**: Apply button always visible; label Update/Apply by dirty state
- **kanal**: disable Save/Apply buttons until something changes
- **kanal**: unified Apply + Save buttons replacing per-tab saves
- in progress refactor app
- **features**: add logitech wireless (Solaar) feature flag
- **features**: add Tailscale feature with tailscale-status GNOME extension
- **features**: add ZFS support option (6.12 LTS kernel, hostId)
- **features**: add Canon UFR II printer driver option
- **features**: add nvidia proprietary driver option
- **gnome/kanal**: user-configurable GNOME extensions via Kanal Extensions tab
- **desktop**: add --refresh to rebuild launchers to fetch latest flake
- **kanal**: add RustDesk to Flatpak catalog
- **kanal**: add Chromium to Flatpak catalog
- **kanal**: Apps tab — Flatpak app picker with checkboxes
- add Apply Update desktop launchers with user-friendly EN/SL text
- add Firefox + apps to Cinnamon taskbar favorites via dconf
- silent boot with Plymouth splash
- add RustDesk feature + open GSConnect firewall ports in GNOME
- change RustDesk to unstable
- install rustdesk from nixpkgs-unstable
- desktop-lite, vm, documentation

### Fix

- **dev**: run cz from pkgs/kanal so pep621 provider finds pyproject.toml
- **dev**: pass --repo to gh release create since origin is Gitea
- **dev**: remove --quiet flag unsupported by this pre-commit version
- **gnome**: remove postPatch shell-version hack; add build-time compat warning
- **gnome**: patch upstream-main ding metadata.json to include GNOME 49 shell-version
- **features**: add missing notenix.features.experimental option
- **kanal/i18n**: use ASCII ... instead of U+2026 ellipsis to fix translation lookup
- **autoupgrade**: add --upgrade to default flags so service updates flake inputs
- **kanal**: remove locale.setlocale causing crash in restricted environments
- **kanal**: disable Save when Apply is clicked
- **kanal**: bundle update-symbolic icon and register icon search path
- **features**: grant uinput access for Solaar device remapping
- **features**: enable Solaar graphical app for logitechWireless
- **features**: sync tailscale-status extension into machine.nix via save_features
- **features**: enable tailscale-status via dconf directly, avoid mkForce collision
- **features**: use pkgs.zfs.kernelModuleAttribute for dynamic ZFS module resolution
- **features**: ZFS tools only, no kernel module at boot to avoid auto-import panic
- **features**: use pkgs.zfs.kernelModuleAttribute for extraModulePackages
- **features**: load ZFS as post-boot module only, avoid initrd scan panic
- **features**: add pkgs to module args for canon-cups-ufr2
- **kanal**: wire nvidia feature through cli and pkexec flag map
- **kanal**: export KEY_FEATURE_NVIDIA from backend
- **autoupgrade**: use path:/etc/nixos as flakeRepo default
- **kanal**: never use root as username fallback in _env_fallbacks
- **gnome**: use TEXTDOMAINDIR to find xdg-user-dirs translations in Nix store
- **desktop**: use --flake flag for nix flake update in launchers
- **gnome**: use --force in xdg-user-dirs-update to always apply locale
- **gnome**: run xdg-user-dirs-update on login to init localized folders
- **desktop**: update launcher done message to reflect kgx close behaviour
- **desktop**: update flake.lock before rebuild in launchers
- **gnome**: use pkgs-unstable for gtk4-desktop-icons-ng-ding extension
- **kanal**: add missing _cmd_set_extensions function to cli.py
- **desktop**: use standard freedesktop icon names for rebuild launchers
- **install**: use --no-filesystems instead of fragile sed to strip fileSystems
- **install**: stub hardware-configuration.nix before disko evaluates flake
- Cinnamon dconf/icons, GNOME GDM cursor, kanal forces boot on DM switch
- remove icon-theme overrides, keep only cursor-theme fix
- remove cursor-theme override from Cinnamon, use default
- lock Adwaita cursor-theme in GNOME user dconf to survive DM switches
- lock icon-theme=Adwaita in GNOME user dconf to survive Cinnamon switches
- import pkgs-unstable with allowUnfree=true for rustdesk/libsciter
- install script

### Refactor

- **kanal**: unify constants imports + drop dead code
- **kanal**: make all remaining code fully data-driven from default.yaml
- **kanal**: deduplicate machine.py, backend.py, window.py, cli.py
- **kanal**: generate set-* subcommands from TAB_CATALOG loop
- **kanal**: deduplicate cli.py handlers with shared helpers
- **kanal**: derive CLI feature flags and machine args from default.yaml
- **kanal**: move machine field keys + flags into default.yaml
- **kanal**: remove all dead pkexec_* functions
- **kanal**: extract stream/worker helpers, remove worker duplication
- **kanal**: unify all dynamic tabs under default.yaml tabs catalog
- **kanal**: data-driven feature catalog via default.yaml
