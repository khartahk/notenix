{ config, lib, ... }:

# Nix daemon configuration: flakes, GC, store optimisation.

let
  cfg    = config.notenix.system.nix;
  inputs = config._module.args.inputs or {};
in
{
  options.notenix.system.nix = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Enable Nix configuration with flakes and store optimisation.";
    };

    autoGC = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Enable automatic garbage collection.";
    };

    gcDays = lib.mkOption {
      type    = lib.types.str;
      default = "weekly";
      description = "How often to run garbage collection (systemd.time format).";
    };

    gcOptions = lib.mkOption {
      type    = lib.types.str;
      default = "--delete-older-than 7d";
      description = "Options passed to nix-collect-garbage.";
    };

    autoOptimise = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Enable automatic store optimisation.";
    };

    trustedUsers = lib.mkOption {
      type    = lib.types.listOf lib.types.str;
      default = [ "root" "@wheel" ];
      description = "Users trusted to use Nix.";
    };
  };

  config = lib.mkIf cfg.enable {
    nix = {
      channel.enable = false;
      nixPath = lib.mkIf (inputs ? nixpkgs) [ "nixpkgs=${inputs.nixpkgs}" ];

      settings = {
        experimental-features = [ "nix-command" "flakes" ];
        trusted-users          = cfg.trustedUsers;
        auto-optimise-store    = cfg.autoOptimise;
      };

      gc = lib.mkIf cfg.autoGC {
        automatic  = true;
        dates      = cfg.gcDays;
        options    = cfg.gcOptions;
        persistent = false;
      };

      optimise = lib.mkIf cfg.autoOptimise {
        automatic = true;
        dates     = [ cfg.gcDays ];
      };
    };

    # Allow non-free packages (firmware, drivers, etc.)
    nixpkgs.config.allowUnfree = lib.mkDefault true;

    # Don't hang waiting for services to stop on shutdown
    systemd.settings.Manager.DefaultTimeoutStopSec = "10s";
  };
}
