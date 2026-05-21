{ config, lib, pkgs, ... }:

# Installs two app-menu entries for running nixos-rebuild manually:
#   "Apply Update Now"        → nixos-rebuild switch (takes effect immediately)
#   "Apply Update on Reboot"  → nixos-rebuild boot   (takes effect after reboot)
#
# Both entries open gnome-console (kgx) so the user can see progress.
# pkexec is used for privilege escalation - no password stored anywhere.
# Enabled whenever any desktop preset is active.

let
  anyDesktop = config.notenix.desktop.gnome.enable
            || config.notenix.desktop.cinnamon.enable;

  flakeArg = "path:/etc/nixos#notenix";

  mkLauncher = { name, label, labelSl, description, descriptionSl, operation, icon }: pkgs.writeTextFile {
    name = "notenix-rebuild-${operation}";
    destination = "/share/applications/notenix-rebuild-${operation}.desktop";
    text = ''
      [Desktop Entry]
      Version=1.0
      Type=Application
      Name=${label}
      Name[sl]=${labelSl}
      Comment=${description}
      Comment[sl]=${descriptionSl}
      Icon=${icon}
      Exec=kgx -- bash -c "pkexec sh -c 'nix flake update /etc/nixos && nixos-rebuild ${operation} --flake ${flakeArg}'; echo; echo '--- Done. Press Enter to close. ---'; read"
      Terminal=false
      Categories=System;Settings;
      Keywords=update;rebuild;nixos;system;
      Keywords[sl]=posodobitev;sistem;nixos;
    '';
  };

  switchLauncher = mkLauncher {
    name          = "notenix-rebuild-switch";
    label         = "Update Now";
    labelSl       = "Posodobi sedaj";
    description   = "Applies pending changes to your computer right away. You can keep using it while the update runs.";
    descriptionSl = "Uveljavi čakajoče spremembe takoj. Med posodobitvijo lahko računalnik normalno uporabljaš.";
    operation     = "switch";
    icon          = "software-update-available";
  };

  bootLauncher = mkLauncher {
    name          = "notenix-rebuild-boot";
    label         = "Update on Reboot";
    labelSl       = "Posodobi po ponovnem zagonu";
    description   = "Prepares the update so it takes effect the next time you restart your computer. Nothing changes until you reboot.";
    descriptionSl = "Pripravi posodobitev, ki se uveljavi ob naslednjem zagonu. Do takrat se ne spremeni nič.";
    operation     = "boot";
    icon          = "system-reboot";
  };

in
lib.mkIf anyDesktop {
  environment.systemPackages = [
    switchLauncher
    bootLauncher
    pkgs.gnome-console   # kgx — needed on Cinnamon too
  ];
}
