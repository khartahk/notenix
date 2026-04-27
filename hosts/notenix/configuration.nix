# Reference host configuration — see README.md for customisation instructions.
{ lib, ... }:
{
  imports = lib.optional
    (builtins.pathExists /etc/nixos/notenix-install-overrides.nix)
    /etc/nixos/notenix-install-overrides.nix;

  notenix.hardware.bluetooth.enable = true;

  system.stateVersion = "25.11"; # do not change after first install
}
