# notenix NixOS modules — assembled from upstream NixOS options.
# Each category mirrors what was previously delegated to shkatle.
{
  imports = [
    ./applications
    ./boot
    ./desktop
    ./hardware
    ./network
    ./security
    ./system
  ];
}
