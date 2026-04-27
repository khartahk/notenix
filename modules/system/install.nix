{ config, lib, ... }:

# Install-time identity module.
# Provides options for values typically set interactively during installation
# (hostname, primary user, timezone, locale, keyboard).
# The installer writes /etc/nixos/notenix-install-overrides.nix which overrides
# these defaults via lib.mkForce, keeping personal data out of the shared repo.

let
  cfg = config.notenix.system.install;
in
{
  options.notenix.system.install = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Install-time identity configuration (hostname, user, locale, keyboard).";
    };

    hostName = lib.mkOption {
      type    = lib.types.str;
      default = "notenix";
      description = "Machine hostname.";
    };

    userName = lib.mkOption {
      type    = lib.types.str;
      default = "uporabnik";
      description = "Primary user account name.";
    };

    userDescription = lib.mkOption {
      type    = lib.types.str;
      default = "Uporabnik";
      description = "Full name / description for the primary user (optional).";
    };

    userGroups = lib.mkOption {
      type    = lib.types.listOf lib.types.str;
      default = [ "wheel" "networkmanager" ];
      description = "Extra groups for the primary user.";
    };

    timeZone = lib.mkOption {
      type    = lib.types.str;
      default = "Europe/Ljubljana";
      example = "UTC";
      description = "System timezone (TZ database name).";
    };

    locale = lib.mkOption {
      type    = lib.types.str;
      default = "sl_SI.UTF-8";
      example = "en_US.UTF-8";
      description = "Default locale (LANG and all LC_* categories).";
    };

    keyboardLayout = lib.mkOption {
      type    = lib.types.str;
      default = "si";
      example = "us";
      description = "XKB keyboard layout code for the graphical session (X11/Wayland).";
    };

    consoleKeyMap = lib.mkOption {
      type    = lib.types.str;
      default = "slovene";
      example = "us";
      description = ''
        Console keymap name (passed to loadkeys).
        Often differs from the XKB name, e.g. XKB "si" → console "slovene".
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    networking.hostName = cfg.hostName;

    time.timeZone = cfg.timeZone;

    i18n.defaultLocale = cfg.locale;
    i18n.extraLocaleSettings = {
      LC_ADDRESS        = cfg.locale;
      LC_IDENTIFICATION = cfg.locale;
      LC_MEASUREMENT    = cfg.locale;
      LC_MONETARY       = cfg.locale;
      LC_NAME           = cfg.locale;
      LC_NUMERIC        = cfg.locale;
      LC_PAPER          = cfg.locale;
      LC_TELEPHONE      = cfg.locale;
      LC_TIME           = cfg.locale;
    };

    console.keyMap = cfg.consoleKeyMap;
    services.xserver.xkb.layout = cfg.keyboardLayout;

    users.users.${cfg.userName} = {
      isNormalUser = true;
      description  = cfg.userDescription;
      extraGroups  = cfg.userGroups;
    };
  };
}
