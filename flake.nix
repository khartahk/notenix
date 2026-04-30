{
  description = "notenix — portable NixOS modules for a minimal GNOME + Flatpak desktop";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    disko.url   = "github:nix-community/disko/latest";
    disko.inputs.nixpkgs.follows = "nixpkgs";
    kanal.url   = "path:pkgs/kanal";
    kanal.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, disko, kanal, ... }:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
    in
    {
      # ---------------------------------------------------------------------------
      # Modules — notenix-local NixOS modules (no shkatle dependency)
      # ---------------------------------------------------------------------------
      nixosModules = {
        default = import ./modules;
      };

      # ---------------------------------------------------------------------------
      # Metadata consumed by kanal — defined in pkgs/kanal/flake.nix
      # ---------------------------------------------------------------------------
      lib.kanal = kanal.lib.kanal;

      # ---------------------------------------------------------------------------
      # lib.mkMachineSystem — used by /etc/nixos/flake.nix on real machines.
      # Takes { modules } and returns a full nixosSystem with all notenix
      # modules, disko, disk layout, and kanal pre-installed.
      # Machine-specific settings (preset, hostname, user, etc.) come from
      # the caller's modules list (typically /etc/nixos/machine.nix).
      # ---------------------------------------------------------------------------
      lib.mkMachineSystem = { modules ? [] }: lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.default
          disko.nixosModules.disko
          ./hosts/notenix/configuration.nix
          ./hosts/notenix/disk.nix
          { environment.systemPackages = [ self.packages.${system}.kanal ]; }
        ] ++ modules;
      };

      # ---------------------------------------------------------------------------
      # NixOS configurations
      #   - sample:      real machine install target (used by the install script)
      #   - vm-headless: quick headless smoke-test VM
      #   - vm-gnome:    full GNOME desktop VM (needs QEMU with a display)
      # ---------------------------------------------------------------------------
      nixosConfigurations =
        let
          # Shared inline overrides for both VM configs — replaces the
          # notenix-install-overrides.nix file that the installer writes on a
          # real machine.
          vmOverrides = {
            notenix.system.install.hostName        = lib.mkForce "notenix-vm";
            notenix.system.install.userName        = lib.mkForce "user";
            notenix.system.install.userDescription = lib.mkForce "Test User";
            notenix.system.install.timeZone        = lib.mkForce "UTC";
            notenix.system.install.locale          = lib.mkForce "en_US.UTF-8";
            notenix.system.install.keyboardLayout  = lib.mkForce "si";
            # VMs have no bootloader — switch activates immediately without reboot
            notenix.system.autoupgrade.operation   = lib.mkForce "switch";
            # Enable desktop preset so GNOME is present in the VM
            notenix.preset                         = lib.mkForce "desktop";

            # Pre-set a password so the VM is usable without extra steps
            users.users.user.initialPassword = "user";
          };
          # Base module list for the real-machine nixosConfiguration
          baseModules = [
            ./modules
            disko.nixosModules.disko
            ./hosts/notenix/configuration.nix
            ./hosts/notenix/disk.nix
            { environment.systemPackages = [ self.packages.${system}.kanal ]; }
          ];
          # Base module list shared by all VM configs (no disko/disk)
          vmBaseModules = [
            ./modules
            ./hosts/notenix/configuration.nix
            "${nixpkgs}/nixos/modules/virtualisation/qemu-vm.nix"
            vmOverrides
            { environment.systemPackages = [ self.packages.${system}.kanal ]; }
            {
              virtualisation.diskSize    = 16384;
              virtualisation.memorySize  = 4096;   # GNOME needs ≥ 2 GB
              virtualisation.cores       = 2;
              virtualisation.graphics    = true;   # enable QEMU display output
              virtualisation.resolution  = { x = 1280; y = 800; };
              # Auto-login to GDM so the desktop appears immediately
              services.displayManager.autoLogin.enable = true;
              services.displayManager.autoLogin.user   = "user";
              # Disable screen lock — no password needed in the test VM
              programs.dconf.profiles.user.databases = lib.mkAfter [
                {
                  lockAll  = false;
                  settings."org/gnome/desktop/screensaver".lock-enabled = false;
                  settings."org/gnome/desktop/session".idle-delay = lib.gvariant.mkUint32 0;
                }
              ];
              # Pre-seed /etc/nixos/machine.nix and flake.nix so kanal has something to edit.
              # Uses an activation script (not environment.etc) so the files are
              # real writable files, not read-only Nix store symlinks.
              system.activationScripts.notenix-machine = {
                text = ''
                  mkdir -p /etc/nixos
                  dest=/etc/nixos/machine.nix
                  if [ ! -e "$dest" ]; then
                    cat > "$dest" << 'EOF'
{ lib, ... }: {
  notenix.preset                         = lib.mkForce "desktop";
  notenix.system.autoupgrade.flakeRepo   = lib.mkForce "path:/etc/nixos";
  notenix.system.autoupgrade.hostName    = lib.mkForce "notenix-vm";
  notenix.system.autoupgrade.operation   = lib.mkForce "switch";
  notenix.system.install.hostName        = lib.mkForce "notenix-vm";
  notenix.system.install.userName        = lib.mkForce "user";
  notenix.system.install.userDescription = lib.mkForce "Test User";
  notenix.system.install.timeZone        = lib.mkForce "UTC";
  notenix.system.install.locale          = lib.mkForce "en_US.UTF-8";
  notenix.system.install.keyboardLayout  = lib.mkForce "si";
  system.stateVersion                    = "25.11";
}
EOF
                  fi
                  flake=/etc/nixos/flake.nix
                  if [ ! -e "$flake" ]; then
                    cat > "$flake" << 'EOF'
# /etc/nixos/flake.nix — machine entry point (seeded by VM).
# inputs.notenix.url is rewritten by kanal to switch branches.
{
  inputs.notenix.url = "github:n1x05/notenix";
  outputs = { notenix, ... }:
    notenix.lib.mkMachineSystem { modules = [ ./machine.nix ]; };
}
EOF
                  fi
                '';
                deps = [];
              };
            }
          ];
        in
        {
          notenix = lib.nixosSystem {
            inherit system;
            modules = baseModules;
          };
          # Alias so `--flake .` works without specifying a hostname
          default = self.nixosConfigurations.notenix;

          # Full GNOME VM: requires a display (QEMU GTK or VNC)
          # Run with:  nix run .#vm
          vm = lib.nixosSystem {
            inherit system;
            modules = vmBaseModules;
          };
        };

      # ---------------------------------------------------------------------------
      # Packages
      #   nix run .#install  — interactive TUI installer (use from live ISO)
      #   nix run            — alias for .#install
      #   nix run .#vm       — full GNOME desktop VM (needs QEMU display)
      # ---------------------------------------------------------------------------
      packages.${system} = {
        install = import ./install.nix { inherit nixpkgs disko system; };
        kanal   = kanal.packages.${system}.kanal;
        default = self.packages.${system}.install;
        vm      = self.nixosConfigurations.vm.config.system.build.vm;
      };

      # ---------------------------------------------------------------------------
      # Dev shell — `nix develop`
      #   Provides Python + kanal deps for hacking on pkgs/kanal without a full
      #   Nix build.  Run kanal directly with:
      #     KANAL_DRY_RUN=1 python -m kanal.gui
      # ---------------------------------------------------------------------------
      devShells.${system}.default =
        let pkgs = nixpkgs.legacyPackages.${system}; in
        pkgs.mkShell {
          name = "notenix-dev";
          packages = with pkgs; [
            # Python runtime + GTK bindings
            (python3.withPackages (ps: with ps; [ pygobject3 ]))
            gobject-introspection
            gtk4
            libadwaita
            glib
            # Useful tools
            nixd
            nil
          ];
          # Make GTK typelib path available
          GI_TYPELIB_PATH = "${pkgs.gtk4}/lib/girepository-1.0:${pkgs.libadwaita}/lib/girepository-1.0:${pkgs.glib}/lib/girepository-1.0";
          shellHook = ''
            # pkgs/kanal/kanal/ is the package directory; add its parent to PYTHONPATH
            # so `import kanal` works without installing.
            export PYTHONPATH="$PWD/pkgs/kanal:$PYTHONPATH"
            export KANAL_DRY_RUN=1
            echo "notenix dev shell — $(python --version)"
            echo "Run GUI: python -m kanal"
            echo "Run CLI: python -m kanal --ctl status"
          '';
        };
    };
}
