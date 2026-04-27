{ config, lib, ... }:

# Sudo policy for the wheel group.

let
  cfg = config.notenix.security.sudo;
in
{
  options.notenix.security.sudo = {
    wheelNeedsPassword = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Require password for wheel group sudo.";
    };
  };

  config = {
    security.sudo.wheelNeedsPassword = cfg.wheelNeedsPassword;
  };
}
