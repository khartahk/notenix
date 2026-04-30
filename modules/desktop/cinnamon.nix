{ config, lib, ... }:

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
  };

  config = lib.mkIf cfg.enable {
    services.xserver = {
      enable              = true;
      desktopManager.cinnamon.enable = true;
      displayManager.lightdm.enable  = true;
    };
    hardware.pulseaudio.enable = lib.mkDefault false;
    services.pipewire = {
      enable            = lib.mkDefault true;
      alsa.enable       = lib.mkDefault true;
      alsa.support32Bit = lib.mkDefault true;
      pulse.enable      = lib.mkDefault true;
    };
  };
}
