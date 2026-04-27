{ config, lib, ... }:

# Bluetooth support with optional Blueman GUI.

let
  cfg = config.notenix.hardware.bluetooth;
in
{
  options.notenix.hardware.bluetooth = {
    enable = lib.mkEnableOption "Bluetooth support";

    powerOnBoot = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Power on the Bluetooth adapter automatically at boot.";
    };

    blueman = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Enable the Blueman graphical Bluetooth manager.";
    };
  };

  config = lib.mkIf cfg.enable {
    hardware.bluetooth.enable       = true;
    hardware.bluetooth.powerOnBoot  = cfg.powerOnBoot;
    services.blueman.enable         = lib.mkIf cfg.blueman true;
  };
}
