{ config, lib, pkgs, ... }:

# Flatpak support: adds Flathub remote and installs/updates apps via systemd
# one-shot services so the package list is managed declaratively.

let
  cfg = config.notenix.applications.flatpak;

  addFlathubScript = pkgs.writeShellScript "notenix-add-flathub" ''
    set -euo pipefail
    if ! ${pkgs.flatpak}/bin/flatpak remote-list --system | grep -q '^flathub'; then
      ${pkgs.flatpak}/bin/flatpak remote-add --system --if-not-exists flathub \
        https://dl.flathub.org/repo/flathub.flatpakrepo
      echo "notenix: Flathub remote added."
    else
      echo "notenix: Flathub remote already present, skipping."
    fi
  '';

  installAppsScript = pkgs.writeShellScript "notenix-install-flatpak-apps" ''
    set -euo pipefail
    for app in ${lib.escapeShellArgs cfg.packages}; do
      if ! ${pkgs.flatpak}/bin/flatpak info --system "$app" &>/dev/null; then
        echo "notenix: installing Flatpak $app …"
        ${pkgs.flatpak}/bin/flatpak install --system --noninteractive flathub "$app" || true
      else
        echo "notenix: $app already installed, skipping."
      fi
    done
  '';

  updateAppsScript = pkgs.writeShellScript "notenix-update-flatpak-apps" ''
    set -euo pipefail
    output=$(${pkgs.flatpak}/bin/flatpak update --system --noninteractive 2>&1)
    echo "$output"
    if echo "$output" | grep -q 'Changes:'; then
      msg="Flatpak apps updated. No reboot required."
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
            --urgency=low \
            "Flatpak Updated" "$msg" 2>/dev/null || true
      done
    fi
  '';
in
{
  options.notenix.applications.flatpak = {
    enable = lib.mkOption {
      type    = lib.types.bool;
      default = true;
      description = "Flatpak support with Flathub remote and daily app updates.";
    };

    packages = lib.mkOption {
      type    = lib.types.listOf lib.types.str;
      default = [];
      example = [ "org.libreoffice.LibreOffice" "com.spotify.Client" ];
      description = ''
        Flatpak application IDs to install from Flathub.
        Apps are installed idempotently on boot and updated daily.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    services.flatpak.enable = true;

    systemd.services."notenix-add-flathub" = {
      description = "Add Flathub Flatpak remote";
      wantedBy    = [ "multi-user.target" ];
      after       = [ "network-online.target" "flatpak-system-helper.service" ];
      wants       = [ "network-online.target" ];
      serviceConfig = {
        Type            = "oneshot";
        RemainAfterExit = true;
        ExecStart       = addFlathubScript;
      };
    };

    systemd.services."notenix-install-flatpak-apps" = lib.mkIf (cfg.packages != []) {
      description = "Install notenix Flatpak applications";
      wantedBy    = [ "multi-user.target" ];
      after       = [ "notenix-add-flathub.service" "network-online.target" ];
      wants       = [ "network-online.target" ];
      requires    = [ "notenix-add-flathub.service" ];
      serviceConfig = {
        Type            = "oneshot";
        RemainAfterExit = true;
        ExecStart       = installAppsScript;
      };
    };

    systemd.timers."notenix-update-flatpak-apps" = {
      description = "Daily Flatpak app update";
      wantedBy    = [ "timers.target" ];
      timerConfig = {
        OnCalendar         = "daily";
        RandomizedDelaySec = "1h";
        Persistent         = true;
      };
    };

    systemd.services."notenix-update-flatpak-apps" = {
      description = "Update notenix Flatpak applications";
      after = [ "network-online.target" "flatpak-system-helper.service" ];
      wants = [ "network-online.target" ];
      serviceConfig = {
        Type       = "oneshot";
        ExecStart  = updateAppsScript;
        Restart    = "on-failure";
        RestartSec = "30s";
      };
      unitConfig = {
        StartLimitIntervalSec = "300s";
        StartLimitBurst       = 5;
      };
    };
  };
}
