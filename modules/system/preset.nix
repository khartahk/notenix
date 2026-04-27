{ config, lib, ... }:

# Presets are named bundles of module defaults.  A preset sets options via
# lib.mkDefault so any explicit option in the host config or overrides file
# still wins.  The default preset is "desktop" (full GNOME experience).

with lib;

let cfg = config.notenix.preset; in
{
  options.notenix.preset = mkOption {
    type        = types.enum [ "desktop" "minimal" ];
    default     = "desktop";
    description = ''
      Named configuration preset that controls which notenix features are
      enabled by default.

      desktop  — full GNOME desktop with Flatpak, sound, bluetooth, printing
      minimal  — headless / server: no desktop, no Flatpak, only essentials
    '';
  };

  config = mkMerge [
    # ── desktop ─────────────────────────────────────────────────────────────
    (mkIf (cfg == "desktop") {
      notenix.desktop.gnome.enable        = mkDefault true;
      notenix.applications.flatpak.enable = mkDefault true;
      notenix.hardware.sound.enable       = mkDefault true;
      notenix.hardware.bluetooth.enable   = mkDefault true;
      notenix.hardware.printing.enable    = mkDefault true;
    })

    # ── minimal ─────────────────────────────────────────────────────────────
    (mkIf (cfg == "minimal") {
      notenix.desktop.gnome.enable        = mkDefault false;
      notenix.applications.flatpak.enable = mkDefault false;
      notenix.hardware.sound.enable       = mkDefault false;
      notenix.hardware.bluetooth.enable   = mkDefault false;
      notenix.hardware.printing.enable    = mkDefault false;
    })
  ];
}
