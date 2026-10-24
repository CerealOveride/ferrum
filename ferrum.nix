{ lib, python3Packages, fetchFromGitHub }:

python3Packages.buildPythonApplication rec {
  pname = "ferrum";
  version = "0.1.2";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "CerealOveride";
    repo = "ferrum";
    rev = "v${version}";
    hash = "sha256-iezm0O9JN2B7JuMRFIkMjaB2nPyzibSZ7OJRuIHpWvI=";
  };

  build-system = with python3Packages; [
    hatchling
  ];

  dependencies = with python3Packages; [
    textual
    aiofiles
    smbprotocol
    send2trash
    keyring
    keyrings-alt
    rich
    jeepney
  ];

  # Don't pick up stale wheels if any are ever present in the source tree.
  preBuild = ''
    rm -rf dist build
  '';

  postInstall = ''
    install -Dm644 ferrum.desktop $out/share/applications/ferrum.desktop
  '';

  meta = with lib; {
    description = "A fast, stable, DE-agnostic TUI file manager";
    homepage = "https://github.com/CerealOveride/ferrum";
    license = licenses.mit;
    maintainers = [ ];
    platforms = platforms.linux;
    mainProgram = "fe";
  };
}
