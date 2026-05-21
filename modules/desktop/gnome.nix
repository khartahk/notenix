{ config, lib, pkgs, pkgs-unstable, ... }:

# GNOME desktop environment with opinionated defaults.

let
  cfg = config.notenix.desktop.gnome;

  _extPkgs = {
    "appindicator"                = pkgs.gnomeExtensions.appindicator;
    "dash-to-dock"                = pkgs.gnomeExtensions.dash-to-dock;
    "gsconnect"                   = pkgs.gnomeExtensions.gsconnect;
    "gtk4-desktop-icons-ng-ding"  = pkgs-unstable.gnomeExtensions.gtk4-desktop-icons-ng-ding;
  };
  _activeExtIds  = builtins.filter (id: builtins.hasAttr id _extPkgs) cfg.extensions;
  _activeExtPkgs = map (id: _extPkgs.${id}) _activeExtIds;
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

    extensions = lib.mkOption {
      type    = lib.types.listOf lib.types.str;
      default = [ "appindicator" "dash-to-dock" "gsconnect" ];
      description = "GNOME extensions to install and enable. Valid IDs: appindicator, dash-to-dock, gsconnect, gtk4-desktop-icons-ng-ding.";
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

    # Set GDM cursor so it's not a blank square
    programs.dconf.profiles.gdm.databases = [
      {
        settings = {
          "org/gnome/desktop/interface" = {
            cursor-theme = "Adwaita";
          };
        };
      }
    ];

    programs.dconf.profiles.user.databases = [
      {
        # Locked: cursor + icon theme must always be Adwaita in GNOME regardless
        # of what a previous desktop environment wrote to the user's dconf.
        lockAll = true;
        settings = {
          "org/gnome/desktop/interface" = {
            cursor-theme = "Adwaita";
            icon-theme   = "Adwaita";
          };
        };
      }
      {
        lockAll  = false;
        settings = {
          "org/gnome/shell" = {
            enabled-extensions = map (id: _extPkgs.${id}.extensionUuid) _activeExtIds;
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
        } // lib.optionalAttrs (builtins.elem "gtk4-desktop-icons-ng-ding" cfg.extensions) {
          "org/gnome/shell/extensions/gtk4-ding" = {
            show-home  = false;
            show-trash = false;
          };
        };
      }
    ];

    environment.systemPackages = with pkgs; [
      adwaita-icon-theme
      firefox
      gnome-calculator
      gnome-calendar
      gnome-screenshot
      gnome-console
      gnome-software
      dconf
      libnotify
      gawk
      gnugrep
    ] ++ _activeExtPkgs ++ cfg.extraPackages;

    # GSConnect / KDE Connect ports
    networking.firewall.allowedTCPPortRanges = [{ from = 1714; to = 1764; }];
    networking.firewall.allowedUDPPortRanges = [{ from = 1714; to = 1764; }];
  };
}
