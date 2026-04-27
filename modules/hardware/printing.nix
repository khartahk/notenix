{ config, lib, ... }:

# CUPS printing with Avahi network printer discovery.

let
  cfg = config.notenix.hardware.printing;
in
{
  options.notenix.hardware.printing = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Printing support via CUPS.";
    };

    openFirewall = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Open firewall ports for Avahi/mDNS printer discovery.";
    };
  };

  config = lib.mkIf cfg.enable {
    services.printing.enable = true;
    services.avahi = {
      enable      = true;
      nssmdns4    = true;
      openFirewall = cfg.openFirewall;
    };
  };
}
