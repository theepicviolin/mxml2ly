let
  nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-25.05";
  pkgs = import nixpkgs {
    config = { };
    overlays = [ ];
  };
in
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (
      p: with p; [
        tkinter
      ]
    ))
  ];
}
