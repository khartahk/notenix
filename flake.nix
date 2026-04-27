{
  description = "notenix — portable NixOS modules for a minimal GNOME + Flatpak desktop";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    disko.url   = "github:nix-community/disko/latest";
    disko.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, disko, ... }:
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

            # Pre-set a password so the VM is usable without extra steps
            users.users.user.initialPassword = "user";
          };
          # Base module list shared by notenix + ssh
          baseModules = [
            ./modules
            disko.nixosModules.disko
            ./hosts/notenix/configuration.nix
            ./hosts/notenix/disk.nix
          ];
          # Base module list shared by all VM configs (no disko/disk)
          vmBaseModules = [
            ./modules
            ./hosts/notenix/configuration.nix
            "${nixpkgs}/nixos/modules/virtualisation/qemu-vm.nix"
            vmOverrides
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
              # kanal: GUI (kanal) + CLI (kanalctl) for channel switching
              environment.systemPackages = [
                self.packages.${system}.kanal
              ];
              # Pre-seed the overrides file so kanal has something to edit.
              # Uses an activation script (not environment.etc) so the file is a
              # real writable file, not a read-only Nix store symlink.
              system.activationScripts.notenix-overrides = {
                text = ''
                  dest=/etc/nixos/notenix-install-overrides.nix
                  if [ ! -e "$dest" ]; then
                    mkdir -p /etc/nixos
                    cat > "$dest" << 'EOF'
# notenix machine configuration — written by the installer.
{ lib, ... }: {
  notenix.preset                         = lib.mkForce "desktop";
  notenix.system.autoupgrade.operation   = lib.mkForce "switch";
  notenix.system.install.hostName        = lib.mkForce "notenix-vm";
  notenix.system.install.userName        = lib.mkForce "user";
  notenix.system.install.userDescription = lib.mkForce "Test User";
  notenix.system.install.timeZone        = lib.mkForce "UTC";
  notenix.system.install.locale          = lib.mkForce "en_US.UTF-8";
  notenix.system.install.keyboardLayout  = lib.mkForce "si";
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

          # Like notenix but with SSH enabled — useful for remote deployment testing
          ssh = lib.nixosSystem {
            inherit system;
            modules = baseModules ++ [
              {
                services.openssh = {
                  enable                          = true;
                  settings.PasswordAuthentication = true;
                  settings.PermitRootLogin        = "no";
                };
              }
            ];
          };

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
      packages.${system} = let
        pkgs = nixpkgs.legacyPackages.${system};
        kanal = pkgs.python3Packages.buildPythonApplication {
          pname   = "kanal";
          version = "0.1.0";
          src     = ./pkgs/kanal;
          format  = "pyproject";
          nativeBuildInputs = with pkgs; [
            python3Packages.setuptools
            wrapGAppsHook4
          ];
          buildInputs = with pkgs; [ gtk4 libadwaita ];
          dependencies = [ pkgs.python3Packages.pygobject3 ];
          postInstall = ''
            install -Dm644 si.n1x05.notenix.kanal.desktop \
              $out/share/applications/si.n1x05.notenix.kanal.desktop
            # Bake the absolute path to kanalctl into the wrapper so pkexec
            # and the GUI can find it even when launched from the app grid.
            wrapProgram $out/bin/kanal \
              --set KANALCTL_BIN $out/bin/kanalctl
          '';
        };
      in {
        install = import ./install.nix { inherit nixpkgs disko system; };
        inherit kanal;
        default = self.packages.${system}.install;
        vm      = self.nixosConfigurations.vm.config.system.build.vm;
      };
    };
}
