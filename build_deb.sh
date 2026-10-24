#!/bin/bash
# Build the Debian/Ubuntu package (python3-ferrum_<version>-<rev>_all.deb) plus the
# PyPI wheel + sdist, from a clean dist/. No py2dsc/stdeb: the .deb is staged
# directly from the freshly built wheel and packed with dpkg-deb.
#
# Requirements: python3 with `build` and `installer` importable (or set PYTHON to
# a venv that has them), dpkg-deb, gzip. Network is needed for the isolated
# hatchling build unless NO_ISOLATION=1 (then hatchling must be installed).
set -euo pipefail
umask 022

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
DEBREV="${DEBREV:-1}"
MAINTAINER="CerealOveride <150073255+CerealOveride@users.noreply.github.com>"
VERSION="$("$PYTHON" -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
DEBVER="${VERSION}-${DEBREV}"
PKG="python3-ferrum"
DEPENDS="python3:any, python3-pip, fonts-noto-color-emoji, xdg-utils, python3-aiofiles, python3-send2trash, python3-keyring, python3-keyrings.alt, python3-rich, python3-jeepney"

echo "==> Building ferrum ${VERSION} (deb ${DEBVER})"

# 1. Clean previous artifacts so stale wheels can never be picked up.
rm -rf dist deb_dist build ./*.egg-info
mkdir -p dist deb_dist

# 2. Wheel + sdist (hatchling backend).
BUILD_ARGS=(--outdir dist)
[ "${NO_ISOLATION:-0}" = "1" ] && BUILD_ARGS+=(--no-isolation)
"$PYTHON" -m build "${BUILD_ARGS[@]}"
WHEEL="dist/ferrum_fm-${VERSION}-py3-none-any.whl"
SDIST="dist/ferrum_fm-${VERSION}.tar.gz"
test -f "$WHEEL" && test -f "$SDIST"

# 3. Stage the Debian tree from the wheel (Debian layout: /usr/lib/python3/dist-packages).
STAGE="deb_dist/stage"
"$PYTHON" - "$WHEEL" "$STAGE" <<'PY'
import sys
from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile
wheel, stage = sys.argv[1], sys.argv[2]
site = "/usr/lib/python3/dist-packages"
dest = SchemeDictionaryDestination(
    {"purelib": site, "platlib": site, "scripts": "/usr/bin",
     "data": "/usr", "headers": "/usr/include/python3/ferrum"},
    interpreter="/usr/bin/python3", script_kind="posix",
    destdir=stage, bytecode_optimization_levels=(),
)
with WheelFile.open(wheel) as src:
    install(src, dest, {"INSTALLER": b"dpkg\n"})
PY

# Normalize permissions (Debian policy: 0755 dirs/executables, 0644 files).
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -exec chmod 644 {} +
chmod 755 "$STAGE"/usr/bin/*

install -Dm644 ferrum.desktop "$STAGE/usr/share/applications/ferrum.desktop"
install -d "$STAGE/usr/share/ferrum/wheels"
install -m644 debian_deps/*.whl "$STAGE/usr/share/ferrum/wheels/"
DOC="$STAGE/usr/share/doc/$PKG"
install -d "$DOC"
{ echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
  echo "Upstream-Name: ferrum"
  echo "Source: https://github.com/CerealOveride/ferrum"
  echo; echo "Files: *"; echo "License: MIT"; echo; sed 's/^/ /; s/^ $/ ./' LICENSE; } > "$DOC/copyright"
gzip -9n -c debian_scripts/changelog > "$DOC/changelog.Debian.gz"
chmod 644 "$DOC/copyright" "$DOC/changelog.Debian.gz"

# 4. Control files.
install -d "$STAGE/DEBIAN"
SIZE="$(du -sk --exclude=DEBIAN "$STAGE" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<CTRL
Package: ${PKG}
Version: ${DEBVER}
Architecture: all
Maintainer: ${MAINTAINER}
Installed-Size: ${SIZE}
Depends: ${DEPENDS}
Section: utils
Priority: optional
Homepage: https://github.com/CerealOveride/ferrum
Description: Fast DE-agnostic TUI file manager (Ferrum)
 Ferrum (fe) is a Python+Textual TUI file manager with SMB support.
 Vendors textual and smbprotocol wheels via postinst; other deps use
 Debian python3-* packages where apt is new enough.
CTRL
install -m755 debian_scripts/postinst "$STAGE/DEBIAN/postinst"
install -m755 debian_scripts/prerm "$STAGE/DEBIAN/prerm"
(cd "$STAGE" && find usr -type f -print0 | sort -z | xargs -0 md5sum > DEBIAN/md5sums)
chmod 644 "$STAGE/DEBIAN/control" "$STAGE/DEBIAN/md5sums"

# 5. Pack.
DEB="deb_dist/${PKG}_${DEBVER}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$DEB"
rm -rf "$STAGE"

echo "==> Built:"
ls -la dist/ "$DEB"
