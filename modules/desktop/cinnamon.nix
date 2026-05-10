{ config, lib, pkgs, ... }:

# Cinnamon desktop environment.

let
  cfg = config.notenix.desktop.cinnamon;
in
{
  options.notenix.desktop.cinnamon = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = false;
      description = "Cinnamon desktop environment.";
    };

    extraPackages = lib.mkOption {
      type    = lib.types.listOf lib.types.package;
      default = [];
      description = "Extra packages to add to the Cinnamon desktop.";
    };
  };

  config = lib.mkIf cfg.enable {
    services.xserver = {
      enable                         = true;
      desktopManager.cinnamon.enable = true;
      displayManager.lightdm.enable  = true;
    };

    # dconf defaults for Cinnamon: taskbar favourites
    programs.dconf.enable = true;
    programs.dconf.profiles.user.databases = [
      {
        lockAll = false;
        settings = {
          "org/cinnamon" = {
            favorite-apps = [
              "firefox.desktop"
              "nemo.desktop"
              "org.gnome.Calculator.desktop"
              "org.gnome.Console.desktop"
            ];
          };
        };
      }
    ];

    # Typical apps shipped with a Cinnamon desktop
    environment.systemPackages = with pkgs; [
      # File management
      nemo-with-extensions
      gnome-disk-utility
      baobab                   # disk usage analyser

      # Media
      celluloid                # video player (MPV frontend)
      rhythmbox                # music player
      eog                      # image viewer

      # App store
      gnome-software

      # Productivity
      gnome-calculator
      evince                   # PDF viewer

      # System tools
      gnome-system-monitor
      gparted

      # Communication / web
      firefox

      # Theming
      mint-themes
      mint-y-icons
      adwaita-icon-theme   # Adwaita cursor fallback
      gnome-themes-extra   # Adwaita GTK theme
    ] ++ cfg.extraPackages;
  };
}
