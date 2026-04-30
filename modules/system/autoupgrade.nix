{ config, lib, pkgs, ... }:

# Automatic NixOS system upgrades via the built-in system.autoUpgrade mechanism.

with lib;

let
  cfg = config.notenix.system.autoupgrade;

  notifyScript = pkgs.writeShellScript "notenix-notify-users" ''
    set -euo pipefail
    message="$1"
    urgency="''${2:-normal}"
    for uid_path in /run/user/[0-9]*; do
      uid=$(basename "$uid_path")
      user=$(id -nu "$uid" 2>/dev/null || true)
      [ -z "$user" ] && continue
      bus="unix:path=/run/user/$uid/bus"
      DBUS_SESSION_BUS_ADDRESS="$bus" \
        DISPLAY=":0" \
        runuser -u "$user" -- \
        ${pkgs.libnotify}/bin/notify-send \
          --app-name="notenix" \
          --urgency="$urgency" \
          "System Update" "$message" 2>/dev/null || true
    done
  '';

  diffNotifyScript = pkgs.writeShellScript "notenix-post-upgrade-notify" ''
    set -euo pipefail
    current=/nix/var/nix/profiles/system
    booted=/run/booted-system
    changed=$(
      ${pkgs.nix}/bin/nix store diff-closures "$booted" "$current" 2>/dev/null \
        | ${pkgs.gawk}/bin/awk '/→/' \
        | wc -l
    ) || true
    if [ "$changed" -gt 0 ]; then
      ${notifyScript} "System updated — restart when convenient." "normal"
    fi
  '';
in
{
  options.notenix.system.autoupgrade = {
    enable = mkOption {
      type    = types.bool;
      default = true;
      description = "NixOS automatic system upgrades.";
    };

    hostName = mkOption {
      type    = types.nullOr types.str;
      default = null;
      example = "notenix";
      description = ''
        The flake output name to upgrade to (the part after # in the flake URL).
        Defaults to networking.hostName when null.
      '';
    };

    flakeRepo = mkOption {
      type    = types.str;
      default = "github:n1x05/notenix";
      example = "path:/etc/nixos";
      description = "Flake URL of the NixOS configuration repository.";
    };

    dates = mkOption {
      type    = types.str;
      default = "daily";
      example = "daily";
      description = "How often to run the upgrade (systemd.time format).";
    };

    randomizedDelaySec = mkOption {
      type    = types.str;
      default = "1h";
      description = "Randomised delay added to the upgrade timer.";
    };

    allowReboot = mkOption {
      type    = types.bool;
      default = false;
      description = "Allow automatic reboots after upgrade.";
    };

    operation = mkOption {
      type    = types.enum [ "switch" "boot" ];
      default = "boot";
      description = ''
        nixos-rebuild operation: "boot" activates on next reboot (safe),
        "switch" activates immediately.
      '';
    };

    flags = mkOption {
      type    = types.listOf types.str;
      default = [];
      description = "Additional flags passed to nixos-rebuild.";
    };

    notify = mkOption {
      type    = types.bool;
      default = false;
      description = ''
        Send desktop notifications to logged-in users before and after the
        upgrade, with a summary of changed packages.
      '';
    };
  };

  config = mkIf cfg.enable {
    system.autoUpgrade = {
      enable     = true;
      flake      = "${cfg.flakeRepo}#${if cfg.hostName != null then cfg.hostName else config.networking.hostName}";
      dates              = cfg.dates;
      randomizedDelaySec = cfg.randomizedDelaySec;
      allowReboot        = cfg.allowReboot;
      operation          = cfg.operation;
      flags              = cfg.flags;
    };

    systemd.services."notenix-upgrade-post-notify" = mkIf cfg.notify {
      description = "Notify users of completed system upgrade with package diff";
      after       = [ "nixos-upgrade.service" ];
      wantedBy    = [ "nixos-upgrade.service" ];
      serviceConfig = {
        Type      = "oneshot";
        ExecStart = diffNotifyScript;
      };
    };

    environment.systemPackages = mkIf cfg.notify [ pkgs.libnotify ];
  };
}
