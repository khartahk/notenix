{ config, lib, ... }:

# PipeWire (default) or PulseAudio sound backend.

let
  cfg = config.notenix.hardware.sound;
in
{
  options.notenix.hardware.sound = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Sound support.";
    };

    backend = lib.mkOption {
      type    = lib.types.enum [ "pipewire" "pulseaudio" ];
      default = "pipewire";
      description = "Sound backend to use.";
    };

    pipewire = {
      alsa32Bit = lib.mkOption {
        type    = lib.types.bool;
        default = true;
        description = "Enable 32-bit ALSA support (needed for some games/Wine).";
      };
      jack = lib.mkOption {
        type    = lib.types.bool;
        default = false;
        description = "Enable JACK compatibility layer.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    services.pulseaudio.enable = lib.mkForce (cfg.backend == "pulseaudio");

    security.rtkit.enable = cfg.backend == "pipewire";

    services.pipewire = lib.mkIf (cfg.backend == "pipewire") {
      enable           = true;
      alsa.enable      = true;
      alsa.support32Bit = cfg.pipewire.alsa32Bit;
      pulse.enable     = true;
      jack.enable      = cfg.pipewire.jack;
    };
  };
}
