{ config, lib, ... }:

# NetworkManager with optional Wi-Fi firmware blobs.

let
  cfg = config.notenix.network.networkmanager;
in
{
  options.notenix.network.networkmanager = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "NetworkManager for managing network connections.";
    };

    enableRedistributableFirmware = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Enable redistributable Wi-Fi firmware (Intel iwlwifi, Realtek, Atheros, etc.).";
    };

    enableAllFirmware = lib.mkOption {
      type    = lib.types.bool;
      default = false;
      description = "Also enable non-redistributable firmware blobs (e.g. some Broadcom chips). Requires allowUnfree.";
    };
  };

  config = lib.mkIf cfg.enable {
    networking.networkmanager.enable = true;

    hardware.enableRedistributableFirmware =
      lib.mkDefault cfg.enableRedistributableFirmware;

    hardware.enableAllFirmware =
      lib.mkIf cfg.enableAllFirmware true;
  };
}
