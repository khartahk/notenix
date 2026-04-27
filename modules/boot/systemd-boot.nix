{ config, lib, pkgs, ... }:

# systemd-boot EFI bootloader.

let
  cfg = config.notenix.boot.systemd-boot;
in
{
  options.notenix.boot.systemd-boot = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "systemd-boot bootloader with EFI support.";
    };

    canTouchEfiVariables = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Whether the bootloader may modify EFI variables.";
    };

    timeout = lib.mkOption {
      type    = lib.types.int;
      default = 5;
      description = "Boot menu timeout in seconds (0 = skip menu).";
    };

    configurationLimit = lib.mkOption {
      type    = lib.types.int;
      default = 10;
      description = "Maximum number of boot entries to keep.";
    };

    kernelPackages = lib.mkOption {
      type    = lib.types.raw;
      default = pkgs.linuxPackages_latest;
      description = "Kernel package set to use.";
    };

    supportedFilesystems = lib.mkOption {
      type    = lib.types.listOf lib.types.str;
      default = [];
      example = [ "ntfs" "exfat" ];
      description = "Extra filesystem kernel modules to load at boot.";
    };
  };

  config = lib.mkIf cfg.enable {
    boot.loader = {
      systemd-boot = {
        enable             = true;
        configurationLimit = cfg.configurationLimit;
      };
      efi.canTouchEfiVariables = cfg.canTouchEfiVariables;
      timeout                  = cfg.timeout;
    };

    boot.kernelPackages      = cfg.kernelPackages;
    boot.supportedFilesystems = lib.mkIf (cfg.supportedFilesystems != []) cfg.supportedFilesystems;

    systemd.settings.Manager.DefaultTimeoutStopSec = "10s";
  };
}
