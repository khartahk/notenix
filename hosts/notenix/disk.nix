# Declarative disk layout via disko.
# Default: GPT, 512 MiB EFI partition, rest as ext4 root.
#
# !! The target disk is /dev/sda by default.
# !! Override disk.device in your host configuration if different,
# !!   e.g.  notenix.disk.device = "/dev/nvme0n1";
#
# During installation disko will partition and format the disk automatically:
#
#   sudo nix run github:nix-community/disko/latest -- \
#     --mode disko \
#     --flake github:n1x05/notenix#notenix
#
# Then install:
#
#   sudo nixos-install --no-root-passwd \
#     --flake github:n1x05/notenix#notenix
#
# Or use the combined one-liner (see README.md).

{ config, lib, ... }:

let
  device = config.notenix.disk.device;
in
{
  options.notenix.disk.device = lib.mkOption {
    type = lib.types.str;
    default = "/dev/sda";
    example = "/dev/nvme0n1";
    description = ''
      Block device to install notenix onto.
      ALL DATA ON THIS DEVICE WILL BE ERASED.
    '';
  };

  config.disko.devices = {
    disk.main = {
      inherit device;
      type = "disk";
      content = {
        type = "gpt";
        partitions = {
          ESP = {
            size = "512M";
            type = "EF00"; # EFI System Partition
            content = {
              type = "filesystem";
              format = "vfat";
              mountpoint = "/boot";
              mountOptions = [ "umask=0077" ];
            };
          };
          root = {
            size = "100%";
            content = {
              type = "filesystem";
              format = "ext4";
              mountpoint = "/";
            };
          };
        };
      };
    };
  };
}
