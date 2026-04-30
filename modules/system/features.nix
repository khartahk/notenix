{ config, lib, ... }:

# Optional feature flags that can be toggled independently of the preset.
# Written to machine.nix by kanal; each defaults to false so the base system
# remains lean until the user explicitly enables a feature.

with lib;

let
  cfg = config.notenix.features;
in
{
  options.notenix.features = {
    ssh = mkOption {
      type        = types.bool;
      default     = false;
      description = "Enable OpenSSH server (password auth, root login disabled).";
    };

    kiosk = mkOption {
      type        = types.bool;
      default     = false;
      description = "Kiosk mode: auto-login to a single-app fullscreen session.";
    };
  };

  config = mkMerge [
    (mkIf cfg.ssh {
      services.openssh = {
        enable                          = true;
        openFirewall                    = true;
        settings.PasswordAuthentication = true;
        settings.PermitRootLogin        = "no";
      };
    })

    # Kiosk: the host config still needs to set the actual app; this just
    # enables the infrastructure (auto-login + no screen lock).
    (mkIf cfg.kiosk {
      services.displayManager.autoLogin.enable = mkDefault true;
      programs.dconf.profiles.user.databases = mkAfter [
        {
          lockAll  = false;
          settings."org/gnome/desktop/screensaver".lock-enabled = false;
          settings."org/gnome/desktop/session".idle-delay = config.lib.gvariant.mkUint32 0;
        }
      ];
    })
  ];
}
