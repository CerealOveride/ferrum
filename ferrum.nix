{ lib, python3Packages, fetchFromGitHub }:

python3Packages.buildPythonApplication {
  pname = "ferrum";
  version = "0.1.0";

  src = fetchFromGitHub {
    owner = "CerealOveride";
    repo = "ferrum";
    rev = "ac5149d3e90d5ae8f71af9af177e038cf0501ffc";
    sha256 = "1pz0ypjzxq1h3q0z306iv7mc6xvrv72jafxdkr3a0brw1hyhscrq";
  };

  format = "pyproject";

  nativeBuildInputs = with python3Packages; [
    hatchling
  ];

  propagatedBuildInputs = with python3Packages; [
    textual
    aiofiles
    smbprotocol
    send2trash
    keyring
    keyrings-alt
    rich
  ];

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
