{ config, lib, pkgs, ... }:

# GNOME desktop environment with opinionated defaults.

let
  cfg = config.notenix.desktop.gnome;
in
{
  options.notenix.desktop.gnome = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = false;
      description = "GNOME desktop environment.";
    };

    autoSuspend = lib.mkOption {
      type    = lib.types.bool;
      default = false;
      description = "Allow GDM to auto-suspend the machine.";
    };

    favoriteApps = lib.mkOption {
      type    = lib.types.listOf lib.types.str;
      default = [
        "firefox.desktop"
        "org.gnome.Nautilus.desktop"
        "org.gnome.Calculator.desktop"
      ];
      description = "Dock favourite apps (desktop file IDs).";
    };

    excludePackages = lib.mkOption {
      type    = lib.types.listOf lib.types.package;
      default = with pkgs; [
        gnome-tour
        gnome-music
        gnome-maps
        gnome-contacts
        gnome-weather
        epiphany   # GNOME Web — ship Firefox instead
        geary      # email client
        totem      # Videos
        yelp       # Help browser
      ];
      defaultText = lib.literalExpression "[ pkgs.gnome-tour pkgs.epiphany … ]";
      description = "Packages to exclude from the default GNOME install.";
    };

    extraPackages = lib.mkOption {
      type    = lib.types.listOf lib.types.package;
      default = [];
      example = lib.literalExpression "[ pkgs.gnome-tweaks ]";
      description = "Additional packages to install alongside GNOME.";
    };

    power = {
      acSleepType = lib.mkOption {
        type    = lib.types.str;
        default = "nothing";
        description = "GNOME power action when idle on AC power (\"nothing\", \"suspend\", \"hibernate\").";
      };
      acSleepTimeout = lib.mkOption {
        type    = lib.types.int;
        default = 0;
        description = "Idle timeout on AC power in seconds. 0 = never.";
      };
      batterySleepType = lib.mkOption {
        type    = lib.types.str;
        default = "nothing";
        description = "GNOME power action when idle on battery.";
      };
      batterySleepTimeout = lib.mkOption {
        type    = lib.types.int;
        default = 0;
        description = "Idle timeout on battery in seconds. 0 = never.";
      };
    };

    dockFixed = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Show the dash-to-dock panel permanently (true) or auto-hide it (false).";
    };
  };

  config = lib.mkIf cfg.enable {
    services.xserver.enable = true;
    services.displayManager.gdm = {
      enable      = true;
      autoSuspend = cfg.autoSuspend;
    };
    services.desktopManager.gnome.enable = true;

    environment.gnome.excludePackages = cfg.excludePackages;

    programs.dconf.profiles.user.databases = [
      {
        lockAll  = false;
        settings = {
          "org/gnome/shell" = {
            enabled-extensions = [
              pkgs.gnomeExtensions.appindicator.extensionUuid
              pkgs.gnomeExtensions.dash-to-dock.extensionUuid
              pkgs.gnomeExtensions.gsconnect.extensionUuid
#              pkgs.gnomeExtensions.gtk4-desktop-icons-ng-ding.extensionUuid
            ];
            favorite-apps = cfg.favoriteApps;
          };

          "org/gnome/settings-daemon/plugins/power" = {
            sleep-inactive-ac-type         = cfg.power.acSleepType;
            sleep-inactive-ac-timeout      = lib.gvariant.mkUint32 cfg.power.acSleepTimeout;
            sleep-inactive-battery-type    = cfg.power.batterySleepType;
            sleep-inactive-battery-timeout = lib.gvariant.mkUint32 cfg.power.batterySleepTimeout;
          };

          "org/gnome/shell/extensions/dash-to-dock" = {
            custom-theme-shrink = true;
            dash-max-icon-size  = lib.gvariant.mkUint32 42;
            dock-fixed          = cfg.dockFixed;
            autohide            = !cfg.dockFixed;
            intellihide         = false;
          };

#          "org/gnome/shell/extensions/gtk4-ding" = {
#            show-home  = false;
#            show-trash = false;
#          };
        };
      }
    ];

    environment.systemPackages = with pkgs; [
      firefox
      gnome-calculator
      gnome-calendar
      gnome-screenshot
      gnome-console
      gnome-software
      gnomeExtensions.appindicator
      gnomeExtensions.dash-to-dock
      gnomeExtensions.gsconnect
#      gnomeExtensions.gtk4-desktop-icons-ng-ding
      dconf
      libnotify
      gawk
      gnugrep
    ] ++ cfg.extraPackages;
  };
}
