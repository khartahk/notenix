{
  description = "kanal — NixOS channel switcher GUI/CLI";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs   = nixpkgs.legacyPackages.${system};
    in
    {
      # -------------------------------------------------------------------------
      # Metadata consumed by kanal at runtime.
      # Channels are discovered from GitHub branches; presets are defined here.
      # -------------------------------------------------------------------------
      lib.kanal = {
        flakeBase = "github:n1x05/notenix";
        presets = [
          { id = "desktop";      label = "Desktop";      subtitle = "Full desktop with Flatpak, sound, bluetooth, printing"; }
          { id = "desktop-lite"; label = "Desktop Lite"; subtitle = "Lightweight desktop with sound, bluetooth, printing"; }
          { id = "minimal";      label = "Minimal";      subtitle = "No desktop, essentials only"; }
        ];
      };

      packages.${system} = {
        kanal = pkgs.python3Packages.buildPythonApplication {
          pname   = "kanal";
          version = "0.1.0";
          src     = ./.;
          format  = "pyproject";
          nativeBuildInputs = with pkgs; [
            python3Packages.setuptools
            wrapGAppsHook4
            gobject-introspection
          ];
          buildInputs = with pkgs; [ gtk4 libadwaita glibc ];
          dependencies = [ pkgs.python3Packages.pygobject3 ];
          postInstall = ''
            install -Dm644 si.n1x05.notenix.kanal.desktop \
              $out/share/applications/si.n1x05.notenix.kanal.desktop
            install -Dm644 ${./assets/update-symbolic.svg} \
              $out/share/icons/hicolor/scalable/actions/update-symbolic.svg
            wrapProgram $out/bin/kanal \
              --set KANALCTL_BIN $out/bin/kanalctl \
              --set KANAL_FLAKE_REF "${self.lib.kanal.flakeBase}" \
              --set KANAL_LOCALE_SUPPORTED "${pkgs.glibc}/share/i18n/SUPPORTED" \
              --set KANAL_XKB_EVDEV_XML "${pkgs.xorg.xkeyboardconfig}/share/X11/xkb/rules/evdev.xml"
          '';
        };

        default = self.packages.${system}.kanal;
      };
    };
}
